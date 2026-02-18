import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置 (使用最新穩定模型) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
else:
    st.error("❌ 找不到 API Key，請檢查 Secrets 設定。")

st.set_page_config(page_title="全方位短炒分析器", layout="wide")
st.title("🛡️ 實戰級股票技術形態分析器")

# --- 2. 週期選擇 (明確標示數據限制) ---
ticker = st.sidebar.text_input("輸入代碼 (例如: NVDA 或 0700.HK)", "TSLA")

time_options = {
    "1. 短線爆發 (5分鐘線 - 近5日)": {"p": "5d", "i": "5m"},
    "2. 即日走勢 (15分鐘線 - 近1週)": {"p": "7d", "i": "15m"},
    "3. 波段操作 (1小時線 - 近1個月)": {"p": "1mo", "i": "60m"},
    "4. 中線趨勢 (日線 - 近半年)": {"p": "6mo", "i": "1d"},
}
selected_label = st.sidebar.selectbox("切換時間週期", list(time_options.keys()))
p = time_options[selected_label]["p"]
i = time_options[selected_label]["i"]

# --- 3. 穩定數據抓取函數 ---
@st.cache_data(ttl=60)
def fetch_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty: return None
        
        # 修正 yfinance 的 MultiIndex 問題，確保指標能正常計算
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.ffill().dropna()
        return df
    except Exception:
        return None

data = fetch_data(ticker, p, i)

# --- 4. 數據顯示與技術運算 ---
if data is not None and len(data) > 20:
    # 計算 RSI, MACD, 布林帶
    data['RSI'] = ta.rsi(data['Close'], length=14)
    macd_df = ta.macd(data['Close'])
    bbands = ta.bbands(data['Close'], length=20, std=2)
    data = pd.concat([data, macd_df, bbands], axis=1)
    
    # 取得最新數值
    curr_price = float(data['Close'].iloc[-1])
    curr_rsi = float(data['RSI'].dropna().iloc[-1])
    # 抓取 MACD 柱狀圖數值 (排除空值)
    h_col = [c for c in data.columns if 'MACDh' in c][0]
    curr_h = float(data[h_col].dropna().iloc[-1])
    
    # 動態顯示時間戳
    last_time = data.index[-1].strftime('%Y-%m-%d %H:%M')
    st.info(f"📅 **數據更新時間 ({selected_label})**: {last_time}")

    # --- 數據儀表板 ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("當前價格", f"${curr_price:.2f}")
    col2.metric("RSI 指標", f"{curr_rsi:.1f}")
    col3.metric("MACD 能量", f"{curr_h:.3f}")
    col4.metric("成交量", f"{int(data['Volume'].iloc[-1]):,}")

    st.markdown("---")
    
    # --- 5. AI 形態分析 ---
    if st.button("🔍 執行 AI 深度圖表形態掃描"):
        try:
            with st.spinner('AI 正在識別 K 線形態與背馳...'):
                # 將最近 15 根 K 線的簡要數據傳給 AI，讓它自己找形態
                recent_data = data[['Open', 'High', 'Low', 'Close']].tail(15).to_string()
                prompt = (
                    f"你是資深技術分析師。分析股票 {ticker} 在 {selected_label} 的表現：\n"
                    f"最新數據：價格 {curr_price}, RSI {curr_rsi}, MACD柱 {curr_h}。\n"
                    f"最近15根K線數據：\n{recent_data}\n\n"
                    f"請繁體中文回答：\n"
                    f"1. 識別具體形態 (如: 雙底、黃昏之星、收斂三角形等)\n"
                    f"2. 是否有 RSI 或 MACD 背馳？\n"
                    f"3. 具體支撐位與壓力位\n"
                    f"4. 建議操作策略與止損價格。"
                )
                response = model.generate_content(prompt)
                st.warning(response.text)
        except Exception as e:
            st.error("AI 分析目前遇到問題，請稍後再試。")
else:
    st.error(f"❌ 無法獲取 {ticker} 的數據。請確認代碼 (如 NVDA 或 0700.HK) 是否正確，或該時間週期暫無數據。")
