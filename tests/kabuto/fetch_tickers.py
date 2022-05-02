import ccxt
import json
import os
from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live
})

response = kabus.fetch_tickers(['8897@1/JPY', '5020@1/JPY', '9306@1/JPY'])
print(response)
