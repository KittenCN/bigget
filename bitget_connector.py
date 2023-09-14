from bitget.consts import CONTRACT_WS_URL
from bitget.ws.bitget_ws_client import BitgetWsClient

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
