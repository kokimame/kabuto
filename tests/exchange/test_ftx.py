# pragma pylint: disable=missing-docstring, C0103, bad-continuation, global-statement
# pragma pylint: disable=protected-access
from random import randint
from unittest.mock import MagicMock

import ccxt
import pytest

from freqtrade.exceptions import DependencyException, InvalidOrderException
from tests.conftest import get_patched_exchange

from .test_exchange import ccxt_exceptionhandlers

STOPLOSS_ORDERTYPE = 'stop'


def test_stoploss_order_ftx(default_conf, mocker):
    api_mock = MagicMock()
    order_id = 'test_prod_buy_{}'.format(randint(0, 10 ** 6))

    api_mock.create_order = MagicMock(return_value={
        'id': order_id,
        'info': {
            'foo': 'bar'
        }
    })

    default_conf['dry_run'] = False
    mocker.patch('freqtrade.exchange.Exchange.amount_to_precision', lambda s, x, y: y)
    mocker.patch('freqtrade.exchange.Exchange.price_to_precision', lambda s, x, y: y)

    exchange = get_patched_exchange(mocker, default_conf, api_mock, 'ftx')

    # stoploss_on_exchange_limit_ratio is irrelevant for ftx market orders
    order = exchange.stoploss(pair='ETH/BTC', amount=1, stop_price=190,
                              order_types={'stoploss_on_exchange_limit_ratio': 1.05})

    assert api_mock.create_order.call_args_list[0][1]['symbol'] == 'ETH/BTC'
    assert api_mock.create_order.call_args_list[0][1]['type'] == STOPLOSS_ORDERTYPE
    assert api_mock.create_order.call_args_list[0][1]['side'] == 'sell'
    assert api_mock.create_order.call_args_list[0][1]['amount'] == 1
    assert api_mock.create_order.call_args_list[0][1]['price'] == 190
    assert 'orderPrice' not in api_mock.create_order.call_args_list[0][1]['params']

    assert api_mock.create_order.call_count == 1

    api_mock.create_order.reset_mock()

    order = exchange.stoploss(pair='ETH/BTC', amount=1, stop_price=220, order_types={})

    assert 'id' in order
    assert 'info' in order
    assert order['id'] == order_id
    assert api_mock.create_order.call_args_list[0][1]['symbol'] == 'ETH/BTC'
    assert api_mock.create_order.call_args_list[0][1]['type'] == STOPLOSS_ORDERTYPE
    assert api_mock.create_order.call_args_list[0][1]['side'] == 'sell'
    assert api_mock.create_order.call_args_list[0][1]['amount'] == 1
    assert api_mock.create_order.call_args_list[0][1]['price'] == 220
    assert 'orderPrice' not in api_mock.create_order.call_args_list[0][1]['params']

    api_mock.create_order.reset_mock()
    order = exchange.stoploss(pair='ETH/BTC', amount=1, stop_price=220,
                              order_types={'stoploss': 'limit'})

    assert 'id' in order
    assert 'info' in order
    assert order['id'] == order_id
    assert api_mock.create_order.call_args_list[0][1]['symbol'] == 'ETH/BTC'
    assert api_mock.create_order.call_args_list[0][1]['type'] == STOPLOSS_ORDERTYPE
    assert api_mock.create_order.call_args_list[0][1]['side'] == 'sell'
    assert api_mock.create_order.call_args_list[0][1]['amount'] == 1
    assert api_mock.create_order.call_args_list[0][1]['price'] == 220
    assert 'orderPrice' in api_mock.create_order.call_args_list[0][1]['params']
    assert api_mock.create_order.call_args_list[0][1]['params']['orderPrice'] == 217.8

    # test exception handling
    with pytest.raises(DependencyException):
        api_mock.create_order = MagicMock(side_effect=ccxt.InsufficientFunds("0 balance"))
        exchange = get_patched_exchange(mocker, default_conf, api_mock, 'ftx')
        exchange.stoploss(pair='ETH/BTC', amount=1, stop_price=220, order_types={})

    with pytest.raises(InvalidOrderException):
        api_mock.create_order = MagicMock(
            side_effect=ccxt.InvalidOrder("ftx Order would trigger immediately."))
        exchange = get_patched_exchange(mocker, default_conf, api_mock, 'ftx')
        exchange.stoploss(pair='ETH/BTC', amount=1, stop_price=220, order_types={})

    ccxt_exceptionhandlers(mocker, default_conf, api_mock, "ftx",
                           "stoploss", "create_order", retries=1,
                           pair='ETH/BTC', amount=1, stop_price=220, order_types={})


