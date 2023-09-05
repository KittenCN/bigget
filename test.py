#!/usr/bin/python
from common import *


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
    symbol = 'btcusd'

    client = login_bigget(api_key, secret_key, passphrase)

    channles = [SubscribeReq("mc", "ticker", "BTCUSD"), SubscribeReq("SP", "candle1W", "BTCUSDT")]
    client.subscribe(channles,handle)

    channles = [SubscribeReq("mc", "ticker", "ETHUSD")]
    client.subscribe(channles, handel_btcusd)