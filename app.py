import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置 ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.error("請在 Secrets 設定 GEMINI_API_KEY")

st.set_page_config(page_title="短炒數據專家", layout="wide")
st.title("⚡ 專業短炒數據儀表板")

# --- 2. 側邊欄設定 (精簡週期) ---
ticker = st.sidebar.text_input("輸入代碼 (如: NVDA, 0700.HK)", "TSLA")

# 只保留最穩定的短線週期
time_options = {
    "1. 極短線 (5分鐘線 - 近5日)": {"p": "5d", "i": "5m"},
    "2. 小時線 (1小時圖 - 近1週)": {"p": "7d", "i": "60m"},
    "3. 短波段 (日線 - 近5日)": {"p": "5d", "i": "1d"},
}
selected_range = st.sidebar.selectbox("分析週期", list(time_options.keys()))
p = time_options[selected_range]["p"]
i = time_options[selected_range]["i"]

@st.cache_data(ttl=60) # 提速：1分鐘內不重複抓取
def get_clean_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if not df.empty:
        # 處理多層索引並填充缺失值
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        df = df.ffill().dropna() 
    return df

data = get_clean_data(ticker, p, i)

# --- 3. 核心數據運算 ---
if not data.empty and len(data) > 15:
    # 技術指標
    data['RSI'] = ta.rsi(data['Close'], length=14)
    macd = ta.macd(data['Close'])
    data = pd.concat([data, macd], axis=1)
    
    # 阻力支持 (取最近 15 根 K 線)
    res = float(data['High'].tail(15).max())
    sup = float(data['Low'].tail(15).min())
    
    # 提取數值 (確保不為空)
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].dropna().iloc[-1])
    # 根據 pandas_ta 欄位命名抓取 MACD 柱狀圖 (Histogram)
    h_col = [c for c in data.columns if 'MACDh' in c][0]
    last_h = float(data[h_col].iloc[-1])

    # --- 4. 數據顯示 ---
    st.subheader(f"📊 {ticker} 分析結果")
    col1, col2, col3 = st.columns(3)
    col1.metric("現價", f"${last_price:.2f}")
    col2.metric("RSI (14)", f"{last_rsi:.1f}", delta="超買" if last_rsi > 70 else "超賣" if last_rsi < 30 else None)
    col3.metric("MACD 趨勢", f"{last_h:.3f}", delta="向上" if last_h > 0 else "向下")

    st.markdown("---")
    sc1, sc2 = st.columns(2)
    sc1.error(f"🔴 短期壓力位: ${res:.2f}")
    sc2.success(f"🟢 短期支撐位: ${sup:.2f}")

    # --- 5. AI 操作建議 ---
    if st.button("🤖 獲取 AI 短炒策略"):
        with st.spinner('AI 分析中...'):
            prompt = (f"你是短線專家。分析股票 {ticker} ({selected_range})：現價 {last_price:.2f}, "
                      f"RSI {last_rsi:.1f}, MACD柱 {last_h:.3f}, 壓力 {res:.2f}, 支撐 {sup:.2f}。 "
                      f"請繁體中文回答：1.背馳狀況 2.建議操作 3.止損位。不要廢話。")
            response = model.generate_content(prompt)
            st.warning(response.text)
else:
    st.info("🕒 正在等待數據更新，或請確保代碼正確（美股 AAPL, 港股 0700.HK）。")
