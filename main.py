import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import google.generativeai as genai
import time
from datetime import datetime
import yfinance as yf

# --- 1. 系统指令 (注入 2026 年时间锚点) ---
SYSTEM_INSTRUCTION = f"""
你是我专属的A股全能操盘手+进化导师。
当前时间是：{datetime.now().strftime('%Y-%m-%d')}。
请严格按照用户提供的《交易成长之路》逻辑进行审计。
注意：如果实时数据缺失，请明确告知用户，严禁使用 2024 年以前的陈旧价格进行误导。
"""

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
        "688041": {"name": "海光信息", "cost": 224.97, "qty": 920, "mkt": "1"},
        "603019": {"name": "中科曙光", "cost": 102.45, "qty": 1400, "mkt": "1"},
        "300059": {"name": "东方财富", "cost": 25.00, "qty": 9200, "mkt": "0"}
    }

for code, info in st.session_state.portfolio.items():
    with st.sidebar.expander(f"{info['name']} ({code})"):
        st.session_state.portfolio[code]['cost'] = st.number_input(f"成本", value=info['cost'], key=f"c_{code}")
        st.session_state.portfolio[code]['qty'] = st.number_input(f"持仓", value=int(info['qty']), key=f"q_{code}")

# --- 4. 核心数据引擎 (v1.7 破壁者：增加 Header 伪装) ---
@st.cache_data(ttl=120)
def get_api_data_v2(code, mkt):
    try:
        # 增加浏览器伪装 Header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        }
        # 更换更稳定的 API 节点
        url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={mkt}.{code}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=120"
        
        response = requests.get(url, headers=headers, timeout=10)
        json_data = response.json()
        
        if not json_data['data']: return None, None
        
        klines = json_data['data']['klines']
        df = pd.DataFrame([x.split(',') for x in klines], columns=['日期','开盘','收盘','最高','最低','成交量','成交额','振幅','涨跌幅','涨跌额','换手率'])
        df[['开盘','收盘','最高','最低','成交量']] = df[['开盘','收盘','最高','最低','成交量']].apply(pd.to_numeric)
        
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        
        current_price = df['收盘'].iloc[-1]
        return df.tail(100), current_price
    except Exception as e:
        return None, None

# --- 5. 主界面 ---
st.title("ZenCore AI 操盘手 v1.7")
tabs = st.tabs(["📊 资产全景", "🏹 右侧安检", "🧠 导师审计"])

# --- Tab 1: 资产全景 ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    total_mv, total_profit = 0.0, 0.0
    
    for code, info in st.session_state.portfolio.items():
        df, price = get_api_data_v2(code, info['mkt'])
        if price:
            total_mv += price * info['qty']
            total_profit += (price - info['cost']) * info['qty']
    
    initial_inv = total_mv - total_profit
    profit_pct = (total_profit / initial_inv * 100) if initial_inv > 0 else 0.0
    col1.metric("总持仓市值", f"¥{total_mv:,.2f}")
    col2.metric("累计浮盈", f"¥{total_profit:,.2f}", f"{profit_pct:.2f}%")
    col3.metric("可用现金", "¥260,000.00") 
    col4.metric("现金比例", f"{(260000/(total_mv+260000)*100):.1f}%" if (total_mv+260000)>0 else "100%")

# --- Tab 2: 右侧安检 ---
with tabs[1]:
    sel_code = st.selectbox("选择审计标的", list(st.session_state.portfolio.keys()))
    info = st.session_state.portfolio[sel_code]
    df, price = get_api_data_v2(sel_code, info['mkt'])
    
    if df is not None:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            fig = go.Figure(data=[go.Candlestick(x=df['日期'], open=df['开盘'], high=df['最高'], low=df['最低'], close=df['收盘'], name="K线")])
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA5'], line=dict(color='orange', width=1), name="MA5"))
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA20'], line=dict(color='cyan', width=1), name="MA20"))
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
        with c_right:
            st.subheader("右侧安检门")
            ma20_val = df['MA20'].iloc[-1]
            st.write(f"**最新价**: {price}")
            st.write(f"**MA20**: {ma20_val:.2f}")
            st.divider()
            check1 = price > ma20_val
            st.write(f"1. 站稳均线: {'✅' if check1 else '❌'}")
            if check1: st.success("信号：右侧确认")
            else: st.warning("信号：保持静默")
    else:
        st.error("❌ 无法获取行情数据。请检查网络或尝试刷新。")

# --- Tab 3: 导师审计 ---
with tabs[2]:
    if st.button("启动大数据审计"):
        if not api_key:
            st.error("请先在侧边栏输入 API Key")
        elif not price:
            st.error("实时行情缺失，导师拒绝在迷雾中审计。请先修复 Tab 2 的数据连接。")
        else:
            with st.spinner("导师正在穿透迷雾..."):
                model = genai.GenerativeModel('gemini-3-flash-preview', system_instruction=SYSTEM_INSTRUCTION)
                audit_context = f"标的：{info['name']}，当前真实价格：{price}。请结合该价格和AI算力行业逻辑给出审计建议。"
                response = model.generate_content(audit_context)
                st.markdown(response.text)
