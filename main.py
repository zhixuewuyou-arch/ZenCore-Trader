import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 页面配置 ---
st.set_page_config(page_title="ZenCore AI 操盘手", layout="wide", page_icon="📈")

# 自定义黑金风格 CSS
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 侧边栏：仓位管理 ---
st.sidebar.title("🛡️ 仓位指挥部")
api_key = st.sidebar.text_input("输入 Gemini API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)

st.sidebar.subheader("当前持仓配置")
# 默认核心票池数据
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {
        "688041": {"name": "海光信息", "cost": 224.97, "qty": 920},
        "603019": {"name": "中科曙光", "cost": 102.45, "qty": 1400},
        "300059": {"name": "东方财富", "cost": 25.00, "qty": 9200}
    }

# 允许手动修改仓位
for code, info in st.session_state.portfolio.items():
    with st.sidebar.expander(f"{info['name']} ({code})"):
        new_cost = st.number_input(f"成本价", value=info['cost'], key=f"cost_{code}")
        new_qty = st.number_input(f"持仓数", value=info['qty'], key=f"qty_{code}")
        st.session_state.portfolio[code]['cost'] = new_cost
        st.session_state.portfolio[code]['qty'] = new_qty

# --- 3. 核心数据引擎 (AkShare) ---
@st.cache_data(ttl=60) # 缓存1分钟，避免频繁请求被封
def get_realtime_data(code):
    try:
        # 获取日线数据
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(60)
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        # 获取实时快照
        spot = ak.stock_zh_a_spot_em()
        current_price = spot[spot['代码'] == code]['最新价'].values[0]
        return df, current_price
    except:
        return None, None

# --- 4. AI 审计引擎 (Gemini) ---
def ai_audit(news_list, context_type="news"):
    if not api_key: return "请先在侧边栏输入 API Key"
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    你是一个冷酷的职业操盘手审计员。请对以下{context_type}进行去噪处理：
    1. 提取硬核事实（订单、技术、财务数据）。
    2. 剔除所有情绪化噪音（暴涨、看好、利好等）。
    3. 用一句话给出客观结论。
    内容如下：{news_list}
    """
    response = model.generate_content(prompt)
    return response.text

# --- 5. 主界面展示 ---
st.title("ZenCore AI 操盘手 v1.0")
st.caption("屏蔽噪音 · 只做信号 · 专注核心资产")

tabs = st.tabs(["📊 资产全景", "🏹 右侧安检", "🧠 去噪情报", "📝 交易日志"])

# --- Tab 1: 资产全景 ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    total_market_value = 0
    total_profit = 0
    
    # 遍历持仓计算
    for code, info in st.session_state.portfolio.items():
        _, price = get_realtime_data(code)
        if price:
            mv = price * info['qty']
            profit = (price - info['cost']) * info['qty']
            total_market_value += mv
            total_profit += profit
    
    # --- 修复 ZeroDivisionError 的逻辑 ---
    initial_investment = total_market_value - total_profit
    
    # 安全计算百分比
    if initial_investment > 0:
        profit_pct = (total_profit / initial_investment) * 100
        profit_pct_str = f"{profit_pct:.2f}%"
    else:
        profit_pct_str = "0.00%"

    # 显示指标
    col1.metric("总持仓市值", f"¥{total_market_value:,.2f}")
    col2.metric("累计浮盈", f"¥{total_profit:,.2f}", profit_pct_str)
    col3.metric("可用现金", "¥260,000.00") 
    col4.metric("现金比例", "26.0%")

# --- Tab 2: 右侧安检 ---
with tabs[1]:
    selected_code = st.selectbox("选择审计标的", list(st.session_state.portfolio.keys()))
    df, price = get_realtime_data(selected_code)
    
    if df is not None:
        col_left, col_right = st.columns([3, 1])
        
        with col_left:
            # 绘制 K 线
            fig = go.Figure(data=[go.Candlestick(x=df['日期'], open=df['开盘'], high=df['最高'], low=df['最低'], close=df['收盘'], name="K线")])
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA5'], line=dict(color='orange', width=1), name="MA5"))
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA20'], line=dict(color='cyan', width=1), name="MA20"))
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
        with col_right:
            st.subheader("右侧安检门")
            ma20_val = df['MA20'].iloc[-1]
            vol_ratio = df['成交量'].iloc[-1] / df['成交量'].tail(5).mean()
            
            c1 = price > ma20_val
            c2 = vol_ratio > 1.2
            
            st.write(f"1. 站稳均线: {'✅' if c1 else '❌'}")
            st.write(f"2. 放量上涨: {'✅' if c2 else '❌'}")
            
            if c1 and c2:
                st.success("信号：右侧确认，允许操作")
            else:
                st.error("信号：禁止入场，保持静默")

# --- Tab 3: 去噪情报 ---
with tabs[2]:
    st.subheader("AI 实时去噪简报")
    if st.button("开始大数据审计"):
        # 模拟抓取最新公告标题（实际可对接 ak.stock_news_em）
        news = ak.stock_news_em(symbol=selected_code).head(5)['新闻标题'].tolist()
        with st.spinner("Gemini 正在穿透迷雾..."):
            report = ai_audit(news)
            st.info(report)

# --- Tab 4: 交易日志 ---
with tabs[3]:
    st.write("本周健康体检：待生成 (每周五 15:30 自动开启)")
    # 这里可以添加一个简单的表格记录操作
