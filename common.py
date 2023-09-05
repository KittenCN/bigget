#!/usr/bin/python
from bitget.consts import CONTRACT_WS_URL
from bitget.ws.bitget_ws_client import BitgetWsClient, SubscribeReq

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