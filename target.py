import pandas as pd

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