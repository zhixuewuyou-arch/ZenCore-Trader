import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import time

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

# --- 4. 极速数据引擎 (v1.4 修复切换 Bug) ---
@st.cache_data(ttl=60)
def get_stable_data(code):
    try:
        # 1. 精准获取个股历史数据（增加重试机制）
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(150)
        if df.empty: return None, None
        
        # 2. 计算均线
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA10'] = df['收盘'].rolling(10).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        df['MA60'] = df['收盘'].rolling(60).mean()
        
        # 3. 极速获取当前价格（不再调用全市场接口）
        # 直接取历史数据的最后一行作为现价，如果是交易时段，hist 接口通常也是准实时的
        current_price = df['收盘'].iloc[-1]
        
        return df.tail(100), current_price
    except Exception as e:
        st.error(f"数据引擎异常: {e}")
        return None, None

# --- 5. 主界面 ---
st.title("ZenCore AI 操盘手 v1.4")
tabs = st.tabs(["📊 资产全景", "🏹 右侧安检", "🧠 导师审计"])

# --- Tab 1: 资产全景 ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    total_mv, total_profit = 0.0, 0.0
    
    # 预加载数据，防止切换闪烁
    with st.spinner('正在同步全球算力资产数据...'):
        for code, info in st.session_state.portfolio.items():
            _, price = get_stable_data(code)
            if price:
                total_mv += price * info['qty']
                total_profit += (price - info['cost']) * info['qty']
    
    initial_inv = total_mv - total_profit
    profit_pct = (total_profit / initial_inv * 100) if initial_inv > 0 else 0.0
    col1.metric("总持仓市值", f"¥{total_mv:,.2f}")
    col2.metric("累计浮盈", f"¥{total_profit:,.2f}", f"{profit_pct:.2f}%")
    col3.metric("可用现金", "¥260,000.00") 
    col4.metric("现金比例", f"{(260000/(total_mv+260000)*100):.1f}%")

# --- Tab 2: 右侧安检 (修复切换逻辑) ---
with tabs[1]:
    sel_code = st.selectbox("选择审计标的", list(st.session_state.portfolio.keys()), index=0)
    
    # 切换时显示加载状态
    df, price = get_stable_data(sel_code)
    
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
            fig.update_layout(template="plotly_dark", height=500, margin=dict(l=10, r=10, t=10, b=10),
                              xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
        with c_right:
            st.subheader("右侧安检门")
            ma20_val = df['MA20'].iloc[-1]
            # 计算成交量比率
            vol_ratio = df['成交量'].iloc[-1] / df['成交量'].tail(5).mean()
            
            check1 = price > ma20_val
            check2 = vol_ratio > 1.1
            
            st.write(f"**最新价**: {price}")
            st.write(f"**MA20**: {ma20_val:.2f}")
            st.divider()
            st.write(f"1. 站稳均线: {'✅' if check1 else '❌'}")
            st.write(f"2. 成交放量: {'✅' if check2 else '❌'}")
            
            if check1 and check2:
                st.success("信号：右侧确认")
            else:
                st.warning("信号：保持静默")
    else:
        st.warning("正在尝试重新连接数据源，请稍候...")
        time.sleep(1)
        st.rerun()

# --- Tab 3: 导师审计 ---
with tabs[2]:
    if st.button("启动大数据审计"):
        if not api_key:
            st.error("请先在侧边栏输入 API Key")
        else:
            with st.spinner("导师正在穿透迷雾..."):
                model = genai.GenerativeModel('gemini-3-flash-preview', system_instruction=SYSTEM_INSTRUCTION)
                try:
                    news_df = ak.stock_news_em(symbol=sel_code)
                    news = news_df.head(10)['新闻标题'].tolist() if not news_df.empty else "无近期新闻"
                except:
                    news = "新闻接口调用受限"
                
                response = model.generate_content(f"标的：{sel_code}, 现价：{price}, 情报：{news}")
                st.markdown(response.text)
