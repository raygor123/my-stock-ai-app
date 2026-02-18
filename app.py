import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 核心配置 (修正 404) ---
def get_ai_response(prompt):
    if "GEMINI_API_KEY" not in st.secrets:
        return "❌ 未設定 API Key"
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 2026 修正：用最基礎嘅 gemini-pro 確保兼容性
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 暫時不可用，請參考下方自動分析數據。(原因: {str(e)})"

st.set_page_config(page_title="短炒形態大師", layout="wide")
st.title("🏹 短炒實戰形態儀表板")

# --- 2. 側邊欄：嚴格週期控制 ---
ticker = st.sidebar.text_input("輸入代碼 (例如: NVDA, 0700.HK)", "TSLA").upper()
time_options = {
    "1. 極短線 (5分鐘線 - 最近)": {"p": "5d", "i": "5m"},
    "2. 小時線 (1小時圖 - 最近)": {"p": "7d", "i": "60m"},
    "3. 波段線 (日線 - 最近)": {"p": "1mo", "i": "1d"}
}
selected_range = st.sidebar.selectbox("分析週期", list(time_options.keys()))
p, i = time_options[selected_range]["p"], time_options[selected_range]["i"]

# --- 3. 數據抓取與清洗 (解決 5 分鐘線消失問題) ---
@st.cache_data(ttl=30)
def fetch_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty: return None
        # 強制壓平多層索引
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.ffill().dropna()
    except: return None

data = fetch_data(ticker, p, i)

# --- 4. 實戰技術分析 (不依賴 AI) ---
if data is not None and len(data) > 15:
    # A. 指標計算
    data['RSI'] = ta.rsi(data['Close'], length=14)
    macd = ta.macd(data['Close'])
    data = pd.concat([data, macd], axis=1)
    
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].iloc[-1])
    res = float(data['High'].tail(15).max())
    sup = float(data['Low'].tail(15).min())
    
    # B. 入場/止損/目標 (硬核計算)
    entry_zone = sup * 1.005 # 支持位加 0.5%
    stop_loss = sup * 0.97   # 支持位減 3%
    target = res * 0.99      # 阻力位減 1%

    # C. 自動形態識別邏輯
    st.subheader(f"📊 {ticker} {selected_range} 數據模型")
    
    # 顯示核心建議位
    col1, col2, col3 = st.columns(3)
    col1.metric("🎯 建議入場點", f"${entry_zone:.2f}")
    col2.metric("🛑 嚴格止損位", f"${stop_loss:.2f}")
    col3.metric("🏁 目標獲利位", f"${target:.2f}")

    st.markdown("---")
    
    # 指標顯示
    m1, m2, m3 = st.columns(3)
    m1.metric("當前價格", f"${last_price:.2f}")
    m2.metric("RSI (14)", f"{last_rsi:.1f}", delta="超買" if last_rsi > 70 else "超賣" if last_rsi < 30 else "中性")
    m3.metric("阻力位", f"${res:.2f}")

    # --- 5. AI 深度分析與形態掃描 ---
    st.divider()
    if st.button("🤖 執行 AI 深度背馳 & 形態分析"):
        with st.spinner('AI 正在讀取 K 線形態...'):
            # 畀最近 10 根 K 線數據 AI 睇，佢先識講形態
            history = data[['Open', 'High', 'Low', 'Close']].tail(10).to_string()
            prompt = (f"你係資深操盤手。分析 {ticker}：現價 {last_price}, RSI {last_rsi}, 支持 {sup}, 阻力 {res}。\n"
                      f"最近10日數據：\n{history}\n"
                      f"請回答：1. 識別形態 (如: W底, 十字星, 吞噬) 2. 是否有背馳訊號 3. 入場策略建議 (繁體中文)")
            analysis = get_ai_response(prompt)
            st.warning(analysis)
else:
    st.error(f"❌ 無法獲取 {ticker} 數據。請檢查代碼(如: AAPL, 0700.HK)或更換週期。5分鐘線數據在休市期間可能無法顯示。")
