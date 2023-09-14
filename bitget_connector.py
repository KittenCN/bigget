import bitget.mix.market_api as market
import bitget.mix.order_api as order
import bitget.mix.account_api as accounts
import bitget.mix.position_api as position
from bitget.consts import CONTRACT_WS_URL
from bitget.ws.bitget_ws_client import BitgetWsClient
from common import read_txt

def handel_error(message):
    print("handle_error:" + message)

def login_bigget(api_key, secret_key, passphrase, http_proxy_host=None, http_proxy_port=None):
    client = BitgetWsClient(CONTRACT_WS_URL, need_login=True) \
        .api_key(api_key) \
        .api_secret_key(secret_key) \
        .passphrase(passphrase) \
        .error_listener(handel_error) \
        .http_proxy_host(http_proxy_host) \
        .http_proxy_port(http_proxy_port) \
        .build()
    return client

# bitget connector
login_info = read_txt("./login.txt")
api_key = login_info[0]
secret_key = login_info[1]
passphrase = login_info[2]
symbol = 'SBTCSUSDT_SUMCBL' #交易对
marginCoin='SUSDT' #保证金币种

# client = login_bigget(api_key, secret_key, passphrase \
#                     #   , http_proxy_host="127.0.0.1", http_proxy_port=7890 \
#                         )
accountApi = accounts.AccountApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
marketApi = market.MarketApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
orderApi = order.OrderApi(api_key, secret_key, passphrase, use_server_time=False, first=False)
positionApi = position.PositionApi(api_key, secret_key, passphrase, use_server_time=False, first=False)