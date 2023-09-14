#!/usr/bin/python
import os
import time
import numpy as np
from datetime import datetime, timezone, timedelta

signal_weight = {"MACD": 0.15, "BOLL": 0.10, "RSI": 0.10, "MA": 0.15, "SO": 0.10, "ATR": 0.15, "OBV": 0.15, "MFI": 0.10}
Signals = {"Signal_MACD":"MACD", "Signal_Boll":"BOLL", "Signal_RSI":"RSI", "Position_MA":"MA", \
           "Signal_SO":"SO", "Signal_ATR":"ATR", "Signal_OBV":"OBV", "Signal_MFI":"MFI"}
price_weight = [-1, -0.6, 0.6, 1]
price_rate = [1.0, 0.5, 0.5, 1.0]
presetTakeProfitPrice_rate = [0.1, 0.05, 0.05, 0.1]
presetStopLossPrice_rate = [0.2, 0.2, 0.2, 0.2]
fee_rate = 0.00084
signal_windows = 3

class element_data:
    def __init__(self, time, open, high, low, close, volume1, volume2):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume1 = volume1
        self.volume2 = volume2

def check_folder(folder):
    # 检查目录是否存在
    if not os.path.exists(folder):
        # 如果目录不存在，则创建目录
        os.makedirs(folder)

def read_txt(file_path):
    if not os.path.exists(file_path):
        with open(file_path, "w") as file:
            file.write("")
        return []
    else:
        result = []
        with open(file_path, "r") as file:
            for line in file:
                result.append(line.strip())
        return result

def write_txt(file_path, content, rewrite=False):
    if not os.path.exists(file_path) or rewrite:
        with open(file_path, "w") as file:
            file.write(content.strip()+ '\n')
    else:
        with open(file_path, 'a') as file:
            # 写入文件
            file.write(content.strip() + '\n')

def get_time(days=2):
    current_timestamp = int(time.time())
    now = datetime.now(timezone.utc)
    begin = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=days)
    begin_timestamp = int(begin.timestamp())

    return (current_timestamp + 1) * 1000, begin_timestamp * 1000

def macd_signals(data):
    """
    使用MACD判断买入和卖出信号
    data: DataFrame，包含MACD, SIGNAL, close列
    返回: 一个DataFrame，包含买入和卖出信号
    """
    buy_signals = []
    sell_signals = []
    
    # 状态变量，用于跟踪上一个交叉点
    last_cross = "none"

    for i in range(1, len(data)):
        
        # 金叉买入信号
        if data['MACD'].iloc[i] > data['SIGNAL_MACD'].iloc[i] and data['MACD'].iloc[i-1] <= data['SIGNAL_MACD'].iloc[i-1]:
            buy_signals.append(data['close'].iloc[i])
            sell_signals.append(None)
            last_cross = "gold"
            
        # 死叉卖出信号
        elif data['MACD'].iloc[i] < data['SIGNAL_MACD'].iloc[i] and data['MACD'].iloc[i-1] >= data['SIGNAL_MACD'].iloc[i-1]:
            sell_signals.append(data['close'].iloc[i])
            buy_signals.append(None)
            last_cross = "dead"
            
        # MACD零线交叉
        elif (data['MACD'].iloc[i] > 0 and data['MACD'].iloc[i-1] <= 0 and last_cross != "gold") or \
             (data['MACD'].iloc[i] < 0 and data['MACD'].iloc[i-1] >= 0 and last_cross != "dead"):
            if last_cross == "none":
                buy_signals.append(None)
                sell_signals.append(None)
            elif last_cross == "gold":
                sell_signals.append(data['close'].iloc[i])
                buy_signals.append(None)
            elif last_cross == "dead":
                buy_signals.append(data['close'].iloc[i])
                sell_signals.append(None)
        
        # 顶部背离
        elif data['close'].iloc[i] > data['close'].iloc[i-1] and data['MACD'].iloc[i] <= data['MACD'].iloc[i-1]:
            sell_signals.append(data['close'].iloc[i])
            buy_signals.append(None)
            
        # 底部背离
        elif data['close'].iloc[i] < data['close'].iloc[i-1] and data['MACD'].iloc[i] >= data['MACD'].iloc[i-1]:
            buy_signals.append(data['close'].iloc[i])
            sell_signals.append(None)
        
        else:
            buy_signals.append(None)
            sell_signals.append(None)

    # 插入None到第一行，因为我们从第二行开始判断
    buy_signals.insert(0, None)
    sell_signals.insert(0, None)

    data['Buy_Signal_MACD'] = buy_signals
    data['Sell_Signal_MACD'] = sell_signals

    data['Signal_MACD'] = 0
    data.loc[data['Buy_Signal_MACD'].notnull(), 'Signal_MACD'] = 1
    data.loc[data['Sell_Signal_MACD'].notnull(), 'Signal_MACD'] = -1

    
    return data

