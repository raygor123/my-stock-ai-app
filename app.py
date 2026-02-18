import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置 (最強兼容版) ---
def init_gemini():
    if "GEMINI_API_KEY" not in st.secrets:
        return None, "❌ 找不到 API Key"
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 強制使用 models/ 前綴解決部分 404 問題
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        return model, None
    except Exception as e:
        return None, str(e)

model, ai_error = init_gemini()

st.set_page_config(page_title="AI 短炒王 2026", layout="wide")
st.title("🚀 短炒形態實戰儀表板 (數字流)")

# --- 2. 側邊欄：週期與代碼 ---
ticker = st.sidebar.text_input("代碼 (例: NVDA, 0700.HK)", "TSLA")
time_options = {
    "5分鐘線 (近5日)": {"p": "5d", "i": "5m"},
    "1小時線 (近1週)": {"p": "7d", "i": "60m"},
    "日線 (近半年)": {"p": "6mo", "i": "1d"},
}
selected_label = st.sidebar.selectbox("分析週期", list(time_options.keys()))
p, i = time_options[selected_label]["p"], time_options[selected_label]["i"]

# --- 3. 數據抓取與清洗 ---
@st.cache_data(ttl=60)
def get_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.ffill().dropna()
    except: return None

data = get_data(ticker, p, i)

# --- 4. 核心技術分析 (一定會顯示的部分) ---
if data is not None and len(data) > 30:
    # A. 計算技術指標
    data['RSI'] = ta.rsi(data['Close'], length=14)
    macd = ta.macd(data['Close'])
    bb = ta.bbands(data['Close'], length=20)
    data = pd.concat([data, macd, bb], axis=1)
    
    # B. 提取關鍵數字
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].iloc[-1])
    res = float(data['High'].tail(20).max())
    sup = float(data['Low'].tail(20).min())
    vol_status = "放量" if data['Volume'].iloc[-1] > data['Volume'].tail(10).mean() else "縮量"
    
    # C. **自動算出入場位與止損位** (不依賴 AI)
    entry_price = sup * 1.005 # 支持位上方 0.5%
    stop_loss = sup * 0.97    # 支持位下方 3%
    target_price = res * 0.98  # 壓力位下方 2%

    # D. 顯示儀表板
    st.subheader(f"📊 {ticker} {selected_label} 實戰數據")
    
    # 第一排：入場策略 (最醒目)
    s1, s2, s3 = st.columns(3)
    s1.success(f"🎯 建議入場點: **${entry_price:.2f}**")
    s2.error(f"🛑 嚴格止損位: **${stop_loss:.2f}**")
    s3.info(f"🏁 短期目標價: **${target_price:.2f}**")

    # 第二排：指標數值
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("現價", f"${last_price:.2f}")
    c2.metric("RSI (14)", f"{last_rsi:.1f}")
    c3.metric("壓力位", f"${res:.2f}")
    c4.metric("成交量", vol_status)

    # --- 5. AI 深度形態解說 ---
    st.write("")
    if st.button("🤖 執行 AI 深度圖表形態掃描"):
        if ai_error:
            st.error(f"AI 暫時休息中 (Error: {ai_error})。請參考上方自動計算的入場位。")
        else:
            try:
                with st.spinner('AI 正在識別背馳與形態...'):
                    # 傳送 OHLC 數據讓 AI 找形態
                    history = data[['Open', 'High', 'Low', 'Close']].tail(15).to_string()
                    prompt = (f"你是專業短線交易員。分析股票 {ticker} ({selected_label})。\n"
                              f"數據：現價 {last_price}, RSI {last_rsi}, 壓力 {res}, 支持 {sup}。\n"
                              f"最近15根K線：\n{history}\n"
                              f"請回答：1.目前是什麼圖表形態？ 2.是否有 RSI 或 MACD 背馳？ 3.綜合買賣評分 (1-10)。")
                    response = model.generate_content(prompt)
                    st.warning(response.text)
            except Exception as e:
                st.error(f"AI 呼叫失敗，請檢查 Key 是否正確。{str(e)}")
else:
    st.error("❌ 抓不到數據。如果是港股請加 .HK (例: 0005.HK)。")
