import ccxt

from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabusapi_password': kCred.kabusapi_password
})

orders = kabus.fetch_open_orders()

print(orders)