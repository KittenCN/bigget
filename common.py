#!/usr/bin/python
import bitget.mix.account_api as accounts
import bitget.mix.market_api as market
import time
from datetime import datetime, timezone, timedelta
from bitget.consts import CONTRACT_WS_URL
from bitget.ws.bitget_ws_client import BitgetWsClient, SubscribeReq

class element_data:
    def __init__(self, time, open, high, low, close, volume1, volume2, DIFF, MACD, SIGNAL):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume1 = volume1
        self.volume2 = volume2
        self.DIFF = DIFF
        self.MACD = MACD
        self.SIGNAL = SIGNAL

def read_txt(file_path):
    result = []
    with open(file_path, "r") as file:
        for line in file:
            result.append(line.strip())
    return result

def handel_error(message):
    print("handle_error:" + message)

def login_bigget(api_key, secret_key, passphrase):
    client = BitgetWsClient(CONTRACT_WS_URL, need_login=True) \
        .api_key(api_key) \
        .api_secret_key(secret_key) \
        .passphrase(passphrase) \
        .error_listener(handel_error) \
        .build()
    return client

def get_time(days=2):
    current_timestamp = int(time.time())
    now = datetime.now(timezone.utc)
    begin = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=days)
    begin_timestamp = int(begin.timestamp())

    return (current_timestamp + 1) * 1000, begin_timestamp * 1000