# pragma pylint: disable=missing-docstring, C0103, bad-continuation, global-statement
# pragma pylint: disable=protected-access
import logging
from random import randint
from unittest.mock import MagicMock

import pytest
from requests.exceptions import RequestException

import freqtrade.exchange as exchange
from freqtrade import OperationalException
from freqtrade.exchange import init, validate_pairs, buy, sell, get_balance, get_balances, \
    get_ticker, get_ticker_history, cancel_order, get_name, get_fee
from freqtrade.tests.conftest import log_has

API_INIT = False


def maybe_init_api(conf, mocker, force=False):
    global API_INIT
    if force or not API_INIT:
        mocker.patch('freqtrade.exchange.validate_pairs',
                     side_effect=lambda s: True)
        init(config=conf)
        API_INIT = True


def test_init(default_conf, mocker, caplog):
    caplog.set_level(logging.INFO)
    maybe_init_api(default_conf, mocker, True)
    assert log_has('Instance is running with dry_run enabled', caplog.record_tuples)


def test_init_exception(default_conf):
    default_conf['exchange']['name'] = 'wrong_exchange_name'

    with pytest.raises(
            OperationalException,
            match='Exchange {} is not supported'.format(default_conf['exchange']['name'])):
        init(config=default_conf)


def test_validate_pairs(default_conf, mocker):
    api_mock = MagicMock()
    api_mock.get_markets = MagicMock(return_value=[
        'BTC_ETH', 'BTC_TKN', 'BTC_TRST', 'BTC_SWT', 'BTC_BCC',
    ])
    mocker.patch('freqtrade.exchange._API', api_mock)
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)
    validate_pairs(default_conf['exchange']['pair_whitelist'])


def test_validate_pairs_not_available(default_conf, mocker):
    api_mock = MagicMock()
    api_mock.get_markets = MagicMock(return_value=[])
    mocker.patch('freqtrade.exchange._API', api_mock)
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)
    with pytest.raises(OperationalException, match=r'not available'):
        validate_pairs(default_conf['exchange']['pair_whitelist'])


def test_validate_pairs_not_compatible(default_conf, mocker):
    api_mock = MagicMock()
    api_mock.get_markets = MagicMock(
        return_value=['BTC_ETH', 'BTC_TKN', 'BTC_TRST', 'BTC_SWT'])
    default_conf['stake_currency'] = 'ETH'
    mocker.patch('freqtrade.exchange._API', api_mock)
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)
    with pytest.raises(OperationalException, match=r'not compatible'):
        validate_pairs(default_conf['exchange']['pair_whitelist'])


def test_validate_pairs_exception(default_conf, mocker, caplog):
    caplog.set_level(logging.INFO)
    api_mock = MagicMock()
    api_mock.get_markets = MagicMock(side_effect=RequestException())
    mocker.patch('freqtrade.exchange._API', api_mock)

    # with pytest.raises(RequestException, match=r'Unable to validate pairs'):
    validate_pairs(default_conf['exchange']['pair_whitelist'])
    assert log_has('Unable to validate pairs (assuming they are correct). Reason: ',
                   caplog.record_tuples)


def test_buy_dry_run(default_conf, mocker):
    default_conf['dry_run'] = True
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert 'dry_run_buy_' in buy(pair='BTC_ETH', rate=200, amount=1)


def test_buy_prod(default_conf, mocker):
    api_mock = MagicMock()
    api_mock.buy = MagicMock(
        return_value='dry_run_buy_{}'.format(randint(0, 10**6)))
    mocker.patch('freqtrade.exchange._API', api_mock)

    default_conf['dry_run'] = False
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert 'dry_run_buy_' in buy(pair='BTC_ETH', rate=200, amount=1)


def test_sell_dry_run(default_conf, mocker):
    default_conf['dry_run'] = True
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert 'dry_run_sell_' in sell(pair='BTC_ETH', rate=200, amount=1)


def test_sell_prod(default_conf, mocker):
    api_mock = MagicMock()
    api_mock.sell = MagicMock(
        return_value='dry_run_sell_{}'.format(randint(0, 10**6)))
    mocker.patch('freqtrade.exchange._API', api_mock)

    default_conf['dry_run'] = False
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert 'dry_run_sell_' in sell(pair='BTC_ETH', rate=200, amount=1)


def test_get_balance_dry_run(default_conf, mocker):
    default_conf['dry_run'] = True
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert get_balance(currency='BTC') == 999.9


def test_get_balance_prod(default_conf, mocker):
    api_mock = MagicMock()
    api_mock.get_balance = MagicMock(return_value=123.4)
    mocker.patch('freqtrade.exchange._API', api_mock)

    default_conf['dry_run'] = False
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert get_balance(currency='BTC') == 123.4


def test_get_balances_dry_run(default_conf, mocker):
    default_conf['dry_run'] = True
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert get_balances() == []


