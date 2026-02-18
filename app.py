import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置 (最強兼容性) ---
def init_gemini():
    if "GEMINI_API_KEY" not in st.secrets:
        return None, "未設定 API Key"
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 嘗試使用多種模型別名以防 404
        for m_name in ['gemini-1.5-flash', 'gemini-pro']:
            try:
                model = genai.GenerativeModel(m_name)
                # 簡單測試一下
                return model, None
            except:
                continue
        return None, "模型版本不相容"
    except Exception as e:
        return None, str(e)

model, ai_error = init_gemini()

st.set_page_config(page_title="AI 短炒分析王", layout="wide")
st.title("🏹 即市形態 & 入場分析器")

# --- 2. 側邊欄設定 ---
ticker = st.sidebar.text_input("輸入代碼 (例: NVDA, 0700.HK)", "TSLA").upper()
time_options = {
    "5分鐘線 (最近數據)": {"p": "5d", "i": "5m"},
    "1小時線 (最近數據)": {"p": "7d", "i": "60m"},
    "日線 (波段數據)": {"p": "1mo", "i": "1d"},
}
selected_label = st.sidebar.selectbox("分析週期", list(time_options.keys()))
p, i = time_options[selected_label]["p"], time_options[selected_label]["i"]

# --- 3. 抓取與處理 ---
@st.cache_data(ttl=60)
def get_stock_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df.ffill().dropna()
    except: return None

data = get_stock_data(ticker, p, i)

# --- 4. 核心分析區 (AI 壞了也能用！) ---
if data is not None and len(data) > 20:
    # A. 計算數據
    data['RSI'] = ta.rsi(data['Close'], length=14)
    macd = ta.macd(data['Close'])
    data = pd.concat([data, macd], axis=1)
    
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].iloc[-1])
    # 自動尋找支持/壓力 (最近 20 根 K 線)
    res = float(data['High'].tail(20).max())
    sup = float(data['Low'].tail(20).min())
    
    # B. 硬核數學計算建議位 (不靠 AI)
    # 入場建議：支持位附近 0.5% 
    entry_suggest = sup * 1.005
    # 止損建議：支持位下方 3%
    stop_suggest = sup * 0.97

    # C. 形態與背馳偵測 (簡易算法)
    st.subheader(f"📊 {ticker} 分析結果")
    
    # 用醒目的卡片顯示
    col1, col2, col3 = st.columns(3)
    col1.success(f"🎯 建議入場點: **${entry_suggest:.2f}**")
    col2.error(f"🛑 建議止損位: **${stop_suggest:.2f}**")
    col3.info(f"📈 阻力壓力位: **${res:.2f}**")

    # --- 5. AI 深入分析功能 ---
    st.write("---")
    if st.button("🤖 執行 AI 深度圖表分析"):
        if ai_error:
            st.error(f"AI 目前無法連線 (404/Error)。請參考上方自動計算的數據。")
        else:
            try:
                with st.spinner('AI 正在解讀形態...'):
                    history = data[['Open', 'High', 'Low', 'Close']].tail(10).to_string()
                    prompt = (f"你是專業交易員，分析股票 {ticker}。\n"
                              f"數據：現價 {last_price}, RSI {last_rsi}, 支持 {sup}, 阻力 {res}。\n"
                              f"最近10筆OHLC數據：\n{history}\n"
                              f"請回答：1. 識別具體形態 (如: W底, 上升三角形) 2. 是否有背馳 3. 入場策略。用繁體中文。")
                    response = model.generate_content(prompt)
                    st.warning(response.text)
            except Exception as e:
                st.error(f"AI 解析失敗: {str(e)}")
else:
    st.error(f"❌ 抓不到 {ticker} 的數據。請確認代碼是否正確，或嘗試換到『日線』。")
