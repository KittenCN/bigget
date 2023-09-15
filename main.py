#!/usr/bin/python
import argparse
import math
import pandas as pd
from common import read_txt, get_time, time, write_txt, datetime, signal_weight, \
                    price_weight, price_rate, Signals, fee_rate, signal_windows, check_folder, presetTakeProfitPrice_rate, \
                    presetStopLossPrice_rate, get_candles, get_ticker, get_account, get_place_order, get_single_position, \
                    record_signal, market_id, granularity, mandatory_stop_loss_score
from signals import macd_signals,  bollinger_signals, rsi_signals, generate_stochastic_signals, generate_atr_signals, \
                    generate_obv_signals, generate_mfi_signals, generate_trading_signals
from target import calculate_macd, compute_bollinger_bands, compute_rsi,calculate_double_moving_average, \
                    calculate_stochastic_oscillator, calculate_atr, calculate_obv, calculate_mfi
from retrying import retry

parser = argparse.ArgumentParser()
parser.add_argument('--market_id', type=str, default='bitget', help='bitget or binance')
parser.add_argument('--granularity', type=str, default='5m', help='granularity')
args = parser.parse_args()

market_id = args.market_id
granularity = args.granularity

if market_id == "bitget":
    from bitget_connector import login_bigget, accountApi, marketApi, orderApi, positionApi, symbol, marginCoin
elif market_id == "binance":
    from binance_connector import um_futures_client, symbol, marginCoin
    accountApi = marketApi = orderApi = positionApi = um_futures_client

