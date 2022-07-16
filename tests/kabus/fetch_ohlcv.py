import json
import time
from multiprocessing import Process

import ccxt
from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred
from freqtrade.kabuto.price_server import PriceServer

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live
})

with open('../../user_data/config_tse.json', 'r') as f:
    user_config = json.load(f)

pserv = PriceServer(user_config)
Process(target=pserv.start_generation).start()

while True:
    try:
        pairs = pserv.pairlist
        symbol, base = pairs[0].split('/')
        print('before request')
        response = kabus.fetch_ohlcv(symbol)
        print('after request')
        print(response)
    except Exception as e:
        print(e)
    time.sleep(2)