def bollinger_signals(data):
    """
    使用Bollinger Bands判断买入和卖出信号
    data: DataFrame，包含close, Middle_Band, Upper_Band, Lower_Band列
    返回: 一个DataFrame，包含买入和卖出信号
    """
    buy_signals = []
    sell_signals = []

    for i in range(1, len(data)):
        
        # 价格从下轨突破到中轨（买入信号）
        if data['close'].iloc[i] > data['Middle_Band'].iloc[i] and data['close'].iloc[i-1] <= data['Lower_Band'].iloc[i-1]:
            buy_signals.append(data['close'].iloc[i])
            sell_signals.append(None)
        
        # 价格从上轨突破到中轨（卖出信号）
        elif data['close'].iloc[i] < data['Middle_Band'].iloc[i] and data['close'].iloc[i-1] >= data['Upper_Band'].iloc[i-1]:
            sell_signals.append(data['close'].iloc[i])
            buy_signals.append(None)
            
        # 价格触及下轨并反弹（买入信号）
        elif data['close'].iloc[i] > data['Lower_Band'].iloc[i] and data['close'].iloc[i-1] <= data['Lower_Band'].iloc[i-1]:
            buy_signals.append(data['close'].iloc[i])
            sell_signals.append(None)
        
        # 价格触及上轨并回落（卖出信号）
        elif data['close'].iloc[i] < data['Upper_Band'].iloc[i] and data['close'].iloc[i-1] >= data['Upper_Band'].iloc[i-1]:
            sell_signals.append(data['close'].iloc[i])
            buy_signals.append(None)
        
        else:
            buy_signals.append(None)
            sell_signals.append(None)

    # 插入None到第一行，因为我们从第二行开始判断
    buy_signals.insert(0, None)
    sell_signals.insert(0, None)

    data['Buy_Signal_Boll'] = buy_signals
    data['Sell_Signal_Boll'] = sell_signals
    
    data['Signal_Boll'] = 0
    data.loc[data['Buy_Signal_Boll'].notnull(), 'Signal_Boll'] = 1
    data.loc[data['Sell_Signal_Boll'].notnull(), 'Signal_Boll'] = -1

    return data

def rsi_signals(data, window=14):
    """
    使用RSI判断买入和卖出信号
    data: DataFrame，包含收盘价数据
    window: RSI计算周期，默认为14天
    返回: 一个DataFrame，包含买入和卖出信号
    """
    buy_signals = []
    sell_signals = []

    for i in range(1, len(data)):
        
        # 从超卖区域上升（买入信号）
        if data['RSI'].iloc[i] > 30 and data['RSI'].iloc[i-1] <= 30:
            buy_signals.append(data['close'].iloc[i])
            sell_signals.append(None)
        
        # 从超买区域下降（卖出信号）
        elif data['RSI'].iloc[i] < 70 and data['RSI'].iloc[i-1] >= 70:
            sell_signals.append(data['close'].iloc[i])
            buy_signals.append(None)
        
        # RSI背离（买入信号）
        elif data['close'].iloc[i] < data['close'].iloc[i-1] and data['RSI'].iloc[i] > data['RSI'].iloc[i-1]:
            buy_signals.append(data['close'].iloc[i])
            sell_signals.append(None)
        
        # RSI背离（卖出信号）
        elif data['close'].iloc[i] > data['close'].iloc[i-1] and data['RSI'].iloc[i] < data['RSI'].iloc[i-1]:
            sell_signals.append(data['close'].iloc[i])
            buy_signals.append(None)
            
        else:
            buy_signals.append(None)
            sell_signals.append(None)

    # 插入None到第一行，因为我们从第二行开始判断
    buy_signals.insert(0, None)
    sell_signals.insert(0, None)

    data['Buy_Signal_RSI'] = buy_signals
    data['Sell_Signal_RSI'] = sell_signals
    
    data['Signal_RSI'] = 0
    data.loc[data['Buy_Signal_RSI'].notnull(), 'Signal_RSI'] = 1
    data.loc[data['Sell_Signal_RSI'].notnull(), 'Signal_RSI'] = -1

    return data

def generate_trading_signals(data):
    """
    生成交易信号

    参数:
    data (pd.DataFrame): 包含双均线指标的DataFrame

    返回:
    pd.DataFrame: 包含交易信号的DataFrame
    """
    data['Signal_MA'] = 0
    data['Signal_MA'] = np.where(data['Short_MA'] > data['Long_MA'], 1.0, 0.0)   
    data['Position_MA'] = data['Signal_MA'].diff()
    
    return data

def generate_stochastic_signals(data):
    """
    生成基于Stochastic Oscillator指标的交易信号

    参数:
    data (pd.DataFrame): 包含Stochastic Oscillator指标的DataFrame

    返回:
    pd.DataFrame: 包含交易信号的DataFrame
    """
    # 初始化信号列
    data['Signal_SO'] = 0
    
    # 生成买入信号
    data.loc[((data['%K'] < data['%D']) & (data['%K'].shift(1) > data['%D'].shift(1))) & (data['%D'] > 80), 'Signal_SO'] = 1
    
    # 生成卖出信号
    data.loc[((data['%K'] > data['%D']) & (data['%K'].shift(1) < data['%D'].shift(1))) & (data['%D'] < 20), 'Signal_SO'] = -1
    
    return data

def generate_atr_signals(data, ma_period=20, atr_multiplier=1.5):
    """
    生成基于ATR通道的交易信号

    参数:
    data (pd.DataFrame): 包含价格数据和ATR指标的DataFrame
    ma_period (int): 移动平均的时间周期
    atr_multiplier (float): ATR乘数

    返回:
    pd.DataFrame: 包含交易信号的DataFrame
    """
    # 计算移动平均
    data['MA_ATR'] = data['close'].rolling(window=ma_period, min_periods=1).mean()
    
    # 计算ATR通道
    data['Upper_Channel_ATR'] = data['MA_ATR'] + (data['ATR'] * atr_multiplier)
    data['Lower_Channel_ATR'] = data['MA_ATR'] - (data['ATR'] * atr_multiplier)
    
    # 生成交易信号
    data['Signal_ATR'] = 0
    data.loc[data['close'] > data['Upper_Channel_ATR'], 'Signal_ATR'] = 1
    data.loc[data['close'] < data['Lower_Channel_ATR'], 'Signal_ATR'] = -1
    
    return data

def generate_obv_signals(data):
    """
    生成基于OBV指标的交易信号

    参数:
    data (pd.DataFrame): 包含价格数据和OBV指标的DataFrame

    返回:
    pd.DataFrame: 包含交易信号的DataFrame
    """
    # 生成OBV信号
    data['Signal_OBV'] = 0
    data.loc[(data['OBV'] > data['OBV'].shift(1)) & (data['close'] > data['close'].shift(1)), 'Signal_OBV'] = 1
    data.loc[(data['OBV'] < data['OBV'].shift(1)) & (data['close'] < data['close'].shift(1)), 'Signal_OBV'] = -1
    return data

def generate_mfi_signals(data):
    """
    生成基于MFI指标的交易信号

    参数:
    data (pd.DataFrame): 包含价格数据和MFI指标的DataFrame

    返回:
    pd.DataFrame: 包含交易信号的DataFrame
    """
    # 生成交易信号
    data['Signal_MFI'] = 0
    data.loc[(data['MFI'] < 20), 'Signal_MFI'] = 1
    data.loc[(data['MFI'] > 80), 'Signal_MFI'] = -1
    return data