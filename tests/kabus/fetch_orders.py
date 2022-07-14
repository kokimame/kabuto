import ccxt

from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred

print(ccxt.__version__)

kabus = ccxt.kabus({
    'ipaddr': kCred.host_ipaddr,
    'password': kCred.password_live,
    'kabucom_password': kCred.kabucom_password
})

orders = kabus.fetch_orders()

for i, order in enumerate(orders, 1):
    order_type = order["type"].title()
    order_side = order["side"].title()
    order_status = order["status"].title()
    filled_pct = int(order["filled"] * 100 / order["amount"]) if order["amount"] > 0 else 'NaN'
    price_str = f'@ {order["price"]} JPY' if order_type == 'Limit' else ''
    action_str = 'Bought' if order_type == 'Buy' else 'Sold'
    print(f'{order_status} {order_type:6s} Order #{i}: {order_side} {order["symbol"]} {price_str} [{order["datetime"]}] id:{order["id"]}')
    # print(f'{action_str} {int(order["filled"])} out of {int(order["amount"])} ({filled_pct}%)')
    info = order['info']
    # del order['info']
    print(order)
    # print(info)
    print()