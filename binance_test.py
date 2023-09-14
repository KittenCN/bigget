import numpy as np
import pandas as pd
from common import element_data, get_time, read_txt
from binance.um_futures import UMFutures
from binance.lib.utils import config_logging

login_info = read_txt("./binance.txt")
api_key = login_info[0]
secret_key = login_info[1]

um_futures_client = UMFutures(key=api_key, secret=secret_key)
um_futures_client.base_url = 'https://testnet.binancefuture.com'
symbol = 'BTCUSDT' #交易对
marginCoin='USDT' #保证金币种

response = um_futures_client.new_order(
        symbol=symbol,
        side="BUY",
        type="MARKET",
        positionSide="SHORT",
        quantity=0.001,
        timeInForce="GTC",
        closePosition=False,
    )
    