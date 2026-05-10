"""
全自動影片合成機 v1
功能：讀取 v2 產出的腳本/圖表，加上 TTS 配音 + 燒入字幕，合成 30 秒 YouTube Shorts 影片
依賴：gTTS（雲端 TTS、免費）、ffmpeg（GitHub Actions runner 內建）
"""
import os
import subprocess
from gtts import gTTS

SCRIPT_FILE = "daily_script.txt"
CHART_FILE = "daily_chart.png"
TTS_AUDIO = "daily_tts.mp3"
SUBS_SRT = "daily_video_subs.srt"
OUTPUT_VIDEO = "daily_video.mp4"


# ============================================================
# 1. 讀腳本（排除標題行）
# ============================================================

def load_script_lines():
    with open(SCRIPT_FILE, encoding="utf-8") as f:
        text = f.read()
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        if s.startswith("#"):  # 略過 markdown 標題
            continue
        lines.append(s)
    return lines


# ============================================================
# 2. TTS 配音
# ============================================================

def synthesize_tts(lines, output_file):
    text = "。".join(lines)
    tts = gTTS(text=text, lang="zh-tw", slow=False)
    tts.save(output_file)
    return output_file


def get_audio_duration(audio_file):
    """用 ffprobe 取得音訊長度（秒）"""
    result = subprocess.run(
        ["ffprobe", "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         audio_file],
        capture_output=True, text=True, check=True
    )
    return float(result.stdout.strip())


# ============================================================
# 3. 重新生成字幕（用實際音訊長度均分）
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
# 4. ffmpeg 合成影片
# ============================================================

def compose_video(image_file, audio_file, srt_file, output_file, duration):
    style = (
        "FontName=Noto Sans CJK TC,"
        "FontSize=18,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=2,"
        "Alignment=2,MarginV=80"
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

    print("🔊 生成 TTS 配音...")
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
