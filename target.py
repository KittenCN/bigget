#!/usr/bin/python
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
    df['DIF_MACD'] = dif
    df['MACD'] = macd
    df['SIGNAL_MACD'] = signal

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

def calculate_double_moving_average(data, short_window=40, long_window=100):
    """
    计算双均线指标

    参数:
    data (pd.DataFrame): 包含价格数据的DataFrame
    short_window (int): 快速移动平均线的窗口大小
    long_window (int): 慢速移动平均线的窗口大小

    返回:
    pd.DataFrame: 包含双均线指标的DataFrame
    """
    data['Short_MA'] = data['close'].rolling(window=short_window, min_periods=1).mean()
    data['Long_MA'] = data['close'].rolling(window=long_window, min_periods=1).mean()
    
    return data

def calculate_stochastic_oscillator(data, n=14, m=3):
    """
    计算Stochastic Oscillator指标

    参数:
    data (pd.DataFrame): 包含价格数据的DataFrame
    n (int): %K线的时间周期
    m (int): %D线的移动平均周期

    返回:
    pd.DataFrame: 包含Stochastic Oscillator指标的DataFrame
    """
    data['Lowest_n'] = data['low'].rolling(window=n, min_periods=1).min()
    data['Highest_n'] = data['high'].rolling(window=n, min_periods=1).max()
    
    data['%K'] = ((data['close'] - data['Lowest_n']) / (data['Highest_n'] - data['Lowest_n'])) * 100
    data['%D'] = data['%K'].rolling(window=m, min_periods=1).mean()
    
    return data

def calculate_atr(data, n=14):
    """
    计算ATR指标

    参数:
    data (pd.DataFrame): 包含价格数据的DataFrame
    n (int): ATR的时间周期

    返回:
    pd.DataFrame: 包含ATR指标的DataFrame
    """
    # 计算前一天的收盘价
    data['Previous_Close'] = data['close'].shift(1)
    
    # 计算真实范围
    data['TR'] = data.apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['Previous_Close']), abs(x['low'] - x['Previous_Close'])), axis=1)
    
    # 计算ATR
    data['ATR'] = data['TR'].rolling(window=n, min_periods=1).mean()
    
    # 删除临时列
    data.drop(columns=['TR', 'Previous_Close'], inplace=True)
    
    return data




