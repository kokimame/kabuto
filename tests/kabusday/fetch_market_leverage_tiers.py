import ccxt

from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

print(ccxt.__version__)

kabus = ccxt.kabusday({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabucom_password': kCred.kabucom_password,
})

response = kabus.fetch_market_leverage_tiers('9318@1/JPY')

print(response)