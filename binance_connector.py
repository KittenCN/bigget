#!/usr/bin/python
from common import read_txt
from binance.um_futures import UMFutures

login_info = read_txt("./binance.txt")
api_key = login_info[0]
secret_key = login_info[1]

um_futures_client = UMFutures(key=api_key, secret=secret_key, base_url='https://testnet.binancefuture.com')
symbol = 'BTCUSDT' #交易对
marginCoin='USDT' #保证金币种