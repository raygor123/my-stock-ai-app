import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import google.generativeai as genai

# --- 1. AI 配置 (修正 NotFound 報錯) ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 確保使用目前最穩定的模型名稱
    model = genai.GenerativeModel('gemini-1.5-flash') 
else:
    st.error("❌ 未偵測到 API Key，請檢查 Streamlit Secrets 設定。")

st.set_page_config(page_title="短炒數據專家", layout="wide")
st.title("⚡ 專業短炒數據儀表板")

# --- 2. 側邊欄設定 ---
ticker = st.sidebar.text_input("輸入代碼 (如: NVDA, 0700.HK)", "TSLA")

# 優化短線抓取參數，確保 5d/5m 能成功抓取
time_options = {
    "1. 極短線 (5分鐘線 - 近5日)": {"p": "5d", "i": "5m"},
    "2. 小時線 (1小時圖 - 近1週)": {"p": "7d", "i": "60m"},
    "3. 短波段 (日線 - 近5日)": {"p": "5d", "i": "1d"},
}
selected_range = st.sidebar.selectbox("分析週期", list(time_options.keys()))
p = time_options[selected_range]["p"]
i = time_options[selected_range]["i"]

@st.cache_data(ttl=60)
def get_clean_data(symbol, period, interval):
    try:
        # 抓取數據並自動處理多層索引
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty:
            return pd.DataFrame()
        
        # 修正 yfinance 新版索引問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.ffill().dropna()
        return df
    except Exception:
        return pd.DataFrame()

data = get_clean_data(ticker, p, i)

# --- 3. 數據運算 ---
if not data.empty and len(data) > 10:
    # 計算 RSI
    data['RSI'] = ta.rsi(data['Close'], length=14)
    # 計算 MACD
    macd = ta.macd(data['Close'])
    data = pd.concat([data, macd], axis=1)
    
    # 阻力支持
    res = float(data['High'].tail(15).max())
    sup = float(data['Low'].tail(15).min())
    
    last_price = float(data['Close'].iloc[-1])
    last_rsi = float(data['RSI'].dropna().iloc[-1])
    # 尋找 MACD 柱狀圖欄位名
    h_col = [c for c in data.columns if 'MACDh' in c][0]
    last_h = float(data[h_col].iloc[-1])

    # --- 4. 顯示數字指標 ---
    st.subheader(f"📊 {ticker} 關鍵數據")
    c1, c2, c3 = st.columns(3)
    c1.metric("現價", f"${last_price:.2f}")
    c2.metric("RSI (14)", f"{last_rsi:.1f}")
    c3.metric("MACD 柱", f"{last_h:.3f}")

    st.markdown("---")
    sc1, sc2 = st.columns(2)
    sc1.error(f"🔴 短期壓力: ${res:.2f}")
    sc2.success(f"🟢 短期支撐: ${sup:.2f}")

    # --- 5. AI 分析按鈕 (修正 NotFound) ---
    if st.button("🤖 獲取 AI 短炒策略"):
        try:
            with st.spinner('AI 分析中...'):
                prompt = (f"分析股票 {ticker}：現價 {last_price:.2f}, RSI {last_rsi:.1f}, "
                          f"壓力 {res:.2f}, 支撐 {sup:.2f}。請簡短給出背馳判斷與操作建議。")
                response = model.generate_content(prompt)
                st.warning(response.text)
        except Exception as e:
            st.error(f"AI 服務暫時不可用，請檢查 API Key。錯誤訊息: {str(e)}")
else:
    st.info("🕒 目前無法獲取該週期的數據。提示：5分鐘線僅限最近 60 天內數據。")
