import ccxt
import json
import os
from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live
})

response = kabus.register_whitelist(['167060018@24/JPY'])
print(response)