def test_stoploss_order_dry_run_ftx(default_conf, mocker):
    api_mock = MagicMock()
    default_conf['dry_run'] = True
    mocker.patch('freqtrade.exchange.Exchange.amount_to_precision', lambda s, x, y: y)
    mocker.patch('freqtrade.exchange.Exchange.price_to_precision', lambda s, x, y: y)

    exchange = get_patched_exchange(mocker, default_conf, api_mock, 'ftx')

    api_mock.create_order.reset_mock()

    order = exchange.stoploss(pair='ETH/BTC', amount=1, stop_price=220, order_types={})

    assert 'id' in order
    assert 'info' in order
    assert 'type' in order

    assert order['type'] == STOPLOSS_ORDERTYPE
    assert order['price'] == 220
    assert order['amount'] == 1


def test_stoploss_adjust_ftx(mocker, default_conf):
    exchange = get_patched_exchange(mocker, default_conf, id='ftx')
    order = {
        'type': STOPLOSS_ORDERTYPE,
        'price': 1500,
    }
    assert exchange.stoploss_adjust(1501, order)
    assert not exchange.stoploss_adjust(1499, order)
    # Test with invalid order case ...
    order['type'] = 'stop_loss_limit'
    assert not exchange.stoploss_adjust(1501, order)


def test_fetch_stoploss_order(default_conf, mocker):
    default_conf['dry_run'] = True
    order = MagicMock()
    order.myid = 123
    exchange = get_patched_exchange(mocker, default_conf, id='ftx')
    exchange._dry_run_open_orders['X'] = order
    assert exchange.fetch_stoploss_order('X', 'TKN/BTC').myid == 123

    with pytest.raises(InvalidOrderException, match=r'Tried to get an invalid dry-run-order.*'):
        exchange.fetch_stoploss_order('Y', 'TKN/BTC')

    default_conf['dry_run'] = False
    api_mock = MagicMock()
    api_mock.fetch_orders = MagicMock(return_value=[{'id': 'X', 'status': '456'}])
    exchange = get_patched_exchange(mocker, default_conf, api_mock, id='ftx')
    assert exchange.fetch_stoploss_order('X', 'TKN/BTC')['status'] == '456'

    api_mock.fetch_orders = MagicMock(return_value=[{'id': 'Y', 'status': '456'}])
    exchange = get_patched_exchange(mocker, default_conf, api_mock, id='ftx')
    with pytest.raises(InvalidOrderException, match=r"Could not get stoploss order for id X"):
        exchange.fetch_stoploss_order('X', 'TKN/BTC')['status']

    with pytest.raises(InvalidOrderException):
        api_mock.fetch_orders = MagicMock(side_effect=ccxt.InvalidOrder("Order not found"))
        exchange = get_patched_exchange(mocker, default_conf, api_mock, id='ftx')
        exchange.fetch_stoploss_order(order_id='_', pair='TKN/BTC')
    assert api_mock.fetch_orders.call_count == 1

    ccxt_exceptionhandlers(mocker, default_conf, api_mock, 'ftx',
                           'fetch_stoploss_order', 'fetch_orders',
                           retries=6,
                           order_id='_', pair='TKN/BTC')
