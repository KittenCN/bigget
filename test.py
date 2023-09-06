#!/usr/bin/python
import pandas as pd
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
    current_timestamp, today_timestamp = get_time(days=2)
    result =  marketApi.candles(symbol, granularity="5m", startTime=today_timestamp, endTime=current_timestamp, limit=1000)
    # print(result)
    _data = []
    for item in result:
        _data.append(element_data(time=item[0], open=item[1], high=item[2], low=item[3], close=item[4], volume1=item[5], volume2=item[6], DIFF=-1, MACD=-1, SIGNAL=-1))
    df = pd.DataFrame([item.__dict__ for item in _data])
    df.iloc[:, 1:] = df.iloc[:, 1:].astype(float)
    df = calculate_macd(df)
    print(df)