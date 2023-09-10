#!/usr/bin/python
import math
import pandas as pd
import numpy as np
import bitget.mix.market_api as market
import bitget.mix.order_api as order
import bitget.mix.account_api as accounts
import bitget.mix.position_api as position
from common import macd_signals,  bollinger_signals, rsi_signals, read_txt, get_time, \
                    element_data, time, write_txt, datetime, signal_weight, generate_trading_signals
from target import calculate_macd, compute_bollinger_bands, compute_rsi,calculate_double_moving_average
from retrying import retry

@retry(stop_max_attempt_number=10, wait_fixed=30000)
def check_price(accountApi,markApi,orderApi,positionApi,symbol,marginCoin):
    global last_time
    assert markApi is not None or orderApi is not None or positionApi is not None or symbol is not None or accountApi is not None
    try:
        total_score = 0.0
        current_timestamp, today_timestamp = get_time(days=2)
        result =  marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000, print_info=False)
        _data = []
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6])))
        df = pd.DataFrame([item.__dict__ for item in _data])
        # df.to_csv("test.csv")
        # df.iloc[:, 1:] = df.iloc[:, 1:].astype(float)
        current_price = float(marketApi.ticker(symbol, print_info=False)['data']['last'])
        current_signal = "wait"
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if last_time != int(df.iloc[-1]['time']):
            last_time = int(df.iloc[-1]['time'])
            df = calculate_macd(df)
            df = macd_signals(df)
            df = compute_bollinger_bands(df)
            df = bollinger_signals(df)
            df['RSI'] = compute_rsi(df, window=14)
            df = rsi_signals(df, window=14)
            df = calculate_double_moving_average(df, short_window=40, long_window=100)
            df = generate_trading_signals(df)
            _item = df.iloc[-1]
            # if not pd.isna(_item['Buy_Signal_MACD']) \
            #     and not pd.isna(_item['Buy_Signal_Boll']) \
            #     and not pd.isna(_item['Buy_Signal_RSI']):
            #     current_signal = "buy"
            # elif not pd.isna(_item['Sell_Signal_MACD']) \
            #     and not pd.isna(_item['Sell_Signal_Boll']) \
            #     and not pd.isna(_item['Sell_Signal_RSI']):
            #     current_signal = "sell"
            if not pd.isna(_item['Buy_Signal_MACD']): total_score += signal_weight["MACD"]
            if not pd.isna(_item['Buy_Signal_Boll']): total_score += signal_weight["BOLL"]
            if not pd.isna(_item['Buy_Signal_RSI']): total_score += signal_weight["RSI"]
            if not pd.isna(_item['Position_MA']) and _item['Position_MA'] == 1: total_score += signal_weight["MA_Pos"]
            if not pd.isna(_item['Position_MA']) and _item['Signal_MA'] == 1: total_score += signal_weight["MA_sig"]
            if not pd.isna(_item['Sell_Signal_MACD']): total_score -= signal_weight["MACD"]
            if not pd.isna(_item['Sell_Signal_Boll']): total_score -= signal_weight["BOLL"]
            if not pd.isna(_item['Sell_Signal_RSI']): total_score -= signal_weight["RSI"]
            if not pd.isna(_item['Position_MA']) and _item['Position_MA'] == -1: total_score -= signal_weight["MA_Pos"]
            if not pd.isna(_item['Position_MA']) and _item['Signal_MA'] == 0: total_score -= signal_weight["MA_sig"]
            if total_score > 0.5:
                current_signal = "buy"
            elif total_score < -0.5:
                current_signal = "sell"
            else:
                current_signal = "wait"
            account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=False)
            ## long trade
            total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
            crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ## long operation
            if crossMaxAvailable >= total_amount * 0.4 and current_signal == "buy":
                use_amount = crossMaxAvailable * 0.7
                basecoin_size = use_amount / current_price
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False, presetStopLossPrice=current_price*0.95, presetTakeProfitPrice=current_price*1.10)
                content = "Date:{}, Buy:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'open_long', current_price, basecoin_size, order_result['msg'])
                print(content)
                write_txt("./log.txt", content)
            if current_signal == "sell" and float(account_info['data']['unrealizedPL']) > 0:
                position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False)
                basecoin_size = 0
                for position_element in position_result['data']:
                    if position_element['holdSide'] == 'long':
                        basecoin_size += float(position_element['total'])
                if basecoin_size > 0:
                    order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False)
                    content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_long', current_price, basecoin_size, order_result['msg'])
                    print(content)
                    write_txt("log.txt", content)
            ## short operation
            current_timestamp, today_timestamp = get_time(days=2)
            if crossMaxAvailable >= total_amount * 0.4 and current_signal == "sell":
                use_amount = crossMaxAvailable * 0.7
                basecoin_size = use_amount / current_price
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False, presetStopLossPrice=current_price*0.95, presetTakeProfitPrice=current_price*1.10)
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'open_short', current_price, basecoin_size, order_result['msg'])
                print(content)
                write_txt("./log.txt", content)
            if current_signal == "buy" and float(account_info['data']['unrealizedPL']) > 0:
                position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False)
                basecoin_size = 0
                for position_element in position_result['data']:
                    if position_element['holdSide'] == 'short':
                        basecoin_size += float(position_element['total'])
                if basecoin_size > 0:
                    order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False)
                    content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_short', current_price, basecoin_size, order_result['msg'])
                    print(content)
                    write_txt("log.txt", content)
        print("\rDate:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, Signal:{}".format(current_datetime, symbol, current_price, total_score, current_signal), end="")
    except Exception as e:
        print(e)
        raise e

if __name__ == '__main__':
    global last_time
    login_info = read_txt("./login.txt")
    last_time = 0

    api_key = login_info[0]
    secret_key = login_info[1]
    passphrase = login_info[2]
    symbol = 'SBTCSUSDT_SUMCBL' #交易对
    marginCoin='SUSDT' #保证金币种

    # client = login_bigget(api_key, secret_key, passphrase)
    accountApi = accounts.AccountApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    marketApi = market.MarketApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    orderApi = order.OrderApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    positionApi = position.PositionApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    while(True):
        check_price(accountApi=accountApi, markApi=marketApi, orderApi=orderApi, positionApi=positionApi, symbol=symbol, marginCoin=marginCoin)
        time.sleep(1)
