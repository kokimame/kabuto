import ccxt

from freqtrade.kabuto.credentials import KabutoCredential as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabusapi_password': kCred.kabusapi_password
})

trades = kabus.fetch_trades('5020@1/JPY')

print(trades)

