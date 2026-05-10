"""
迷因哏圖製造機 v1
產出：1080x1080 IG/Threads 友善方圖，含市場情緒 emoji + AI 鄉民風文案
"""
import os
import random
import datetime
import yfinance as yf
from PIL import Image, ImageDraw, ImageFont
from google import genai

MODEL_NAME = "gemini-2.5-flash"
OUTPUT = "daily_meme.png"

# Ubuntu runner 內建的 Noto CJK 字型路徑
FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
]

# 迷因情緒分級（門檻、emoji、文字標籤、背景顏色）
MOODS = [
    (5,    "🚀", "起飛中",  "#16a34a"),
    (2,    "💪", "看多日",  "#22c55e"),
    (0.5,  "😏", "穩穩賺",  "#84cc16"),
    (-0.5, "😐", "盤整日",  "#a1a1aa"),
    (-2,   "😬", "慌張中",  "#f59e0b"),
    (-5,   "📉", "崩盤日",  "#ef4444"),
    (-999, "💀", "葬禮日",  "#7f1d1d"),
]

# 標的池（會隨機抽 4 檔）
STOCK_POOL = {
    "2330.TW": "台積電",
    "^TWII":   "台股大盤",
    "^GSPC":   "S&P 500",
    "NVDA":    "輝達",
    "TSLA":    "特斯拉",
    "AAPL":    "蘋果",
    "BTC-USD": "比特幣",
    "ETH-USD": "以太坊",
    "GC=F":    "黃金",
}


# ============================================================
# 1. 抓資料
# ============================================================

def fetch_data(n=4):
    random.seed(datetime.date.today().isoformat())
    sample = dict(random.sample(list(STOCK_POOL.items()), n))
    df = yf.download(list(sample.keys()), period="5d", auto_adjust=True)["Close"].dropna()
    return [
        {
            "name": sample[code],
            "change": ((df[code].iloc[-1] - df[code].iloc[-2]) / df[code].iloc[-2]) * 100,
        }
        for code in sample
    ]


def get_mood(change):
    for threshold, emoji, label, color in MOODS:
        if change >= threshold:
            return emoji, label, color
    return MOODS[-1][1:]


# ============================================================
# 2. AI 寫文案
# ============================================================

def get_caption(stocks, avg_change, mood_label):
    summary = ", ".join(f"{s['name']} {s['change']:+.1f}%" for s in stocks)
    prompt = f"""
你是一個極度毒舌、愛自嘲、像 PTT 股版鄉民的迷因小編。

今日市場：{summary}
整體情緒：{mood_label}（平均 {avg_change:+.2f}%）

請寫一句 15 字內、有梗、適合放在 IG 迷因方圖正中央的中文標題。

要求：
- 用台灣鄉民流行語、自嘲、財經黑話
- 不要正經，越荒謬越好
- 結尾不要標點符號、不要引號
- 直接輸出一句話，不要解釋

風格範例：
- 韭菜的盛世我又來了
- 黃金漲了我才剛梭哈台股
- 散戶的眼淚比黃金還貴
- 我只是來繳學費的
- 跌停板上見朋友

直接給標題：
""".strip()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return resp.text.strip().strip("「」\"'""''").strip()


# ============================================================
# 3. 字型載入
# ============================================================

def load_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_chinese(text, font, max_width, draw):
    """中文逐字 wrap"""
    lines, current = [], ""
    for ch in text:
        test = current + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current:
                lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines


# ============================================================
# 4. 繪製迷因卡
# ============================================================

def draw_meme(stocks, avg_change, mood_data, caption, output):
    W, H = 1080, 1080
    emoji, mood_label, bg_color = mood_data

    img = Image.new("RGB", (W, H), bg_color)
    draw = ImageDraw.Draw(img)

    # 大 emoji（中上）
    emoji_font = load_font(260)
    draw.text((W // 2, 250), emoji, font=emoji_font, anchor="mm", fill="white")

    # AI 標題（中央）
    title_font = load_font(72)
    wrapped = wrap_chinese(caption, title_font, W - 140, draw)
    y = 560 if len(wrapped) <= 1 else 530
    for line in wrapped:
        draw.text((W // 2, y), line, font=title_font, anchor="mm",
                  fill="white", stroke_width=4, stroke_fill="black")
        y += 90

    # 底部黑色資訊條（半透明）
    bar_h = 220
    overlay = Image.new("RGBA", (W, bar_h), (0, 0, 0, 180))
    img.paste(overlay, (0, H - bar_h), overlay)

    # 心情標籤（左）
    info_font = load_font(40)
    label_font = load_font(30)
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    draw.text((60, H - 180), f"今日：{mood_label} {avg_change:+.2f}%",
              font=info_font, fill="white")
    draw.text((60, H - 60), today_str, font=label_font, fill="#cbd5e1")

    # 個股漲跌（右）
    y_offset = H - 180
    for s in stocks:
        sign = "+" if s["change"] >= 0 else ""
        line = f"{s['name']}: {sign}{s['change']:.2f}%"
        draw.text((W - 60, y_offset), line, font=label_font, anchor="rt", fill="white")
        y_offset += 38

    img.save(output, "PNG", optimize=True)


# ============================================================
# 5. 主流程
# ============================================================

def main():
    stocks = fetch_data(n=4)
    avg = sum(s["change"] for s in stocks) / len(stocks)
    mood = get_mood(avg)
    print(f"🎲 抽中標的：{[s['name'] for s in stocks]}")
    print(f"📈 市場情緒：{mood[0]} {mood[1]} ({avg:+.2f}%)")

    caption = get_caption(stocks, avg, mood[1])
    print(f"💬 AI 文案：{caption}")

    draw_meme(stocks, avg, mood, caption, OUTPUT)
    print(f"✅ 迷因哏圖已生成：{OUTPUT}")


if __name__ == "__main__":
    main()
