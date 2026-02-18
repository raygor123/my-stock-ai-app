import streamlit as st
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. 配置 AI ---
# 之後在 Streamlit 設定裡輸入 API Key 會更安全，現在先預留位置
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🚀 AI 股票即市分析專家")

# --- 2. 側邊欄輸入 ---
ticker = st.sidebar.text_input("輸入美股代碼 (例如: NVDA)", "TSLA")
period = st.sidebar.selectbox("分析週期", ["1mo", "3mo", "6mo", "1y"])

# --- 3. 抓取數據 ---
data = yf.download(ticker, period=period, interval="1d")

if not data.empty:
    # 計算 RSI
    data['RSI'] = ta.rsi(data['Close'], length=14)
    
    # 畫 K 線圖
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 4. 呼叫 AI 分析 ---
    if st.button("點擊進行 AI 深度分析"):
        last_price = data['Close'].iloc[-1]
        last_rsi = data['RSI'].iloc[-1]
        
        prompt = f"分析股票 {ticker}：目前價格 {last_price:.2f}，RSI 為 {last_rsi:.2f}。請給出短線背馳分析及操作建議。"
        response = model.generate_content(prompt)
        st.write("### 🤖 AI 分析報告")
        st.write(response.text)
else:
    st.error("代碼有誤，請重新輸入")
