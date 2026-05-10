"""
全自動影片合成機 v2
升級重點：
- TTS 從 gTTS 換成 edge-tts（微軟神經網絡 TTS，免費、自然度大幅提升）
- 字幕字級縮小（12pt）
- 字幕位置往下挪（離底部 30px，原本 80）
- 配音速度 +15%（比正常快一點點）
"""
import os
import subprocess
import asyncio
import edge_tts

SCRIPT_FILE = "daily_script.txt"
CHART_FILE = "daily_chart.png"
TTS_AUDIO = "daily_tts.mp3"
SUBS_SRT = "daily_video_subs.srt"
OUTPUT_VIDEO = "daily_video.mp4"

# ============================================================
# Edge TTS 設定（可以自己挑語音）
# ============================================================
# 台灣女聲：zh-TW-HsiaoChenNeural（推薦，自然清晰）
# 台灣女聲：zh-TW-HsiaoYuNeural（活潑年輕）
# 台灣男聲：zh-TW-YunJheNeural（沉穩專業）
VOICE = "zh-TW-HsiaoChenNeural"
TTS_RATE = "+15%"   # 比正常快 15%，可改 +0% / +10% / +25%


# ============================================================
# 1. 讀腳本
# ============================================================

def load_script_lines():
    with open(SCRIPT_FILE, encoding="utf-8") as f:
        text = f.read()
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        lines.append(s)
    return lines


# ============================================================
# 2. TTS 配音（edge-tts 神經網絡語音）
# ============================================================

async def synthesize_async(text, output_file):
    communicate = edge_tts.Communicate(text, VOICE, rate=TTS_RATE)
    await communicate.save(output_file)


def synthesize_tts(lines, output_file):
    text = "。".join(lines)
    asyncio.run(synthesize_async(text, output_file))
    return output_file


def get_audio_duration(audio_file):
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         audio_file],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


# ============================================================
# 3. 字幕重新對齊
# ============================================================

def regenerate_srt(lines, total_duration, output_file):
    n = len(lines)
    if n == 0:
        return
    per_line = total_duration / n
    with open(output_file, "w", encoding="utf-8") as f:
        for i, line in enumerate(lines):
            start = i * per_line
            end = (i + 1) * per_line
            f.write(f"{i+1}\n")
            f.write(f"{srt_time(start)} --> {srt_time(end)}\n")
            f.write(f"{line}\n\n")


def srt_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s_full = seconds - h * 3600 - m * 60
    s_int = int(s_full)
    ms = int((s_full - s_int) * 1000)
    return f"{h:02d}:{m:02d}:{s_int:02d},{ms:03d}"


# ============================================================
# 4. 合成影片
# ============================================================

def compose_video(image_file, audio_file, srt_file, output_file, duration):
    style = (
        "FontName=Noto Sans CJK TC,"
        "FontSize=12,"                  # 18 → 12（小一些，不擋畫面）
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=2,"
        "Alignment=2,"                  # 底部置中
        "MarginV=30"                    # 80 → 30（更靠近底部）
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_file,
        "-i", audio_file,
        "-vf", f"scale=1080:1920:force_original_aspect_ratio=decrease,"
               f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=white,"
               f"subtitles={srt_file}:force_style='{style}'",
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-t", f"{duration:.2f}",
        output_file,
    ]
    subprocess.run(cmd, check=True)


# ============================================================
# 5. 主流程
# ============================================================

def main():
    print(f"📖 讀取腳本：{SCRIPT_FILE}")
    lines = load_script_lines()
    print(f"   - 共 {len(lines)} 句")

    print(f"🔊 edge-tts 生成配音（語音 {VOICE}，速度 {TTS_RATE}）...")
    synthesize_tts(lines, TTS_AUDIO)
    duration = get_audio_duration(TTS_AUDIO)
    print(f"   - 音訊長度：{duration:.2f} 秒")

    print("📝 重新對齊字幕時間...")
    regenerate_srt(lines, duration, SUBS_SRT)

    print("🎬 ffmpeg 合成影片中...")
    compose_video(CHART_FILE, TTS_AUDIO, SUBS_SRT, OUTPUT_VIDEO, duration)

    size_mb = os.path.getsize(OUTPUT_VIDEO) / 1024 / 1024
    print(f"✅ 影片完成：{OUTPUT_VIDEO}（{size_mb:.1f} MB）")


if __name__ == "__main__":
    main()
