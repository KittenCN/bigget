

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    # 计算快速和慢速移动平均线
    ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()

    # 计算差离值（DIF）
    dif = ema_fast - ema_slow

    # 计算信号线
    signal = dif.ewm(span=signal_period, adjust=False).mean()

    # 计算MACD指标
    macd = dif - signal

    # 将结果添加到DataFrame中
    df['DIF'] = dif
    df['MACD'] = macd
    df['SIGNAL'] = signal

    return df

def compute_bollinger_bands(data, window=20, num_std=2):
    """
    计算Bollinger Bands
    data: DataFrame，包含收盘价数据
    window: 移动平均线的窗口大小，默认为20
    num_std: 标准差的倍数，默认为2
    返回: DataFrame，包含中轨、上轨和下轨数据
    """
    # 计算中轨
    data['Middle_Band'] = data['close'].rolling(window=window).mean()
    
    # 计算标准差
    data['Rolling_STD'] = data['close'].rolling(window=window).std()
    
    # 计算上轨和下轨
    data['Upper_Band'] = data['Middle_Band'] + (data['Rolling_STD'] * num_std)
    data['Lower_Band'] = data['Middle_Band'] - (data['Rolling_STD'] * num_std)
    
    return data

def compute_rsi(data, window=14):
    """
    计算RSI值
    data: DataFrame，包含收盘价数据
    window: 计算周期，默认为14天
    返回: RSI值列表
    """
    delta = data['close'].diff(1)
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=window, min_periods=1).mean()
    avg_loss = loss.rolling(window=window, min_periods=1).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi