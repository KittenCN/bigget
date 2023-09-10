#!/usr/bin/python
import os
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from bitget.consts import CONTRACT_WS_URL
from bitget.ws.bitget_ws_client import BitgetWsClient

signal_weight = {"MACD": 0.3, "BOLL": 0.3, "RSI": 0.2, "MA_sig": 0.1, "MA_Pos": 0.2}

class element_data:
    def __init__(self, time, open, high, low, close, volume1, volume2):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume1 = volume1
        self.volume2 = volume2

def read_txt(file_path):
    if not os.path.exists(file_path):
        with open(file_path, "w") as file:
            file.write("")
    else:
        result = []
        with open(file_path, "r") as file:
            for line in file:
                result.append(line.strip())
        return result

def write_txt(file_path, content, rewrite=False):
    if not os.path.exists(file_path) or rewrite:
        with open(file_path, "w") as file:
            file.write(content)
    else:
        with open(file_path, 'r+') as file:
            # 读取文件内容
            contents = file.read()
            # 将字符串插入到最后一行
            contents += '\n' + content
            # 将文件指针移到文件末尾
            file.seek(0, 2)
            # 写入文件
            file.write(contents)

def handel_error(message):
    print("handle_error:" + message)

def login_bigget(api_key, secret_key, passphrase):
    client = BitgetWsClient(CONTRACT_WS_URL, need_login=True) \
        .api_key(api_key) \
        .api_secret_key(secret_key) \
        .passphrase(passphrase) \
        .error_listener(handel_error) \
        .build()
    return client

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