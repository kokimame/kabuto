import ccxt

from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabucom_password': kCred.kabucom_password,
})

response = kabus.create_order('9318@1/JPY', 'limit', 'buy', 100, 1)

print(response)