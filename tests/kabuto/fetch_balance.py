import ccxt

from freqtrade.kabuto.credentials import KabutoCredential as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live
})

response = kabus.fetch_balance()
print(response)