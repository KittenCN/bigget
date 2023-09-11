#!/usr/bin/python
import math
import pandas as pd
import numpy as np
import bitget.mix.market_api as market
import bitget.mix.order_api as order
import bitget.mix.account_api as accounts
import bitget.mix.position_api as position
from common import macd_signals,  bollinger_signals, rsi_signals, read_txt, get_time, \
                    element_data, time, write_txt, datetime, signal_weight, generate_trading_signals, login_bigget, \
                    generate_stochastic_signals, generate_atr_signals, price_weight, price_rate
from target import calculate_macd, compute_bollinger_bands, compute_rsi,calculate_double_moving_average, \
                    calculate_stochastic_oscillator, calculate_atr
from retrying import retry

@retry(stop_max_attempt_number=10, wait_fixed=30000)
def check_price(accountApi,markApi,orderApi,positionApi,symbol,marginCoin):
    global last_time, last_signal, current_signal_value, current_signal
    assert markApi is not None or orderApi is not None or positionApi is not None or symbol is not None or accountApi is not None
    try:
        total_score = 0.0
        current_timestamp, today_timestamp = get_time(days=2)
        result = marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000, print_info=False)
        _data = []
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6])))
        df = pd.DataFrame([item.__dict__ for item in _data])
        current_price = float(marketApi.ticker(symbol, print_info=False)['data']['last'])
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
            df = calculate_stochastic_oscillator(df, n=14, m=3)
            df = generate_stochastic_signals(df)
            df = calculate_atr(df, n=14)
            df = generate_atr_signals(df)
            _item = df.iloc[-1]
            signal_generator = []
            Signals = {"Signal_MACD":"MACD", "Signal_Boll":"BOLL", "Signal_RSI":"RSI", "Position_MA":"MA_Pos", "Signal_SO":"SO", "Signal_ATR":"ATR"}
            for item in Signals.keys():
                if not pd.isna(_item[item]) and _item[item] == 1:
                    total_score += signal_weight[Signals[item]]
                    signal_generator.append(Signals[item])
                elif not pd.isna(_item[item]) and _item[item] == -1:
                    total_score -= signal_weight[Signals[item]]
                    signal_generator.append(Signals[item])
            current_signal_value = {"MACD": round(_item['MACD'], 1), "SIGNAL_MACD": round(_item['SIGNAL_MACD'], 1), "Middle_Band": round(_item['Middle_Band'], 1), "Upper_Band": round(_item['Upper_Band'], 1), "Lower_Band": round(_item['Lower_Band'], 1)}
            if total_score >= 0.3:
                current_signal = "buy"
            elif total_score <= -0.3:
                current_signal = "sell"
            else:
                current_signal = "wait"
            ## long operation
            account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=False)
            total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
            crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ## record signal to file
            if total_score != 0:
                centent = "Date:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, Signal:{}, Signal_Generator:{}\nSignalValue:{}".format(current_datetime, symbol, current_price, total_score, current_signal, signal_generator, current_signal_value)
                print('\r' + centent)
                # write_txt("./signal_his.txt", centent, rewrite=False)
            if crossMaxAvailable >= total_amount * 0.4 and current_signal == "buy":
                use_amount = crossMaxAvailable * 0.7
                for _i in range(len(price_weight)):
                    if total_score <= price_weight[_i]:
                        use_amount = crossMaxAvailable * price_rate[_i]
                        break
                basecoin_size = use_amount / current_price
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True, presetStopLossPrice=round(current_price*0.95, 1), presetTakeProfitPrice=round(current_price*1.10,1))
                content = "Date:{}, Buy:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'open_long', current_price, basecoin_size, order_result['msg'])
                print('\r' + centent)
                write_txt("./log.txt", content)
            elif current_signal == "buy":
                print('\rOpen_Long fail, crossMaxAvailable:{}, total_amount:{}'.format(crossMaxAvailable, total_amount))
            basecoin_size = 0
            for position_element in position_result['data']:
                if position_element['holdSide'] == 'long':
                    basecoin_size += float(position_element['total'])
            if (last_signal == "sell" or current_signal == "sell") and float(account_info['data']['unrealizedPL']) >= 0 and basecoin_size > 0:
                last_signal = ""
                write_txt("./signal.txt", last_signal)
                position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False)            
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True)
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_long', current_price, basecoin_size, order_result['msg'])
                print('\r' + centent)
                write_txt("./log.txt", content)
            elif current_signal == "sell" and float(account_info['data']['unrealizedPL']) < 0 and basecoin_size > 0:
                last_signal = "sell"
                print('\rClose_Long fail, unrealizedPL:{}'.format(float(account_info['data']['unrealizedPL'])))
                write_txt("./signal.txt", last_signal)
            ## short operation
            account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=False)
            total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
            crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_timestamp, today_timestamp = get_time(days=2)
            if crossMaxAvailable >= total_amount * 0.4 and current_signal == "sell":
                use_amount = crossMaxAvailable * 0.7
                for _i in range(len(price_weight)):
                    if total_score <= price_weight[_i]:
                        use_amount = crossMaxAvailable * price_rate[_i]
                        break
                basecoin_size = use_amount / current_price
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True, presetStopLossPrice=round(current_price*0.95,1), presetTakeProfitPrice=round(current_price*1.10,1))
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'open_short', current_price, basecoin_size, order_result['msg'])
                print('\r' + centent)
                write_txt("./log.txt", content)
            elif current_signal == "sell":
                print('\rOpen_Short fail, crossMaxAvailable:{}, total_amount:{}'.format(crossMaxAvailable, total_amount))
            position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False)
            basecoin_size = 0
            for position_element in position_result['data']:
                if position_element['holdSide'] == 'short':
                    basecoin_size += float(position_element['total'])
            if (last_signal == "buy" or current_signal == "buy") and float(account_info['data']['unrealizedPL']) > 0 and basecoin_size > 0:
                last_signal = ""
                write_txt("./signal.txt", last_signal)
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True)
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_short', current_price, basecoin_size, order_result['msg'])
                print('\r' + centent)
                write_txt("./log.txt", content)
            elif current_signal == "buy" and float(account_info['data']['unrealizedPL']) < 0 and basecoin_size > 0:
                last_signal = "buy"
                print('\rClose_Short fail, unrealizedPL:{}'.format(float(account_info['data']['unrealizedPL'])))
                write_txt("./signal.txt", last_signal)
        print("\rDate:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, Signal:{}".format(current_datetime, symbol, current_price, total_score, current_signal), end="")
        # print("SignalValue:{}".format(current_signal_value), end="")
    except Exception as e:
        print('\r' + e)
        write_txt("./error.txt", e, rewrite=False)
        raise e

if __name__ == '__main__':
    global last_time, last_signal, current_signal_value, current_signal
    login_info = read_txt("./login.txt")
    last_time = 0
    if len(last_signal) == 0:
        last_signal = ""
    else:
        last_signal = last_signal[0]
    current_signal = "wait"
    current_signal_value = {"MACD": 0, "SIGNAL_MACD": 0, "Middle_Band": 0, "Upper_Band": 0, "Lower_Band": 0}

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
        last_signal = read_txt("./signal.txt")
        check_price(accountApi=accountApi, markApi=marketApi, orderApi=orderApi, positionApi=positionApi, symbol=symbol, marginCoin=marginCoin)
        time.sleep(0.3)
