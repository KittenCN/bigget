from bitget_connector import *
from common import *
current_timestamp, today_timestamp = get_time(days=2)
result = marketApi.candles(symbol=symbol, startTime=today_timestamp, granularity=granularity, limit=1000, print_info=False)
print(result)