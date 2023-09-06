#!/usr/bin/python
import pandas as pd
import numpy as np
from loguru import logger
from common import *
from target import *

def handle(message):
    print("handle:" + message)


def handel_error(message):
    print("handle_error:" + message)


def handel_btcusd(message):
    print("handel_btcusd:" + message)


if __name__ == '__main__':
    login_info = read_txt("login.txt")

    api_key = login_info[0]
    secret_key = login_info[1]
    passphrase = login_info[2]
    symbol = 'SBTCSUSDT_SUMCBL'
    marginCoin='SUSDT'

    # client = login_bigget(api_key, secret_key, passphrase)
    # accountApi = accounts.AccountApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
    marketApi = market.MarketApi(api_key, secret_key, passphrase, use_server_time=False, first=False)

    # channles = [SubscribeReq("mc", "ticker", "BTCUSD"), SubscribeReq("SP", "candle1W", "BTCUSDT")]
    # client.subscribe(channles,handle)

    # channles = [SubscribeReq("mc", "ticker", "ETHUSD")]
    # client.subscribe(channles, handel_btcusd)

    # result = accountApi.account(symbol, marginCoin)
    # print(result)
    while(True):
        current_timestamp, today_timestamp = get_time(days=2)
        result =  marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000, print_info=False)
        # print(result)
        _data = []
        for item in result:
            _data.append(element_data(time=np.int64(item[0]), open=float(item[1]), high=float(item[2]), low=float(item[3]), close=float(item[4]), volume1=float(item[5]), volume2=float(item[6]), DIFF=-1, MACD=-1, SIGNAL=-1))
        df = pd.DataFrame([item.__dict__ for item in _data])
        # df.to_csv("test.csv")
        # df.iloc[:, 1:] = df.iloc[:, 1:].astype(float)
        df = calculate_macd(df)
        df = macd_signals(df)
        df = compute_bollinger_bands(df)
        df = bollinger_signals(df)
        # df['RSI'] = compute_rsi(df, window=14)
        _item = df.iloc[-1]
        if not pd.isna(_item['Buy_Signal']) \
            and not pd.isna(_item['Buy_Signal_Boll']):
            # and not pd.isna(_item['Buy_Signal_RSI']):
            logger.info([str(_item['Buy_Signal']), str(_item['Buy_Signal_Boll']), "buy"])
        elif not pd.isna(_item['Sell_Signal']) \
            and not pd.isna(_item['Sell_Signal_Boll']):
            # and not pd.isna(_item['Sell_Signal_RSI']):
            logger.info([str(_item['Sell_Signal']), str(_item['Sell_Signal_Boll']), "sell"])
        else:
            logger.info([str(_item['Buy_Signal']), str(_item['Buy_Signal_Boll']),str(_item['Sell_Signal']), str(_item['Sell_Signal_Boll']), "wait"])
        time.sleep(60)