def test_get_balances_prod(default_conf, mocker):
    balance_item = {
        'Currency': '1ST',
        'Balance': 10.0,
        'Available': 10.0,
        'Pending': 0.0,
        'CryptoAddress': None
    }

    api_mock = MagicMock()
    api_mock.get_balances = MagicMock(
        return_value=[balance_item, balance_item, balance_item])
    mocker.patch('freqtrade.exchange._API', api_mock)

    default_conf['dry_run'] = False
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert len(get_balances()) == 3
    assert get_balances()[0]['Currency'] == '1ST'
    assert get_balances()[0]['Balance'] == 10.0
    assert get_balances()[0]['Available'] == 10.0
    assert get_balances()[0]['Pending'] == 0.0


# This test is somewhat redundant with
# test_exchange_bittrex.py::test_exchange_bittrex_get_ticker
def test_get_ticker(default_conf, mocker):
    maybe_init_api(default_conf, mocker)
    api_mock = MagicMock()
    tick = {"success": True, 'result': {'Bid': 0.00001098, 'Ask': 0.00001099, 'Last': 0.0001}}
    api_mock.get_ticker = MagicMock(return_value=tick)
    mocker.patch('freqtrade.exchange.bittrex._API', api_mock)

    # retrieve original ticker
    ticker = get_ticker(pair='BTC_ETH')
    assert ticker['bid'] == 0.00001098
    assert ticker['ask'] == 0.00001099

    # change the ticker
    tick = {"success": True, 'result': {"Bid": 0.5, "Ask": 1, "Last": 42}}
    api_mock.get_ticker = MagicMock(return_value=tick)
    mocker.patch('freqtrade.exchange.bittrex._API', api_mock)

    # if not caching the result we should get the same ticker
    # if not fetching a new result we should get the cached ticker
    ticker = get_ticker(pair='BTC_ETH', refresh=False)
    assert ticker['bid'] == 0.00001098
    assert ticker['ask'] == 0.00001099

    # force ticker refresh
    ticker = get_ticker(pair='BTC_ETH', refresh=True)
    assert ticker['bid'] == 0.5
    assert ticker['ask'] == 1


def test_get_ticker_history(default_conf, mocker):
    api_mock = MagicMock()
    tick = 123
    api_mock.get_ticker_history = MagicMock(return_value=tick)
    mocker.patch('freqtrade.exchange._API', api_mock)

    # retrieve original ticker
    ticks = get_ticker_history('BTC_ETH', int(default_conf['ticker_interval']))
    assert ticks == 123

    # change the ticker
    tick = 999
    api_mock.get_ticker_history = MagicMock(return_value=tick)
    mocker.patch('freqtrade.exchange._API', api_mock)

    # ensure caching will still return the original ticker
    ticks = get_ticker_history('BTC_ETH', int(default_conf['ticker_interval']))
    assert ticks == 123


def test_cancel_order_dry_run(default_conf, mocker):
    default_conf['dry_run'] = True
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)

    assert cancel_order(order_id='123') is None


# Ensure that if not dry_run, we should call API
def test_cancel_order(default_conf, mocker):
    default_conf['dry_run'] = False
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)
    api_mock = MagicMock()
    api_mock.cancel_order = MagicMock(return_value=123)
    mocker.patch('freqtrade.exchange._API', api_mock)
    assert cancel_order(order_id='_') == 123


def test_get_order(default_conf, mocker):
    default_conf['dry_run'] = True
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)
    order = MagicMock()
    order.myid = 123
    exchange._DRY_RUN_OPEN_ORDERS['X'] = order
    print(exchange.get_order('X'))
    assert exchange.get_order('X').myid == 123

    default_conf['dry_run'] = False
    mocker.patch.dict('freqtrade.exchange._CONF', default_conf)
    api_mock = MagicMock()
    api_mock.get_order = MagicMock(return_value=456)
    mocker.patch('freqtrade.exchange._API', api_mock)
    assert exchange.get_order('X') == 456


def test_get_name(default_conf, mocker):
    mocker.patch('freqtrade.exchange.validate_pairs',
                 side_effect=lambda s: True)
    default_conf['exchange']['name'] = 'bittrex'
    init(default_conf)

    assert get_name() == 'Bittrex'


def test_get_fee(default_conf, mocker):
    mocker.patch('freqtrade.exchange.validate_pairs',
                 side_effect=lambda s: True)
    init(default_conf)

    assert get_fee() == 0.0025


def test_exchange_misc(mocker):
    api_mock = MagicMock()
    mocker.patch('freqtrade.exchange._API', api_mock)
    exchange.get_markets()
    assert api_mock.get_markets.call_count == 1
    exchange.get_market_summaries()
    assert api_mock.get_market_summaries.call_count == 1
    api_mock.name = 123
    assert exchange.get_name() == 123
    api_mock.fee = 456
    assert exchange.get_fee() == 456
    exchange.get_wallet_health()
    assert api_mock.get_wallet_health.call_count == 1
