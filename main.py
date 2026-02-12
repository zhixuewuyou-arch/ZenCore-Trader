import yfinance as yf

@st.cache_data(ttl=300)
def get_global_data(code):
    try:
        # 转换 A 股代码格式：688041 -> 688041.SS, 300308 -> 300308.SZ
        suffix = ".SS" if code.startswith(('60', '68')) else ".SZ"
        symbol = code + suffix
        
        # 获取数据
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6mo")
        
        if df.empty: return None, None
        
        # 统一字段名
        df = df.reset_index()
        df.columns = ['日期', '开盘', '最高', '最低', '收盘', '成交量', 'Dividends', 'Stock Splits']
        
        # 计算均线
        df['MA5'] = df['收盘'].rolling(5).mean()
        df['MA20'] = df['收盘'].rolling(20).mean()
        
        current_price = df['收盘'].iloc[-1]
        return df.tail(100), round(current_price, 2)
    except:
        return None, None