@retry(stop_max_attempt_number=10, wait_fixed=30000)
def check_price(accountApi,markApi,orderApi,positionApi,symbol,marginCoin):
    global last_time, record_long_signal, current_signal_value, current_open_signal, total_score, last_open_signal, \
            current_close_signal, last_close_signal, content, record_short_signal
    assert markApi is not None or orderApi is not None or positionApi is not None or symbol is not None or accountApi is not None
    try:
        current_timestamp, today_timestamp = get_time(days=2)
        _data = get_candles(marketApi=marketApi, symbol=symbol, startTime=today_timestamp, endTime=current_timestamp, granularity=granularity, limit=1000, print_info=False, market_id=market_id)
        df = pd.DataFrame([item.__dict__ for item in _data])
        current_price = float(get_ticker(marketApi, symbol, print_info=False, market_id=market_id))
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
            total_amount, crossMaxAvailable = get_account(accountApi, symbol, marginCoin, print_info=False, market_id=market_id)
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ## record signal to file
            if total_score != 0:
                last_content_size = len(content)
                content = "Date:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, OpenSignal:{}, CloseSignal:{}, Signal_Generator:{}".format(current_datetime, symbol, current_price, total_score, current_open_signal, current_close_signal, signal_generator)
                # ext_centent = "\nSignalValue:{}".format(current_signal_value)
                content_diff = last_content_size - len(content) + 1
                if content_diff < 0:
                    content_diff = 0
                print('\r' + '\033[33m' + content + ' ' * content_diff + '\033[0m')
                write_txt(f"./signal_his/{market_id}_signal_his_{current_date}.txt", content, rewrite=False)
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
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False, presetStopLossPrice=round(current_price*StopLoss_rate, 1), presetTakeProfitPrice=round(current_price*TakeProfit_rate,1), market_id=market_id)
                order_status = order_result['msg'] if market_id == "bitget" else orderApi.get_all_orders(symbol=symbol, orderId=order_result['orderId'])[0]['status']
                content = "Date:{}, Buy:{}, Side:{}, Price:{}, size:{}, presetStopLossPrice:{}, presetTakeProfitPrice:{}, status:{}".format(current_datetime, symbol, 'open_long', current_price, basecoin_size, round(current_price*StopLoss_rate, 1), round(current_price*TakeProfit_rate,1), order_status)
                if order_status.lower() == "success" or order_status == "FILLED":
                    print('\r' + '\033[42m' + content + '\033[0m')
                else:
                    print('\r' + '\033[31m' + content + '\033[0m')
                write_txt(f"./log/{market_id}_log_{current_date}.txt", content + '\n')
                record_long_signal = 0
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)   
            # open buy fail
            elif current_open_signal == "open_long":
                content = 'Open_Long fail, crossMaxAvailable:{}, total_amount:{}'.format(crossMaxAvailable, total_amount)
                print('\r' + '\033[31m' + content + '\033[0m')
            basecoin_size = 0
            basecoin_size, unrealizedPL = get_single_position(positionApi, symbol=symbol, marginCoin=marginCoin, print_info=False, market_id=market_id, positionSide="long")
            price_fee = basecoin_size * current_price * fee_rate
            unrealizedPL = unrealizedPL - price_fee
            # close long operation
            if (record_long_signal == 1 or current_close_signal == "close_long") and (unrealizedPL > 0 or abs(total_score) >= mandatory_stop_loss_score) and basecoin_size > 0:
                record_long_signal = 0
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)   
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_long', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False, market_id=market_id)
                order_status = order_result['msg'] if market_id == "bitget" else orderApi.get_all_orders(symbol=symbol, orderId=order_result['orderId'])[0]['status']
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_long', current_price, basecoin_size, order_status)
                if order_status.lower() == "success" or order_status == "FILLED":
                    print('\r' + '\033[42m' + content + '\033[0m')
                else:
                    print('\r' + '\033[31m' + content + '\033[0m')
                write_txt(f"./log/{market_id}_log_{current_date}.txt", content + '\n')
            # close long fail
            elif (record_long_signal == 1 or current_close_signal == "close_long") and unrealizedPL < 0 and basecoin_size > 0:
                record_long_signal = 1
                content = 'Close_Long fail, unrealizedPL:{}'.format(unrealizedPL)
                print('\r' + '\033[31m' + content + '\033[0m')
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)
            elif record_long_signal == 1 and basecoin_size <= 0:
                record_long_signal = 0
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)
            ## check short signal
            total_amount, crossMaxAvailable = get_account(accountApi, symbol, marginCoin, print_info=False, market_id=market_id)
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
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False, presetStopLossPrice=round(current_price*StopLoss_rate,1), presetTakeProfitPrice=round(current_price*TakeProfit_rate,1), market_id=market_id)
                order_status = order_result['msg'] if market_id == "bitget" else orderApi.get_all_orders(symbol=symbol, orderId=order_result['orderId'])[0]['status']
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, presetStopLossPrice:{}, presetTakeProfitPrice:{}, status:{}".format(current_datetime, symbol, 'open_short', current_price, basecoin_size, round(current_price*StopLoss_rate,1), round(current_price*TakeProfit_rate,1), order_status)
                if order_status.lower() == "success" or order_status == "FILLED":
                    print('\r' + '\033[42m' + content + '\033[0m')
                else:
                    print('\r' + '\033[31m' + content + '\033[0m')
                write_txt(f"./log/{market_id}_log_{current_date}.txt", content + '\n')
                record_short_signal = 0
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)    
            # open short fail
            elif current_open_signal == "open_short":
                content = 'Open_Short fail, crossMaxAvailable:{}, total_amount:{}'.format(crossMaxAvailable, total_amount)
                print('\r' + '\033[31m' + content + '\033[0m')
            basecoin_size = 0
            basecoin_size, unrealizedPL = get_single_position(positionApi, symbol=symbol, marginCoin=marginCoin, print_info=False, market_id=market_id, positionSide="short")
            price_fee = basecoin_size * current_price * fee_rate
            unrealizedPL = unrealizedPL - price_fee
            # close short operation
            if (record_short_signal == 1 or current_close_signal == "close_short") and (unrealizedPL > 0 or abs(total_score) >= mandatory_stop_loss_score) and basecoin_size > 0:
                record_short_signal = 0
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)
                order_result = get_place_order(orderApi, symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='close_short', orderType='market', timeInForceValue='normal', clientOrderId=current_timestamp, print_info=False, market_id=market_id)
                order_status = order_result['msg'] if market_id == "bitget" else orderApi.get_all_orders(symbol=symbol, orderId=order_result['orderId'])[0]['status']
                content = "Date:{}, Sell:{}, Side:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, 'close_short', current_price, basecoin_size, order_status)
                if order_status.lower() == "success" or order_status == "FILLED":
                    print('\r' + '\033[42m' + content + '\033[0m')
                else:
                    print('\r' + '\033[31m' + content + '\033[0m')
                write_txt(f"./log/{market_id}_log_{current_date}.txt", content + '\n')
            elif (record_short_signal == 1 or current_close_signal == "close_short") and unrealizedPL < 0 and basecoin_size > 0:
                record_short_signal = 1
                content = 'Close_Short fail, unrealizedPL:{}'.format(unrealizedPL)
                print('\r' + '\033[31m' + content + '\033[0m')
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)
            elif record_short_signal == 1 and basecoin_size <= 0:
                record_short_signal = 0
                record_signal(record_long_signal=record_long_signal, record_short_signal=record_short_signal)
        content = "Date:{}, Product:{}, Price:{:.2f}, Score:{:.2f}, OpenSignal:{}, LastOpenSignal:{}, CloseSignal:{}, LastCloseSignal:{}, RecordSignal:{}/{}".format(current_datetime, symbol, current_price, total_score, current_open_signal, last_open_signal, current_close_signal, last_close_signal, record_long_signal, record_short_signal)
        print('\r' + '\033[1m' + content + '\033[0m', end="")
    except Exception as e:
        print('\r' + '\033[31m\033[1m' + e + '\033[0m')
        write_txt(f"./{market_id}_error.txt", e + '\n', rewrite=False)
        raise e

if __name__ == '__main__':
    global last_time, record_long_signal, current_signal_value, current_open_signal, total_score, last_open_signal, current_date, \
            current_close_signal, last_close_signal, content, record_short_signal
    check_folder("./log")
    check_folder("./signal_his")
    content = ""
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
        record_signals = read_txt(f"./{market_id}_signal.txt")
        for item in record_signals:
            item_list = item.split(',')
            if item_list[0] == "close_long":
                record_long_signal = int(item_list[1])
            elif item_list[0] == "close_short":
                record_short_signal = int(item_list[1])
        check_price(accountApi=accountApi, markApi=marketApi, orderApi=orderApi, positionApi=positionApi, symbol=symbol, marginCoin=marginCoin)
        time.sleep(0.2)
