import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai

# --- 1. 页面配置 ---
st.set_page_config(page_title="ZenCore AI 操盘手", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：仓位管理 ---
st.sidebar.title("🛡️ 仓位指挥部")
# 建议在 Streamlit Secrets 中设置 API_KEY，或者手动输入
api_key_input = st.sidebar.text_input("输入 Gemini API Key", type="password")
api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")

if api_key:
    genai.configure(api_key=api_key)

st.sidebar.subheader("当前持仓配置")
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {
        "688041": {"name": "海光信息", "cost": 224.97, "qty": 920},
        "603019": {"name": "中科曙光", "cost": 102.45, "qty": 1400},
        "300059": {"name": "东方财富", "cost": 25.00, "qty": 9200}
    }

for code, info in st.session_state.portfolio.items():
    with st.sidebar.expander(f"{info['name']} ({code})"):
        st.session_state.portfolio[code]['cost'] = st.number_input(f"成本", value=info['cost'], key=f"c_{code}")
        st.session_state.portfolio[code]['qty'] = st.number_input(f"持仓", value=info['qty'], key=f"q_{code}")

# --- 3. 核心数据引擎 (优化版) ---
@st.cache_data(ttl=300) # 缓存5分钟
def get_clean_data(code):
    try:
        # 直接获取日线，包含最新价格
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(60)
        if df.empty: return None, None
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        current_price = df['收盘'].iloc[-1] # 取最后一行作为当前价
        return df, current_price
    except Exception as e:
        return None, None

# --- 4. AI 审计引擎 (修复版) ---
def ai_audit(news_list):
    if not api_key: return "❌ 未检测到 API Key，请在侧边栏输入。"
    try:
        # 使用更稳定的模型名称格式
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"你是一个冷酷的职业操盘手审计员。请对以下新闻去噪，提取硬核事实，剔除情绪噪音，一句话总结结论：{news_list}"
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"⚠️ AI 审计暂时不可用: {str(e)}"

# --- 5. 主界面 ---
st.title("ZenCore AI 操盘手 v1.1")
tabs = st.tabs(["📊 资产全景", "🏹 右侧安检", "🧠 去噪情报", "📝 交易日志"])

# --- Tab 1: 资产全景 ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    total_mv, total_profit = 0.0, 0.0
    
    for code, info in st.session_state.portfolio.items():
        _, price = get_clean_data(code)
        if price:
            total_mv += price * info['qty']
            total_profit += (price - info['cost']) * info['qty']
    
    initial_inv = total_mv - total_profit
    profit_pct = (total_profit / initial_inv * 100) if initial_inv > 0 else 0.0

    col1.metric("总持仓市值", f"¥{total_mv:,.2f}")
    col2.metric("累计浮盈", f"¥{total_profit:,.2f}", f"{profit_pct:.2f}%")
    col3.metric("可用现金", "¥260,000.00") 
    col4.metric("现金比例", "26.0%")

# --- Tab 2: 右侧安检 ---
with tabs[1]:
    sel_code = st.selectbox("选择审计标的", list(st.session_state.portfolio.keys()))
    df, price = get_clean_data(sel_code)
    
    if df is not None:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            fig = go.Figure(data=[go.Candlestick(x=df['日期'], open=df['开盘'], high=df['最高'], low=df['最低'], close=df['收盘'], name="K线")])
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA5'], line=dict(color='orange', width=1), name="MA5"))
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA20'], line=dict(color='cyan', width=1), name="MA20"))
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
        with c_right:
            st.subheader("右侧安检门")
            ma20_now = df['MA20'].iloc[-1]
            vol_ratio = df['成交量'].iloc[-1] / df['成交量'].tail(5).mean()
            
            check1 = price > ma20_now
            check2 = vol_ratio > 1.1
            
            st.write(f"1. 站稳均线: {'✅' if check1 else '❌'}")
            st.write(f"2. 成交放量: {'✅' if check2 else '❌'}")
            if check1 and check2: st.success("信号：右侧确认")
            else: st.error("信号：禁止入场")

# --- Tab 3: 去噪情报 ---
with tabs[2]:
    if st.button("开始大数据审计"):
        try:
            news_df = ak.stock_news_em(symbol=sel_code)
            if not news_df.empty:
                news_list = news_df.head(5)['新闻标题'].tolist()
                st.info(ai_audit(news_list))
            else:
                st.warning("未获取到相关新闻")
        except:
            st.error("新闻接口调用失败")
