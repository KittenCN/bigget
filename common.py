#!/usr/bin/python
import os
import time
import numpy as np
from datetime import datetime, timezone, timedelta

signal_weight = {"MACD": 0.15, "BOLL": 0.10, "RSI": 0.10, "MA": 0.15, "SO": 0.10, "ATR": 0.15, "OBV": 0.15, "MFI": 0.10}
Signals = {"Signal_MACD":"MACD", "Signal_Boll":"BOLL", "Signal_RSI":"RSI", "Position_MA":"MA", \
           "Signal_SO":"SO", "Signal_ATR":"ATR", "Signal_OBV":"OBV", "Signal_MFI":"MFI"}
price_weight = [-1, -0.7, -0.5, 0.5, 0.7, 1]
price_rate = [1.0, 0.5, 0.3, 0.3, 0.5, 1.0]
presetTakeProfitPrice_rate = [0.2, 0.1, 0.05, 0.05, 0.1, 0.2]
presetStopLossPrice_rate = [0.4, 0.2, 0.1, 0.1, 0.2, 0.4]
fee_rate = 0.00084
signal_windows = 3
market_id = "bitget"
granularity = "5m"
mandatory_stop_loss_score = 0.4

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

def record_signal(record_long_signal, record_short_signal):
    content = "close_long,{}\nclose_short,{}".format(record_long_signal, record_short_signal)
    write_txt(f"./{market_id}_signal.txt", content, rewrite=True)

def get_time(days=2):
    current_timestamp = int(time.time())
    now = datetime.now(timezone.utc)
    begin = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=days)
    begin_timestamp = int(begin.timestamp())

    return (current_timestamp + 1) * 1000, begin_timestamp * 1000

def get_candles(marketApi, symbol, startTime, endTime, granularity="5m", limit=1000, print_info=False, market_id="bitget"):
    _data = []
    if market_id == "binance":
        result = marketApi.klines(
            symbol=symbol, 
            interval=granularity, 
            startTime=startTime, 
            endTime=endTime, 
            limit=limit
            )
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[5])))
    elif market_id == "bitget":
        result = marketApi.candles(
            symbol=symbol, 
            granularity=granularity, 
            startTime=startTime, 
            endTime=endTime, 
            limit=limit, 
            print_info=print_info
            )
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6])))
    return _data

def get_ticker(marketApi, symbol, print_info=False, market_id="bitget"):
    if market_id == "bitget":
        return marketApi.ticker(symbol=symbol, print_info=print_info)['data']['last']
    elif market_id == "binance":
        return marketApi.ticker_price(symbol=symbol)['price']

def get_account(accountApi, symbol, marginCoin, print_info=False, market_id="bitget"):
    total_amount, crossMaxAvailable= 0, 0
    if market_id == "bitget":
        account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=print_info)
        total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
        crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
    elif market_id == "binance":
        _data = accountApi.balance(recvWindow=5000)
        for sub_data in _data:
            if sub_data['asset'] == marginCoin:
                total_amount, crossMaxAvailable= sub_data['balance'], sub_data['availableBalance']
                break 
    return float(total_amount), float(crossMaxAvailable)

def get_place_order(orderApi, symbol, marginCoin, size, side, orderType, timeInForceValue, clientOrderId, print_info=False, presetStopLossPrice=None, presetTakeProfitPrice=None, market_id="bitget"):
    if market_id == "bitget":
        return orderApi.place_order(
            symbol=symbol, 
            marginCoin=marginCoin, 
            size=size, 
            side=side, 
            orderType=orderType, 
            timeInForceValue=timeInForceValue, 
            clientOrderId=clientOrderId, 
            print_info=print_info, 
            presetStopLossPrice=presetStopLossPrice, 
            presetTakeProfitPrice=presetTakeProfitPrice
            )
    elif market_id == "binance":
        _side = "BUY" if side.split("_")[0].upper() == "OPEN" else "SELL"
        _positionSide = side.split("_")[1].upper()
        return orderApi.new_order(
                symbol=symbol,
                side=_side,
                type=orderType.upper(),
                positionSide=_positionSide,
                quantity=size,
                closePosition=False,
                newClientOrderId=clientOrderId,
            )

def get_single_position(positionApi, symbol, marginCoin, print_info=False, market_id="bitget", positionSide="short"):
    basecoin_size, unrealizedPL = 0, 0
    if market_id == "bitget":
        position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=print_info)
        for position_element in position_result['data']:
            if position_element['holdSide'] == positionSide.lower():
                basecoin_size += float(position_element['total'])
                unrealizedPL += float(position_element['unrealizedPL'])
    elif market_id == "binance":
        position_result = positionApi.account(recvWindow=5000)['positions']
        for position_element in position_result:
            if position_element['symbol'] == symbol:
                if position_element['positionSide'] == positionSide.upper():
                        basecoin_size += float(position_element['positionAmt'])
                        unrealizedPL += (float(position_element['unrealizedProfit']) / float(position_element['leverage']))
    return abs(float(basecoin_size)), float(unrealizedPL)