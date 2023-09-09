#!/usr/bin/python
import math
import pandas as pd
import numpy as np
import bitget.mix.market_api as market
import bitget.mix.order_api as order
import bitget.mix.account_api as accounts
import bitget.mix.position_api as position
from common import macd_signals,  bollinger_signals, rsi_signals, read_txt, get_time, element_data, time, logger, write_txt, datetime
from target import calculate_macd, compute_bollinger_bands, compute_rsi
from retrying import retry

@retry(stop_max_attempt_number=10, wait_fixed=30000)
def check_price(accountApi,markApi,orderApi,positionApi,symbol,marginCoin):
    global last_time
    assert markApi is not None or orderApi is not None or positionApi is not None or symbol is not None or accountApi is not None
    try:
        current_timestamp, today_timestamp = get_time(days=2)
        result =  marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000, print_info=False)
        _data = []
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6]), DIFF=-1, MACD=-1, SIGNAL=-1))
        df = pd.DataFrame([item.__dict__ for item in _data])
        # df.to_csv("test.csv")
        # df.iloc[:, 1:] = df.iloc[:, 1:].astype(float)
        current_price = marketApi.ticker(symbol, print_info=False)['data']['last']
        current_signal = "wait"
        if last_time != int(df.iloc[-1]['time']):
            last_time = int(df.iloc[-1]['time'])
            df = calculate_macd(df)
            df = macd_signals(df)
            df = compute_bollinger_bands(df)
            df = bollinger_signals(df)
            df['RSI'] = compute_rsi(df, window=14)
            df = rsi_signals(df, window=14)
            _item = df.iloc[-1]
            if not pd.isna(_item['Buy_Signal']) \
                and not pd.isna(_item['Buy_Signal_Boll']) \
                and not pd.isna(_item['Buy_Signal_RSI']):
                current_signal = "buy"
            elif not pd.isna(_item['Sell_Signal']) \
                and not pd.isna(_item['Sell_Signal_Boll']) \
                and not pd.isna(_item['Sell_Signal_RSI']):
                current_signal = "sell"
            account_info = accountApi.account(symbol=symbol, marginCoin=marginCoin, print_info=False)
            ## long trade
            total_amount = float(account_info['data']['locked']) + float(account_info['data']['available'])
            crossMaxAvailable = float(account_info['data']['crossMaxAvailable'])
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if crossMaxAvailable >= total_amount * 0.4 and current_signal == "buy":
                use_amount = crossMaxAvailable * 0.7
                basecoin_size = use_amount / current_price
                basecoin_size = math.floor(round(basecoin_size, 7) * 10**6) / 10**6
                order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_long', orderType='market', timeInForceValue='normal', clientOid=current_timestamp, print_info=False)
                content = "Date:{}, Buy:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, current_price, basecoin_size, order_result['msg'])
                logger.info(content)
                write_txt("log.txt", content)
            if current_signal == "sell" and account_info['data']['unrealizedPL'] > 0:
                position_result = positionApi.single_position(symbol=symbol, marginCoin=marginCoin, print_info=False)
                basecoin_size = 0
                for position_element in position_result['data']:
                    if position_element['holdSide'] == 'long':
                        basecoin_size += float(position_element['total'])
                if basecoin_size > 0:
                    order_result = orderApi.place_order(symbol=symbol, marginCoin=marginCoin, size=basecoin_size, side='open_short', orderType='market', timeInForceValue='normal', clientOid=current_timestamp, print_info=False)
                    content = "Date:{}, Sell:{}, Price:{}, size:{}, status:{}".format(current_datetime, symbol, current_price, basecoin_size, order_result['msg'])
                    logger.info(content)
                    write_txt("log.txt", content)
        logger.info("Product:{}, Price:{}, Signal:{}".format(symbol, current_price, current_signal))
    except Exception as e:
        logger.error(e)
        raise e

if __name__ == '__main__':
    global last_time
    login_info = read_txt("login.txt")
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
        time.sleep(15)
