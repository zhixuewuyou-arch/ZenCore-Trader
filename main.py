import streamlit as st
import akshare as ak
import efinance as ef
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import time
import random

# --- 1. 系统指令 ---
SYSTEM_INSTRUCTION = """你是我专属的A股全能操盘手+进化导师。请严格按照用户提供的《交易成长之路》逻辑进行审计。"""

# --- 2. 页面配置 ---
st.set_page_config(page_title="ZenCore AI 操盘手", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. 侧边栏 ---
st.sidebar.title("🛡️ 指挥部控制台")
api_key = st.sidebar.text_input("输入 Gemini API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {
        "688041": {"name": "海光信息", "cost": 224.97, "qty": 920},
        "603019": {"name": "中科曙光", "cost": 102.45, "qty": 1400},
        "300059": {"name": "东方财富", "cost": 25.00, "qty": 9200}
    }

for code, info in st.session_state.portfolio.items():
    with st.sidebar.expander(f"{info['name']} ({code})"):
        st.session_state.portfolio[code]['cost'] = st.number_input(f"成本", value=info['cost'], key=f"c_{code}")
        st.session_state.portfolio[code]['qty'] = st.number_input(f"持仓", value=int(info['qty']), key=f"q_{code}")

# --- 4. 强韧数据引擎 (v1.5 解决云端连接中断) ---
@st.cache_data(ttl=120)
def get_resilient_data(code):
    # 尝试使用 efinance 引擎 (在云端更稳定)
    try:
        df = ef.stock.get_quote_history(code).tail(150)
        if df.empty: raise ValueError("Empty Data")
        
        # 统一字段名
        df = df.rename(columns={
            '日期': '日期', '开盘': '开盘', '收盘': '收盘', 
            '最高': '最高', '最低': '最低', '成交量': '成交量'
        })
        
        # 计算均线
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA10'] = df['收盘'].rolling(10).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        df['MA60'] = df['收盘'].rolling(60).mean()
        
        current_price = df['收盘'].iloc[-1]
        return df.tail(100), current_price
    
    except Exception as e:
        # 如果 efinance 失败，尝试 akshare 的备用接口
        try:
            time.sleep(random.uniform(0.5, 1.5)) # 随机延迟防封
            df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(150)
            df['MA5'] = df['收盘'].rolling(5).mean()
            df['MA10'] = df['收盘'].rolling(10).mean()
            df['MA20'] = df['收盘'].rolling(20).mean()
            df['MA60'] = df['收盘'].rolling(60).mean()
            return df.tail(100), df['收盘'].iloc[-1]
        except:
            return None, None

# --- 5. 主界面 ---
st.title("ZenCore AI 操盘手 v1.5")
tabs = st.tabs(["📊 资产全景", "🏹 右侧安检", "🧠 导师审计"])

# --- Tab 1: 资产全景 ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    total_mv, total_profit = 0.0, 0.0
    
    # 增加重试逻辑
    data_load_success = True
    for code, info in st.session_state.portfolio.items():
        df, price = get_resilient_data(code)
        if price:
            total_mv += price * info['qty']
            total_profit += (price - info['cost']) * info['qty']
        else:
            data_load_success = False

    if not data_load_success:
        st.warning("⚠️ 部分数据源连接受限，正在尝试通过备用通道解析...")
    
    initial_inv = total_mv - total_profit
    profit_pct = (total_profit / initial_inv * 100) if initial_inv > 0 else 0.0
    col1.metric("总持仓市值", f"¥{total_mv:,.2f}")
    col2.metric("累计浮盈", f"¥{total_profit:,.2f}", f"{profit_pct:.2f}%")
    col3.metric("可用现金", "¥260,000.00") 
    col4.metric("现金比例", f"{(260000/(total_mv+260000)*100):.1f}%" if (total_mv+260000)>0 else "100%")

# --- Tab 2: 右侧安检 ---
with tabs[1]:
    sel_code = st.selectbox("选择审计标的", list(st.session_state.portfolio.keys()))
    df, price = get_resilient_data(sel_code)
    
    if df is not None:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            fig = go.Figure(data=[go.Candlestick(
                x=df['日期'], open=df['开盘'], high=df['最高'], low=df['最低'], close=df['收盘'],
                name="K线", increasing_line_color='#ef5350', decreasing_line_color='#26a69a'
            )])
            colors = {'MA5': 'white', 'MA10': 'yellow', 'MA20': 'magenta', 'MA60': 'cyan'}
            for ma in ['MA5', 'MA10', 'MA20', 'MA60']:
                fig.add_trace(go.Scatter(x=df['日期'], y=df[ma], line=dict(color=colors[ma], width=1), name=ma))
            
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])]) 
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with c_right:
            st.subheader("右侧安检门")
            ma20_val = df['MA20'].iloc[-1]
            vol_ratio = df['成交量'].iloc[-1] / df['成交量'].tail(5).mean()
            
            check1 = price > ma20_val
            check2 = vol_ratio > 1.1
            
            st.write(f"**最新价**: {price}")
            st.write(f"**MA20**: {ma20_val:.2f}")
            st.divider()
            st.write(f"1. 站稳均线: {'✅' if check1 else '❌'}")
            st.write(f"2. 成交放量: {'✅' if check2 else '❌'}")
            if check1 and check2: st.success("信号：右侧确认")
            else: st.warning("信号：保持静默")
    else:
        st.error("❌ 无法连接到行情服务器。请尝试刷新页面或稍后再试。")

# --- Tab 3: 导师审计 ---
with tabs[2]:
    if st.button("启动大数据审计"):
        if not api_key:
            st.error("请先在侧边栏输入 API Key")
        else:
            with st.spinner("导师正在穿透迷雾..."):
                model = genai.GenerativeModel('gemini-3-flash-preview', system_instruction=SYSTEM_INSTRUCTION)
                # 简化新闻获取，降低封禁风险
                news = f"标的：{sel_code}，当前价格：{price}。请结合全维度大数据给出审计建议。"
                response = model.generate_content(news)
                st.markdown(response.text)
