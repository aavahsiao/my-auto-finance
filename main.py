"""
AI 財經短影音腳本生成器 v2
功能：每天輪替不同人格、隨機抽選標的、結合即時新聞、產出 5 種素材
"""
import os
import random
import datetime
import feedparser
import matplotlib
matplotlib.use("Agg")  # 不需要 GUI
import matplotlib.pyplot as plt
import yfinance as yf
from google import genai

# ============================================================
# 1. 設定區（你可以隨時改這幾個區塊）
# ============================================================

# --- 標的池：每天從這裡隨機抽 5 檔 ---
STOCK_POOL = {
    "2330.TW": "台積電",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2603.TW": "長榮",
    "2882.TW": "國泰金",
    "^TWII":   "台股加權",
    "^GSPC":   "美股 S&P 500",
    "^IXIC":   "那斯達克",
    "NVDA":    "輝達",
    "AAPL":    "蘋果",
    "TSLA":    "特斯拉",
    "MSFT":    "微軟",
    "BTC-USD": "比特幣",
    "ETH-USD": "以太坊",
    "GC=F":    "黃金",
    "CL=F":    "原油",
    "USDTWD=X": "台幣匯率",
    "JPY=X":   "日圓匯率",
}

# --- 七種人格：以星期幾自動輪替 (0=週一, 6=週日) ---
PERSONAS = {
    0: ("嚴謹分析師", "理性、數據導向，像 CNBC 評論員。用數據說話，適度引用歷史對照，尾段給專業觀點。"),
    1: ("搞笑網紅",   "俏皮玩梗，像脫口秀演員。找時事的好笑切入點，用比喻和迷因，結尾要有笑點。"),
    2: ("震驚標題黨", "誇張緊迫感，標題要驚悚。製造焦慮和好奇，全段都要爆點，結尾呼籲『點讚追蹤』。"),
    3: ("故事達人",   "敘事派、情感豐富，像在說書。把當日市場擬人化，用劇情起伏，結尾留懸念。"),
    4: ("週末懶人包", "精簡整理，像新聞主播。條列重點，總結本週走勢，給週末持有建議。"),
    5: ("教學老師",   "深入淺出，用比喻。選一個財經觀念當主軸，結合當天股市實例，結尾出小考題。"),
    6: ("預言家",     "前瞻預測，像週日節目主持人。預測下週走勢，列出值得觀察的事件，結尾給觀眾投票題。"),
}

# --- AI 模型 ---
MODEL_NAME = "gemini-2.5-flash"

# ============================================================
# 2. 抓資料
# ============================================================

def pick_stocks(n=5):
    """每天隨機抽 n 檔標的"""
    # 用今天日期當隨機種子，確保同一天執行兩次抽到一樣的（避免重跑差異）
    random.seed(datetime.date.today().isoformat())
    return dict(random.sample(list(STOCK_POOL.items()), n))


def fetch_prices(stocks):
    """抓股價，回傳 (prices, changes, df)"""
    df = yf.download(list(stocks.keys()), period="5d", auto_adjust=True)["Close"]
    df = df.dropna()
    prices = df.iloc[-1]
    changes = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100
    return prices, changes, df


def fetch_news(top_n=3):
    """從 Google News RSS 抓今日財經頭條（免費、無需 API key）"""
    url = "https://news.google.com/rss/search?q=%E8%B2%A1%E7%B6%93+%E8%82%A1%E5%B8%82&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries[:top_n]]


# ============================================================
# 3. 整理 prompt
# ============================================================

def build_prompt(persona_name, persona_style, data_summary, news_lines):
    today = datetime.date.today().strftime("%Y/%m/%d")
    news_block = "\n".join(f"- {n}" for n in news_lines)
    return f"""
你今天是「{persona_name}」風格的財經短影音創作者。
風格設定：{persona_style}

請根據以下資料寫一段 30 秒的 YouTube Shorts 腳本，並順便產出其他素材。

【日期】{today}

【今日股市快照】
{data_summary}

【今日財經頭條】
{news_block}

請依照以下格式輸出，每段都用三個等號標記區塊邊界，不要遺漏任何段：

===標題候選===
（產出 3 個吸睛標題，每個 25 字內，每個獨立一行，不要編號）

===腳本===
（30 秒口語腳本，每句獨立一行，總共約 6~8 句，要有起承轉合）

===描述===
（YouTube 影片描述，2~3 段，可帶入新聞時事）

===標籤===
（10 個 hashtag，用空格分隔，不要 # 號重複）
""".strip()


