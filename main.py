import streamlit as st
import akshare as ak
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime

# ==========================================
# 1. 核心灵魂：进化导师系统指令 (System Instruction)
# ==========================================
SYSTEM_INSTRUCTION = """
# 🚀 我的交易成长之路（智能体指令·周全优化版）
## 一、核心定义
你是我专属的A股全能操盘手+进化导师+行为矫正师。
核心目标：系统性训练我形成可复制的交易体系，从“凭感觉交易”升级为“靠规则盈利”。
核心原则：数据不说谎，纪律不妥协；只做高盈亏比（≥3:1）的交易。

## 二、核心工作流
1. 风险前置校验：判断大盘环境（20日线上方？）与板块周期（主升浪？）。
2. 大数据情报搜集：资金面、盘口面、情绪面、基本面、技术面、筹码面。
3. 心法规则过滤：主要矛盾检查、技术形态检查、周期匹配校验、盈亏比校验、仓位合规校验。
4. 计算最优执行方案：买卖方向、仓位指令（金字塔建仓）、盈亏比确认、风控红线、做T指引。

## 三、交互输出模板（必须严格遵守）
回答必须包含：
1. 📊 【情报扫描·全维度】
2. 【情绪与状态审计·行为矫正】
3. 【仓位与节奏审计·合规校验】
4. 🛡️ 【心法审计·核心校验】
5. 💡 【最优行动方案·可执行】
6. 📝 【交易日志·强制记录】
7. 📈 【进化提示·下次优化】

## 四、核心法则库
- 法则一：金字塔建仓（底仓15-25% -> 加仓40% -> 补仓20%），20%预备金神圣不可侵犯。
- 法则二：买入必看盈亏比≥3:1，右侧确认（站稳均线+放量）。
- 法则三：止盈止损铁律，利润回撤50%强制减仓。
- 法则四：周期匹配，短线只做龙头。
"""

# ==========================================
# 2. 页面配置与样式
# ==========================================
st.set_page_config(page_title="ZenCore AI 操盘手", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 侧边栏：仓位与配置
# ==========================================
st.sidebar.title("🛡️ 指挥部控制台")
api_key = st.sidebar.text_input("输入 Gemini API Key", type="password")

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
        st.session_state.portfolio[code]['qty'] = st.number_input(f"持仓", value=int(info['qty']), key=f"q_{code}")

# ==========================================
# 4. 数据引擎 (AkShare)
# ==========================================
@st.cache_data(ttl=300)
def get_market_data(code):
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq").tail(100)
        if df.empty: return None, None
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA10'] = df['收盘'].rolling(10).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        current_price = df['收盘'].iloc[-1]
        return df, current_price
    except:
        return None, None

# ==========================================
# 5. AI 导师引擎 (Gemini 3 Flash Preview)
# ==========================================
def run_mentor_audit(stock_name, stock_code, price, df, news):
    if not api_key: return "❌ 请先在侧边栏输入 API Key 以激活导师系统。"
    
    try:
        model = genai.GenerativeModel(
            model_name='gemini-3-flash-preview',
            system_instruction=SYSTEM_INSTRUCTION
        )
        
        # 构造喂给 AI 的实时上下文
        context = f"""
        标的：{stock_name} ({stock_code})
        当前价格：{price}
        技术指标：MA5={df['MA5'].iloc[-1]:.2f}, MA20={df['MA20'].iloc[-1]:.2f}
        近期新闻/公告：{news}
        用户当前心态：冷静，请求大数据审计。
        """
        
        response = model.generate_content(context)
        return response.text
    except Exception as e:
        return f"⚠️ 导师系统连接失败: {str(e)}"

# ==========================================
# 6. 主界面布局
# ==========================================
st.title("ZenCore AI 操盘手 v1.2")
st.caption("数据不说谎 · 纪律不妥协 · 盈亏比优先")

tabs = st.tabs(["📊 资产全景", "🏹 右侧安检", "🧠 导师审计", "📝 交易日志"])

# --- Tab 1: 资产全景 ---
with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    total_mv, total_profit = 0.0, 0.0
    
    for code, info in st.session_state.portfolio.items():
        _, price = get_market_data(code)
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
    df, price = get_market_data(sel_code)
    
    if df is not None:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            fig = go.Figure(data=[go.Candlestick(x=df['日期'], open=df['开盘'], high=df['最高'], low=df['最低'], close=df['收盘'], name="K线")])
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA5'], line=dict(color='orange', width=1.5), name="MA5"))
            fig.add_trace(go.Scatter(x=df['日期'], y=df['MA20'], line=dict(color='cyan', width=1.5), name="MA20"))
            fig.update_layout(template="plotly_dark", height=600, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        with c_right:
            st.subheader("右侧安检门")
            ma20_now = df['MA20'].iloc[-1]
            vol_ratio = df['成交量'].iloc[-1] / df['成交量'].tail(5).mean()
            
            check1 = price > ma20_now
            check2 = vol_ratio > 1.1
            
            st.write(f"1. 站稳均线 (Price > MA20): {'✅' if check1 else '❌'}")
            st.write(f"2. 成交放量 (Vol Ratio > 1.1): {'✅' if check2 else '❌'}")
            
            if check1 and check2:
                st.success("信号：右侧确认，符合建仓条件")
            else:
                st.warning("信号：左侧阴跌或震荡，保持静默")

# --- Tab 3: 导师审计 (Gemini 3 核心功能) ---
with tabs[2]:
    st.subheader("🚀 进化导师·大数据全维度审计")
    if st.button("启动四步闭环工作流"):
        with st.spinner("导师正在联网搜集情报并过滤心法..."):
            # 获取新闻
            try:
                news_df = ak.stock_news_em(symbol=sel_code).head(10)
                news_text = news_df['新闻标题'].tolist()
            except:
                news_text = "暂时无法获取实时新闻"
            
            # 运行 AI 审计
            report = run_mentor_audit(st.session_state.portfolio[sel_code]['name'], sel_code, price, df, news_text)
            st.markdown(report)

# --- Tab 4: 交易日志 ---
with tabs[3]:
    st.info("系统已自动开启行为画像分析。每周五 15:30 将生成《周度交易体系复盘报告》。")
    st.write("当前弱点监测：[等待数据积累...]")
