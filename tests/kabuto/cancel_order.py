import ccxt

from freqtrade.kabuto.credentials import KabutoCredential as kCred


def count_open_orders(orders):
    return len([o for o in orders if o['status'] == 'open'])


kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabusapi_password': kCred.kabusapi_password
})

orders_before = kabus.fetch_orders()
for order in orders_before:
    if order['status'] == 'open':
        kabus.cancel_order(order['id'])
        break
orders_after = kabus.fetch_orders()

print(f'# of open orders is {count_open_orders(orders_before)} and '
      f'it\' {count_open_orders(orders_after)} after cancel_order')
