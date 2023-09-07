#!/usr/bin/python
import pandas as pd
import numpy as np
import bitget.mix.market_api as market
from common import macd_signals,  bollinger_signals, rsi_signals, read_txt, get_time, element_data, time, logger
from target import calculate_macd, compute_bollinger_bands, compute_rsi
from retrying import retry

@retry(stop_max_attempt_number=3, wait_fixed=500)
def check_price(markApi):
    global last_time
    assert markApi is not None
    try:
        current_timestamp, today_timestamp = get_time(days=2)
        result =  marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000, print_info=False)
        _data = []
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6]), DIFF=-1, MACD=-1, SIGNAL=-1))
        df = pd.DataFrame([item.__dict__ for item in _data])
        # df.to_csv("test.csv")
        # df.iloc[:, 1:] = df.iloc[:, 1:].astype(float)
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
                logger.info([str(_item['Buy_Signal']), str(_item['Buy_Signal_Boll']), str(_item['Buy_Signal_RSI']), "buy"])
            elif not pd.isna(_item['Sell_Signal']) \
                and not pd.isna(_item['Sell_Signal_Boll']) \
                and not pd.isna(_item['Sell_Signal_RSI']):
                logger.info([str(_item['Sell_Signal']), str(_item['Sell_Signal_Boll']), str(_item['Sell_Signal_RSI']), "sell"])
            else:
                logger.info([str(_item['Buy_Signal']), str(_item['Buy_Signal_Boll']),str(_item['Sell_Signal']), str(_item['Sell_Signal_Boll']), str(_item['Buy_Signal_RSI']), str(_item['Sell_Signal_RSI']), "wait"])
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
    symbol = 'SBTCSUSDT_SUMCBL'
    marginCoin='SUSDT'

    # client = login_bigget(api_key, secret_key, passphrase)
    # accountApi = accounts.AccountApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    marketApi = market.MarketApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    while(True):
        check_price(marketApi)
        time.sleep(60)