# ============================================================
# 4. 呼叫 AI 並 parse 結果
# ============================================================

def parse_sections(text):
    """把 AI 輸出的 ===段名=== 拆成 dict"""
    sections = {}
    current = None
    buf = []
    for line in text.splitlines():
        if line.strip().startswith("===") and line.strip().endswith("==="):
            if current:
                sections[current] = "\n".join(buf).strip()
            current = line.strip().strip("=").strip()
            buf = []
        else:
            buf.append(line)
    if current:
        sections[current] = "\n".join(buf).strip()
    return sections


# ============================================================
# 5. 產出檔案
# ============================================================

def write_files(sections, prices, changes, stocks, persona_name):
    today = datetime.date.today().strftime("%Y-%m-%d")

    # (1) 主腳本
    with open("daily_script.txt", "w", encoding="utf-8") as f:
        f.write(f"# {today} ({persona_name} 風格)\n\n")
        f.write(sections.get("腳本", "") + "\n")

    # (2) 標題候選
    with open("daily_titles.txt", "w", encoding="utf-8") as f:
        f.write(f"# {today} 標題候選\n\n")
        f.write(sections.get("標題候選", "") + "\n")

    # (3) 描述 + 標籤
    with open("daily_description.txt", "w", encoding="utf-8") as f:
        f.write(f"# {today} YouTube 描述\n\n")
        f.write(sections.get("描述", "") + "\n\n")
        f.write("【標籤】\n")
        f.write(sections.get("標籤", "") + "\n")

    # (4) SRT 字幕：把腳本每句配上 4 秒區段
    write_srt(sections.get("腳本", ""))

    # (5) 漲跌幅圖
    write_chart(prices, changes, stocks, today)


def write_srt(script_text):
    lines = [l for l in script_text.splitlines() if l.strip()]
    if not lines:
        return
    seconds_each = 4  # 每句 4 秒
    with open("daily_subtitles.srt", "w", encoding="utf-8") as f:
        for i, line in enumerate(lines):
            start = i * seconds_each
            end = (i + 1) * seconds_each
            f.write(f"{i+1}\n")
            f.write(f"{format_srt_time(start)} --> {format_srt_time(end)}\n")
            f.write(f"{line.strip()}\n\n")


def format_srt_time(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d},000"


def write_chart(prices, changes, stocks, today):
    names = [stocks[code] for code in changes.index]
    values = [changes[code] for code in changes.index]
    colors = ["#e74c3c" if v >= 0 else "#27ae60" for v in values]  # 台股紅漲綠跌

    plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(names, values, color=colors)
    for bar, v in zip(bars, values):
        ax.text(v, bar.get_y() + bar.get_height()/2,
                f"  {v:+.2f}%", va="center",
                ha="left" if v >= 0 else "right",
                fontsize=11, fontweight="bold")
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(f"{today} 漲跌幅一覽", fontsize=14, fontweight="bold")
    ax.set_xlabel("漲跌幅 (%)")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig("daily_chart.png", dpi=100, bbox_inches="tight")
    plt.close()


# ============================================================
# 6. 主流程
# ============================================================

def main():
    weekday = datetime.date.today().weekday()
    persona_name, persona_style = PERSONAS[weekday]
    print(f"🎭 今日人格：{persona_name}")

    stocks = pick_stocks(n=5)
    print(f"🎲 今日標的：{list(stocks.values())}")

    prices, changes, _ = fetch_prices(stocks)
    data_summary = "\n".join(
        f"- {stocks[code]}：{prices[code]:.2f}（{changes[code]:+.2f}%）"
        for code in changes.index
    )

    news = fetch_news(top_n=3)
    print(f"📰 抓到 {len(news)} 則新聞")

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = build_prompt(persona_name, persona_style, data_summary, news)
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)

    sections = parse_sections(response.text)
    write_files(sections, prices, changes, stocks, persona_name)

    print("✅ 全部產出完成：")
    print("   - daily_script.txt（主腳本）")
    print("   - daily_titles.txt（3 個標題候選）")
    print("   - daily_description.txt（描述 + 標籤）")
    print("   - daily_subtitles.srt（字幕）")
    print("   - daily_chart.png（漲跌幅圖）")


if __name__ == "__main__":
    main()
