import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置與錯誤診斷 ---
def init_gemini():
    if "GEMINI_API_KEY" not in st.secrets:
        return None, "❌ 找不到 API Key。請在 Streamlit Cloud 的 Secrets 設定 GEMINI_API_KEY。"
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 嘗試使用最穩定的模型
        model = genai.GenerativeModel('gemini-1.0-pro')
        return model, None
    except Exception as e:
        return None, f"❌ AI 初始化失敗: {str(e)}"

model, ai_error = init_gemini()

st.set_page_config(page_title="AI 短炒實戰儀表板", layout="wide")
st.title("🏹 AI 短炒形態實戰儀表板")

# --- 2. 週期選擇 ---
ticker = st.sidebar.text_input("輸入代碼 (例如: NVDA, 0700.HK)", "TSLA")

time_options = {
    "1. 極短線 (5分鐘線 - 近5日)": {"p": "5d", "i": "5m"},
    "2. 小時線 (1小時圖 - 近1週)": {"p": "7d", "i": "60m"},
    "3. 中線趨勢 (日線 - 近半年)": {"p": "6mo", "i": "1d"},
}
selected_label = st.sidebar.selectbox("分析週期", list(time_options.keys()))
p = time_options[selected_label]["p"]
i = time_options[selected_label]["i"]

# --- 3. 數據抓取 ---
@st.cache_data(ttl=60)
def fetch_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.ffill().dropna()
    except:
        return None

data = fetch_data(ticker, p, i)

# --- 4. 形態標籤與技術運算 ---
if data is not None and len(data) > 20:
    data['RSI'] = ta.rsi(data['Close'], length=14)
    macd = ta.macd(data['Close'])
    data = pd.concat([data, macd], axis=1)
    
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].iloc[-1])
    res = float(data['High'].tail(20).max())
    sup = float(data['Low'].tail(20).min())
    
    # 簡易形態標籤邏輯
    pattern_label = "🔍 正在分析形態..."
    if last_rsi < 30: pattern_label = "📉 極度超賣 (潛在反彈)"
    elif last_rsi > 70: pattern_label = "📈 極度超買 (注意回調)"
    elif last_price > res * 0.98: pattern_label = "⚔️ 挑戰阻力位"
    elif last_price < sup * 1.02: pattern_label = "🛡️ 支撐位防守中"
    else: pattern_label = "↔️ 橫盤震盪"

    st.success(f"**當前形態動態標籤：{pattern_label}**")

    # 數據卡片
    c1, c2, c3 = st.columns(3)
    c1.metric("當前價格", f"${last_price:.2f}")
    c2.metric("RSI 指標", f"{last_rsi:.1f}")
    c3.metric("阻力 / 支持", f"{res:.1f} / {sup:.1f}")

    st.markdown("---")

    # --- 5. AI 分析 (含入場位) ---
    if st.button("🤖 獲取 AI 實戰入場策略"):
        if ai_error:
            st.error(ai_error)
        else:
            try:
                with st.spinner('AI 正在計算精確入場位...'):
                    # 傳送數據給 AI
                    recent_ohlc = data[['Open', 'High', 'Low', 'Close']].tail(10).to_string()
                    prompt = (
                        f"你是一位實戰交易員。分析股票 {ticker} ({selected_label})：\n"
                        f"現價: {last_price}, RSI: {last_rsi}, 阻力: {res}, 支持: {sup}。\n"
                        f"最近10筆數據：\n{recent_ohlc}\n\n"
                        f"請以繁體中文給出：\n"
                        f"1. 技術形態標籤 (如：W底、上升旗形)\n"
                        f"2. 是否有背馳訊號？\n"
                        f"3. 入場位建議 (精確數字)\n"
                        f"4. 止損位與目標價 (精確數字)"
                    )
                    response = model.generate_content(prompt)
                    st.warning(response.text)
            except Exception as e:
                st.error(f"AI 呼叫失敗。請檢查 API Key 是否有效。錯誤：{str(e)}")
else:
    st.error(f"❌ 無法獲取 {ticker} 數據。如果是港股請加 .HK (例: 0700.HK)。")
