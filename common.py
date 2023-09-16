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
presetTakeProfitPrice_rate = [0.3, 0.2, 0.1, 0.1, 0.2, 0.3]
presetStopLossPrice_rate = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5]
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

def get_new_clientOrderId(clientOrderId):
    current_timestamp, today_timestamp = get_time(days=2)
    while clientOrderId == current_timestamp:
        current_timestamp, today_timestamp = get_time(days=2)
    return current_timestamp

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

def get_mark(marketApi, symbol, print_info=False, market_id="bitget"):
    if market_id == "bitget":
        return marketApi.market_price(symbol=symbol, print_info=print_info)['data']['markPrice']
    elif market_id == "binance":
        return marketApi.mark_price(symbol=symbol)['markPrice']

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

def get_place_order(orderApi, symbol, marginCoin, size, side, orderType, timeInForceValue, clientOrderId, print_info=False, presetStopLossPrice=None, presetTakeProfitPrice=None, market_id="bitget", price_index=0):
    _positionSide = side.split("_")[1].upper()
    if market_id == "bitget":
        result = orderApi.place_order(
            symbol=symbol, 
            marginCoin=marginCoin, 
            size=size, 
            side=side, 
            orderType=orderType, 
            timeInForceValue=timeInForceValue, 
            clientOrderId=clientOrderId, 
            print_info=print_info, 
            # presetStopLossPrice=presetStopLossPrice, 
            # presetTakeProfitPrice=presetTakeProfitPrice
            )
        if result['msg'] == "success":
            current_price = orderApi.detail(symbol=symbol, orderId=result['data']['orderId'], print_info=print_info)['data']['price']
            if _positionSide.upper() == "LONG":
                presetStopLossPrice = round(current_price * (1 - presetStopLossPrice_rate[price_index]), 2)
                presetTakeProfitPrice = round(current_price * (1 + presetTakeProfitPrice_rate[price_index]), 2)
            else:
                presetStopLossPrice = round(current_price * (1 + presetStopLossPrice_rate[price_index]), 2)
                presetTakeProfitPrice = round(current_price * (1 - presetTakeProfitPrice_rate[price_index]), 2)
            orderApi.modifyOrder(
                symbol=symbol,
                orderId=result['data']['orderId'],
                presetTakeProfitPrice=presetStopLossPrice,
                presetStopLossPrice=presetTakeProfitPrice,
                print_info=print_info,
            )
        return result
    elif market_id == "binance":
        if _positionSide == "LONG":
            _side = "BUY" if side.split("_")[0].upper() == "OPEN" else "SELL"
        elif _positionSide == "SHORT":
            _side = "SELL" if side.split("_")[0].upper() == "OPEN" else "BUY"
        ## open or close opt
        print("open or close opt")
        clientOrderId = get_new_clientOrderId(clientOrderId)
        result = orderApi.new_order(
                symbol=symbol,
                side=_side,
                type=orderType.upper(),
                positionSide=_positionSide,
                quantity=round(size, 3),
                newClientOrderId=clientOrderId,
            )
        print(result)
        order_info = orderApi.get_all_orders(symbol=symbol, orderId=result['orderId'])[0]
        order_status = order_info['status']
        if order_status == "FILLED" and side.split("_")[0].upper() == "OPEN":
            current_price = float(order_info['avgPrice'])
            if _positionSide.upper() == "LONG":
                presetStopLossPrice = round(current_price * (1 - presetStopLossPrice_rate[price_index]), 2)
                presetTakeProfitPrice = round(current_price * (1 + presetTakeProfitPrice_rate[price_index]), 2)
            else:
                presetStopLossPrice = round(current_price * (1 + presetStopLossPrice_rate[price_index]), 2)
                presetTakeProfitPrice = round(current_price * (1 - presetTakeProfitPrice_rate[price_index]), 2)
            ## stop loss or take profit opt
            print("stop loss opt")
            if _positionSide == "SHORT":
                _side = "BUY" 
            elif _positionSide == "LONG":
                _side = "SELL"
            if presetStopLossPrice is not None:
                clientOrderId = get_new_clientOrderId(clientOrderId)
                order_result = orderApi.new_order(
                            symbol=symbol,
                            side=_side,
                            type="STOP_MARKET",
                            positionSide=_positionSide,
                            closePosition=True,
                            stopPrice=presetStopLossPrice,
                            newClientOrderId=clientOrderId,
                        )
                print(order_result)
            print("take profit opt")
            if presetTakeProfitPrice is not None:
                clientOrderId = get_new_clientOrderId(clientOrderId)
                order_result = orderApi.new_order(
                            symbol=symbol,
                            side=_side,
                            type="TAKE_PROFIT_MARKET",
                            positionSide=_positionSide,
                            closePosition=True,
                            stopPrice=presetTakeProfitPrice,
                            newClientOrderId=clientOrderId,
                        )
                print(order_result)
        return result

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