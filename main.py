import yfinance as yf
import os
import google.generativeai as genai

# 1. 設定 AI (從您的 GitHub 保險箱讀取密鑰)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-pro')

# 2. 抓取金融數據 (台積電、美股標普500、台幣匯率)
stocks = {"2330.TW": "台積電", "^GSPC": "美股標普500", "USDTWD=X": "台幣匯率"}
df = yf.download(list(stocks.keys()), period="2d")['Close']
prices = df.iloc[-1]
changes = ((df.iloc[-1] - df.iloc[-2]) / df.iloc[-2]) * 100

# 3. 整理數據交給 AI 撰寫
data_summary = ""
for code, name in stocks.items():
    data_summary += f"{name} 最新價格: {prices[code]:.2f}, 漲跌幅: {changes[code]:+.2f}%\n"

# 4. 讓 AI 生成生動的 YouTube Shorts 腳本
prompt = f"""
你是一位專業的財經短影音創作者，風格要像『標題黨』，非常吸睛。
請根據以下數據，寫一段 30 秒的 YouTube Shorts 腳本。
要求：標題要有爆發力，內容要有情緒起伏（例如：震驚或機會來了），並呼籲觀眾點讚追蹤。
數據如下：
{data_summary}
"""
response = model.generate_content(prompt)
ai_script = response.text

# 5. 將 AI 寫好的腳本存入 daily_script.txt
with open("daily_script.txt", "w", encoding="utf-8") as f:
    f.write(ai_script)

print("✅ AI 腳本已生成成功！")
