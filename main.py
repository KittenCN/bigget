#!/usr/bin/python
import math
import pandas as pd
import numpy as np
from common import read_txt, get_time, element_data, time, write_txt, datetime, signal_weight, \
                    price_weight, price_rate, Signals, fee_rate, signal_windows, check_folder, presetTakeProfitPrice_rate, \
                    presetStopLossPrice_rate, get_candles, get_ticker, get_account, get_place_order, get_single_position
from signals import macd_signals,  bollinger_signals, rsi_signals, generate_stochastic_signals, generate_atr_signals, \
                    generate_obv_signals, generate_mfi_signals, generate_trading_signals
from target import calculate_macd, compute_bollinger_bands, compute_rsi,calculate_double_moving_average, \
                    calculate_stochastic_oscillator, calculate_atr, calculate_obv, calculate_mfi
from bitget_connector import login_bigget, accountApi, marketApi, orderApi, positionApi, symbol, marginCoin
from retrying import retry

@retry(stop_max_attempt_number=10, wait_fixed=30000)
def check_price(accountApi,markApi,orderApi,positionApi,symbol,marginCoin):
    global last_time, record_signal, current_signal_value, current_open_signal, total_score, last_open_signal, \
            current_close_signal, last_close_signal, content
    assert markApi is not None or orderApi is not None or positionApi is not None or symbol is not None or accountApi is not None
    try:
        current_timestamp, today_timestamp = get_time(days=2)
        # result = marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000, print_info=False)
        # _data = []
        # for item in result:
        #     _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6])))
        _data = get_candles(marketApi=marketApi, symbol=symbol, startTime=today_timestamp, endTime=current_timestamp, granularity="5m", limit=1000, print_info=False)
        df = pd.DataFrame([item.__dict__ for item in _data])
        # current_price = float(marketApi.ticker(symbol, print_info=False)['data']['last'])
        current_price = float(get_ticker(marketApi, symbol, print_info=False)['data']['last'])
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if last_time != int(df.iloc[-1]['time']):
            last_time = int(df.iloc[-1]['time'])
            df = calculate_macd(df)
            df = macd_signals(df)
            df = compute_bollinger_bands(df)
            df = bollinger_signals(df)
            df = compute_rsi(df, window=14)
            df = rsi_signals(df, window=14)
            df = calculate_double_moving_average(df, short_window=40, long_window=100)
            df = generate_trading_signals(df)
            df = calculate_stochastic_oscillator(df, n=14, m=3)
            df = generate_stochastic_signals(df)
            df = calculate_atr(df, n=14)
            df = generate_atr_signals(df)
            df = calculate_obv(df)
            df = generate_obv_signals(df)
            df = calculate_mfi(df)
            df = generate_mfi_signals(df)
            ## calculate price score
            signal_generator = []
            total_score = 0
            for item in Signals.keys():
                before_score = total_score
                for _window in range(1, signal_windows+1):
                    _item = df.iloc[-1 * _window]
                    if not pd.isna(_item[item]) and _item[item] == 1:
                        total_score += signal_weight[Signals[item]]
                        signal_generator.append('+' + Signals[item])
                    elif not pd.isna(_item[item]) and _item[item] == -1:
                        total_score -= signal_weight[Signals[item]]
                        signal_generator.append('-' + Signals[item])
                    if before_score != total_score:
                        break
            current_signal_value = {"MACD": round(_item['MACD'], 1), "SIGNAL_MACD": round(_item['SIGNAL_MACD'], 1), "Middle_Band": round(_item['Middle_Band'], 1), "Upper_Band": round(_item['Upper_Band'], 1), "Lower_Band": round(_item['Lower_Band'], 1)}
            ## check signal
            if total_score > 0.3:
                current_open_signal = "open_long"
            elif total_score < -0.3:
                current_open_signal = "open_short"
            else:
                current_open_signal = "wait"
            if current_open_signal != "wait" and current_open_signal == last_open_signal:
                current_open_signal = "wait"
            else:
                last_open_signal = current_open_signal
            
            if total_score > 0.2:
                current_close_signal = "close_short"
            elif total_score < -0.2:
                current_close_signal = "close_long"
            else:
                current_close_signal = "wait"
            if current_close_signal != "wait" and current_close_signal == last_close_signal:
                current_close_signal = "wait"
            else:
                last_close_signal = current_close_signal
            price_lever = 20
            StopLoss_rate = 1 - (0.1 / price_lever)
            TakeProfit_rate = 1 + (0.1 / price_lever)
            ## long operation
            # account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=False)
            account_info = get_account(accountApi, symbol, marginCoin, print_info=False)
            total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
            crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ## record signal to file
            if total_score != 0:
                content = "Date:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, OpenSignal:{}, CloseSignal:{}, Signal_Generator:{}".format(current_datetime, symbol, current_price, total_score, current_open_signal, current_close_signal, signal_generator)
                # ext_centent = "\nSignalValue:{}".format(current_signal_value)
                print('\r' + content)
                write_txt(f"./signal_his/signal_his_{current_date}.txt", content, rewrite=False)
            # open long operation
            if crossMaxAvailable >= total_amount * 0.3 and current_open_signal == "open_long":
                use_amount = crossMaxAvailable * 0.8
                for _i in range(len(price_weight)):
                    if total_score <= price_weight[_i]:
                        use_amount = crossMaxAvailable * price_rate[_i]
                        StopLoss_rate = 1 - (presetStopLossPrice_rate[_i] / price_lever)
                        TakeProfit_rate = 1 + (presetTakeProfitPrice_rate[_i] / price_lever)
                        break
                basecoin_size = use_amount / current_price * price_lever
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                print()
                # order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True, presetStopLossPrice=round(current_price*StopLoss_rate, 1), presetTakeProfitPrice=round(current_price*TakeProfit_rate,1))
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True, presetStopLossPrice=round(current_price*StopLoss_rate, 1), presetTakeProfitPrice=round(current_price*TakeProfit_rate,1))
                content = "Date:{}, Buy:{}, Side:{}, Price:{}, size:{}, presetStopLossPrice:{}, presetTakeProfitPrice:{}, status:{}".format(current_datetime, symbol, 'open_long', current_price, basecoin_size, round(current_price*StopLoss_rate, 1), round(current_price*TakeProfit_rate,1), order_result['msg'])
                print('\r' + content)
                write_txt(f"./log/log_{current_date}.txt", content + '\n')
            # open buy fail
            elif current_open_signal == "open_long":
                print('\rOpen_Long fail, crossMaxAvailable:{}, total_amount:{}'.format(crossMaxAvailable, total_amount))
            basecoin_size = 0
            # position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False) 
            position_result = get_single_position(positionApi, symbol=symbol, marginCoin=marginCoin, print_info=False)
            for position_element in position_result['data']:
                if position_element['holdSide'] == 'long':
                    basecoin_size += float(position_element['total'])
            # close long operation
            if (record_signal == "close_long" or current_close_signal == "close_long") and float(account_info['data']['unrealizedPL']) >= 0 and basecoin_size > 0:
                record_signal = ""
                write_txt("./signal.txt", record_signal, rewrite=True)    
                print()     
                # order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True)
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True)
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_long', current_price, basecoin_size, order_result['msg'])
                print('\r' + content)
                write_txt(f"./log/log_{current_date}.txt", content + '\n')
            # close long fail
            elif (record_signal == "close_long" or current_close_signal == "close_long") and float(account_info['data']['unrealizedPL']) < 0 and basecoin_size > 0:
                record_signal = "close_long"
                print('\rClose_Long fail, unrealizedPL:{}'.format(float(account_info['data']['unrealizedPL'])))
                write_txt("./signal.txt", record_signal, rewrite=True)
            elif record_signal == "close_long" and basecoin_size <= 0:
                record_signal = ""
                write_txt("./signal.txt", record_signal, rewrite=True)
            ## short operation
            # account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=False)
            account_info = get_account(accountApi, symbol, marginCoin, print_info=False)
            total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
            crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_timestamp, today_timestamp = get_time(days=2)
            # open short operation
            if crossMaxAvailable >= total_amount * 0.3 and current_open_signal == "open_short":
                use_amount = crossMaxAvailable * 0.8
                for _i in range(len(price_weight)):
                    if total_score <= price_weight[_i]:
                        use_amount = crossMaxAvailable * price_rate[_i]
                        StopLoss_rate = 1 + (presetStopLossPrice_rate[_i] / price_lever)
                        TakeProfit_rate = 1 - (presetTakeProfitPrice_rate[_i] / price_lever)
                        break
                basecoin_size = use_amount / current_price * price_lever
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                print()
                # order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True, presetStopLossPrice=round(current_price*StopLoss_rate,1), presetTakeProfitPrice=round(current_price*TakeProfit_rate,1))
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True, presetStopLossPrice=round(current_price*StopLoss_rate,1), presetTakeProfitPrice=round(current_price*TakeProfit_rate,1))
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, presetStopLossPrice:{}, presetTakeProfitPrice:{}, status:{}".format(current_datetime, symbol, 'open_short', current_price, basecoin_size, round(current_price*StopLoss_rate,1), round(current_price*TakeProfit_rate,1), order_result['msg'])
                print('\r' + content)
                write_txt(f"./log/log_{current_date}.txt", content + '\n')
            # open short fail
            elif current_open_signal == "open_short":
                print('\rOpen_Short fail, crossMaxAvailable:{}, total_amount:{}'.format(crossMaxAvailable, total_amount))
            # position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False)
            position_result = get_single_position(positionApi, symbol=symbol, marginCoin=marginCoin, print_info=False)
            basecoin_size = 0
            for position_element in position_result['data']:
                if position_element['holdSide'] == 'short':
                    basecoin_size += float(position_element['total'])
            # close short operation
            if (record_signal == "close_short" or current_close_signal == "close_short") and float(account_info['data']['unrealizedPL']) > 0 and basecoin_size > 0:
                record_signal = ""
                write_txt("./signal.txt", record_signal, rewrite=True)
                print()
                # order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True)
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=True)
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_short', current_price, basecoin_size, order_result['msg'])
                print('\r' + content)
                write_txt(f"./log/log_{current_date}.txt", content + '\n')
            elif (record_signal == "close_short" or current_close_signal == "close_short") and float(account_info['data']['unrealizedPL']) < 0 and basecoin_size > 0:
                record_signal = "close_short"
                print('\rClose_Short fail, unrealizedPL:{}'.format(float(account_info['data']['unrealizedPL'])))
                write_txt("./signal.txt", record_signal, rewrite=True)
            elif record_signal == "close_short" and basecoin_size <= 0:
                record_signal = ""
                write_txt("./signal.txt", record_signal, rewrite=True)
        print("\rDate:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, OpenSignal:{}, LastOpenSignal:{}, CloseSignal:{}, LastCloseSignal:{}, RecordSignal:{}".format(current_datetime, symbol, current_price, total_score, current_open_signal, last_open_signal, current_close_signal, last_close_signal, record_signal), end="")
        # print("SignalValue:{}".format(current_signal_value), end="")
    except Exception as e:
        print('\r' + e)
        write_txt("./error.txt", e + '\n', rewrite=False)
        raise e

if __name__ == '__main__':
    global last_time, record_signal, current_signal_value, current_open_signal, total_score, last_open_signal, current_date, \
            current_close_signal, last_close_signal
    check_folder("./log")
    check_folder("./signal_his")
    last_time = 0
    total_score = 0.0
    current_open_signal = "wait"
    current_close_signal = "wait"
    last_open_signal = "wait"
    last_close_signal = "wait"
    current_signal_value = {"MACD": 0, "SIGNAL_MACD": 0, "Middle_Band": 0, "Upper_Band": 0, "Lower_Band": 0}

    # main
    while(True):
        current_date = datetime.now().strftime("%Y-%m-%d")
        record_signal = read_txt("./signal.txt")
        if len(record_signal) == 0:
            record_signal = ""
        else:
            record_signal = record_signal[0]
        check_price(accountApi=accountApi, markApi=marketApi, orderApi=orderApi, positionApi=positionApi, symbol=symbol, marginCoin=marginCoin)
        time.sleep(0.2)
