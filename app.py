import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置 (從 Streamlit Secrets 讀取 Key) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    st.warning("⚠️ 請在 Streamlit Secrets 中設定 GEMINI_API_KEY 以啟用 AI 分析。")

st.set_page_config(page_title="短炒數據專家", layout="wide")
st.title("⚡ 短炒即市數據儀表板")

# --- 2. 側邊欄設定 (針對短炒週期) ---
st.sidebar.header("市場設定")
ticker = st.sidebar.text_input("輸入代碼 (如: NVDA, 0700.HK)", "TSLA")

# 定義短線頻率：1分鐘(最近1日), 5分鐘(最近5日), 1小時(最近1週)
time_options = {
    "1. 今日即市 (1分鐘線)": {"p": "1d", "i": "1m"},
    "2. 近5日走勢 (5分鐘線)": {"p": "5d", "i": "5m"},
    "3. 近1週分析 (1小時線)": {"p": "7d", "i": "60m"},
}
selected_range = st.sidebar.selectbox("選擇分析週期", list(time_options.keys()))
p = time_options[selected_range]["p"]
i = time_options[selected_range]["i"]

# --- 3. 獲取數據 (加入快取提速) ---
@st.cache_data(ttl=30)
def get_data(symbol, period, interval):
    try:
        # 加上 progress=False 減少 log 輸出提速
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        return df
    except Exception as e:
        return pd.DataFrame()

data = get_data(ticker, p, i)

# --- 4. 數據運算與顯示 ---
if not data.empty and len(data) > 30:
    # A. 技術指標計算 (RSI & MACD)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    # 使用 pandas_ta 計算 MACD
    macd = ta.macd(data['Close'], fast=12, slow=26, signal=9)
    data = pd.concat([data, macd], axis=1)
    
    # B. 自動找阻力與支持 (取最近 20 根 K 線的高低點)
    support = data['Low'].rolling(window=20).min().iloc[-1]
    resistance = data['High'].rolling(window=20).max().iloc[-1]
    
    # C. 取得最新一筆數據
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].iloc[-1])
    # 根據 pandas_ta 的欄位命名規則抓取
    m_val = float(data['MACD_12_26_9'].iloc[-1])
    s_val = float(data['MACDs_12_26_9'].iloc[-1])
    h_val = float(data['MACDh_12_26_9'].iloc[-1])
    
    # --- 5. 數據儀表板佈局 ---
    st.subheader(f"📊 {ticker} 實時關鍵指標")
    
    # 第一排：核心數據卡片
    col1, col2, col3 = st.columns(3)
    col1.metric("當前價格", f"${last_price:.2f}")
    col2.metric("RSI (14)", f"{last_rsi:.1f}", 
                delta="⚠️超買" if last_rsi > 70 else "✅超賣" if last_rsi < 30 else "中性")
    col3.metric("MACD 能量柱", f"{h_val:.2f}", 
                delta="底背馳機會" if (h_val > 0 and last_rsi < 40) else "頂背馳風險" if (h_val < 0 and last_rsi > 60) else None)

    # 第二排：阻力與支持
    st.markdown("---")
    s_col1, s_col2 = st.columns(2)
    with s_col1:
        st.error(f"🔴 短期阻力位 (近期高點): **${resistance:.2f}**")
    with s_col2:
        st.success(f"🟢 短期支持位 (近期低點): **${support:.2f}**")

    # --- 6. AI 操作建議 ---
    st.write("") 
    if st.button("🤖 獲取 Gemini AI 即市操作策略"):
        with st.spinner('AI 正在深度掃描背馳訊號...'):
            prompt = (f"你是一位專業的短線操盤手。分析股票 {ticker} 在 {selected_range} 週期下的表現：\n"
                      f"當前價格: {last_price:.2f}, RSI: {last_rsi:.2f}, MACD柱: {h_val:.2f}, "
                      f"阻力位: {resistance:.2f}, 支持位: {support:.2f}。\n"
                      f"請根據以上『數字』直接給出：1. 是否有背馳訊號？ 2. 具體進場價位建議。 3. 嚴格止損位。 (請用繁體中文，越簡短越好，直接講重點)")
            response = model.generate_content(prompt)
            st.info(response.text)
else:
    st.warning("⚠️ 無法獲取數據。請檢查：1. 代碼是否正確 2. 是否在開市時段 3. Yahoo Finance 暫時限制。")
