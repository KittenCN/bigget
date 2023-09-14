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

def record_signal(record_long_signal, recore_short_signal):
    content = "close_long,{}\nclose_short,{}".format(record_long_signal, recore_short_signal)
    write_txt("./signal.txt", content, rewrite=True)

def get_time(days=2):
    current_timestamp = int(time.time())
    now = datetime.now(timezone.utc)
    begin = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=days)
    begin_timestamp = int(begin.timestamp())

    return (current_timestamp + 1) * 1000, begin_timestamp * 1000

def get_candles(marketApi, symbol, startTime, endTime, granularity="5m", limit=1000, print_info=False, market_id="bitget"):
    _data = []
    if market_id == "binance":
        result = marketApi.klines(symbol=symbol, interval=granularity, startTime=startTime, endTime=endTime, limit=limit)
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[5])))
    elif market_id == "bitget":
        result = marketApi.candles(symbol=symbol, granularity=granularity, startTime=startTime, endTime=endTime, limit=limit, print_info=print_info)
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6])))
    return _data

def get_ticker(marketApi, symbol, print_info=False):
    return marketApi.ticker(symbol=symbol, print_info=print_info)

def get_account(accountApi, symbol, marginCoin, print_info=False):
    return accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=print_info)

def get_place_order(orderApi, symbol, marginCoin, size, side, orderType, timeInForceValue, clientOrderId, print_info=False, presetStopLossPrice=None, presetTakeProfitPrice=None):
    return orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=size, side=side, orderType=orderType, timeInForceValue=timeInForceValue, clientOrderId=clientOrderId, print_info=print_info, presetStopLossPrice=presetStopLossPrice, presetTakeProfitPrice=presetTakeProfitPrice)

# positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False) 
def get_single_position(positionApi, symbol, marginCoin, print_info=False):
    return positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=print_info)