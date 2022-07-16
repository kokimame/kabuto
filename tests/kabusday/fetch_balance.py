import ccxt

from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

kabusday = ccxt.kabusday({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabucom_password': kCred.kabucom_password
})

print(kabusday.fetch_balance())
