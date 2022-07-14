import ccxt

from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred


def count_open_orders(orders):
    return len([o for o in orders if o['status'] == 'open'])


kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabucom_password': kCred.kabucom_password
})

orders_before = kabus.fetch_orders()
for order in orders_before:
    if order['status'] == 'open':
        kabus.cancel_order(order['id'])
        break
orders_after = kabus.fetch_orders()

print(f'# of open orders is {count_open_orders(orders_before)} and '
      f'it\'s {count_open_orders(orders_after)} after cancel_order')
