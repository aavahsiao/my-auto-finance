import yfinance as yf
import datetime

# 1. 設定監控清單 (可隨時增加)
stocks = {"2330.TW": "台積電", "^GSPC": "美股標普500", "USDTWD=X": "台幣匯率"}
today_str = datetime.datetime.now().strftime("%Y-%m-%d")

# 2. 抓取數據 (包含今天與昨天)
print(f"正在分析 {today_str} 全球行情...")
df = yf.download(list(stocks.keys()), period="2d")['Close']
changes = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100

# 3. 生成影片文案
content = f"--- {today_str} 自動化影音腳本 ---\n\n"
for code, name in stocks.items():
    content += f"👉 {name}: {df.iloc[-1][code]:.2f} ({changes[code]:+.2f}%)\n"

content += "\n🔥 【爆款標題推薦】\n"
content += f"2026最新財富密碼！{stocks['2330.TW']}今天波動 {abs(changes['2330.TW']):.1f}%，現在進場還來得及？\n"

# 4. 把文案存成 txt 檔案供您複製
with open("daily_script.txt", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ 任務成功！")
