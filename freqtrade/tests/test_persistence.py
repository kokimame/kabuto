# pragma pylint: disable=missing-docstring, C0103
from copy import deepcopy
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine

from freqtrade import OperationalException, constants
from freqtrade.persistence import Trade, clean_dry_run_db, init
from freqtrade.tests.conftest import log_has


@pytest.fixture(scope='function')
def init_persistence(default_conf):
    init(default_conf)


def test_init_create_session(default_conf):
    # Check if init create a session
    init(default_conf)
    assert hasattr(Trade, 'session')
    assert 'Session' in type(Trade.session).__name__


def test_init_custom_db_url(default_conf, mocker):
    conf = deepcopy(default_conf)

    # Update path to a value other than default, but still in-memory
    conf.update({'db_url': 'sqlite:///tmp/freqtrade2_test.sqlite'})
    create_engine_mock = mocker.patch('freqtrade.persistence.create_engine', MagicMock())

    init(conf)
    assert create_engine_mock.call_count == 1
    assert create_engine_mock.mock_calls[0][1][0] == 'sqlite:///tmp/freqtrade2_test.sqlite'


def test_init_invalid_db_url(default_conf):
    conf = deepcopy(default_conf)

    # Update path to a value other than default, but still in-memory
    conf.update({'db_url': 'unknown:///some.url'})
    with pytest.raises(OperationalException, match=r'.*no valid database URL*'):
        init(conf)


def test_init_prod_db(default_conf, mocker):
    conf = deepcopy(default_conf)
    conf.update({'dry_run': False})
    conf.update({'db_url': constants.DEFAULT_DB_PROD_URL})

    create_engine_mock = mocker.patch('freqtrade.persistence.create_engine', MagicMock())

    init(conf)
    assert create_engine_mock.call_count == 1
    assert create_engine_mock.mock_calls[0][1][0] == 'sqlite:///tradesv3.sqlite'


def test_init_dryrun_db(default_conf, mocker):
    conf = deepcopy(default_conf)
    conf.update({'dry_run': True})
    conf.update({'db_url': constants.DEFAULT_DB_DRYRUN_URL})

    create_engine_mock = mocker.patch('freqtrade.persistence.create_engine', MagicMock())

    init(conf)
    assert create_engine_mock.call_count == 1
    assert create_engine_mock.mock_calls[0][1][0] == 'sqlite://'


@pytest.mark.usefixtures("init_persistence")
def test_update_with_bittrex(limit_buy_order, limit_sell_order, fee):
    """
    On this test we will buy and sell a crypto currency.

    Buy
    - Buy: 90.99181073 Crypto at 0.00001099 BTC
        (90.99181073*0.00001099 = 0.0009999 BTC)
    - Buying fee: 0.25%
    - Total cost of buy trade: 0.001002500 BTC
        ((90.99181073*0.00001099) + ((90.99181073*0.00001099)*0.0025))

    Sell
    - Sell: 90.99181073 Crypto at 0.00001173 BTC
        (90.99181073*0.00001173 = 0,00106733394 BTC)
    - Selling fee: 0.25%
    - Total cost of sell trade: 0.001064666 BTC
        ((90.99181073*0.00001173) - ((90.99181073*0.00001173)*0.0025))

    Profit/Loss: +0.000062166 BTC
        (Sell:0.001064666 - Buy:0.001002500)
    Profit/Loss percentage: 0.0620
        ((0.001064666/0.001002500)-1 = 6.20%)

    :param limit_buy_order:
    :param limit_sell_order:
    :return:
    """

    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )
    assert trade.open_order_id is None
    assert trade.open_rate is None
    assert trade.close_profit is None
    assert trade.close_date is None

    trade.open_order_id = 'something'
    trade.update(limit_buy_order)
    assert trade.open_order_id is None
    assert trade.open_rate == 0.00001099
    assert trade.close_profit is None
    assert trade.close_date is None

    trade.open_order_id = 'something'
    trade.update(limit_sell_order)
    assert trade.open_order_id is None
    assert trade.close_rate == 0.00001173
    assert trade.close_profit == 0.06201057
    assert trade.close_date is not None


@pytest.mark.usefixtures("init_persistence")
def test_calc_open_close_trade_price(limit_buy_order, limit_sell_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )

    trade.open_order_id = 'something'
    trade.update(limit_buy_order)
    assert trade.calc_open_trade_price() == 0.001002500

    trade.update(limit_sell_order)
    assert trade.calc_close_trade_price() == 0.0010646656

    # Profit in BTC
    assert trade.calc_profit() == 0.00006217

    # Profit in percent
    assert trade.calc_profit_percent() == 0.06201057


@pytest.mark.usefixtures("init_persistence")
def test_calc_close_trade_price_exception(limit_buy_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )

    trade.open_order_id = 'something'
    trade.update(limit_buy_order)
    assert trade.calc_close_trade_price() == 0.0


@pytest.mark.usefixtures("init_persistence")
def test_update_open_order(limit_buy_order):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=1.00,
        fee_open=0.1,
        fee_close=0.1,
        exchange='bittrex',
    )

    assert trade.open_order_id is None
    assert trade.open_rate is None
    assert trade.close_profit is None
    assert trade.close_date is None

    limit_buy_order['status'] = 'open'
    trade.update(limit_buy_order)

    assert trade.open_order_id is None
    assert trade.open_rate is None
    assert trade.close_profit is None
    assert trade.close_date is None


@pytest.mark.usefixtures("init_persistence")
def test_update_invalid_order(limit_buy_order):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=1.00,
        fee_open=0.1,
        fee_close=0.1,
        exchange='bittrex',
    )
    limit_buy_order['type'] = 'invalid'
    with pytest.raises(ValueError, match=r'Unknown order type'):
        trade.update(limit_buy_order)


@pytest.mark.usefixtures("init_persistence")
def test_calc_open_trade_price(limit_buy_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )
    trade.open_order_id = 'open_trade'
    trade.update(limit_buy_order)  # Buy @ 0.00001099

    # Get the open rate price with the standard fee rate
    assert trade.calc_open_trade_price() == 0.001002500

    # Get the open rate price with a custom fee rate
    assert trade.calc_open_trade_price(fee=0.003) == 0.001003000


@pytest.mark.usefixtures("init_persistence")
def test_calc_close_trade_price(limit_buy_order, limit_sell_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )
    trade.open_order_id = 'close_trade'
    trade.update(limit_buy_order)  # Buy @ 0.00001099

    # Get the close rate price with a custom close rate and a regular fee rate
    assert trade.calc_close_trade_price(rate=0.00001234) == 0.0011200318

    # Get the close rate price with a custom close rate and a custom fee rate
    assert trade.calc_close_trade_price(rate=0.00001234, fee=0.003) == 0.0011194704

    # Test when we apply a Sell order, and ask price with a custom fee rate
    trade.update(limit_sell_order)
    assert trade.calc_close_trade_price(fee=0.005) == 0.0010619972


@pytest.mark.usefixtures("init_persistence")
def test_calc_profit(limit_buy_order, limit_sell_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )
    trade.open_order_id = 'profit_percent'
    trade.update(limit_buy_order)  # Buy @ 0.00001099

    # Custom closing rate and regular fee rate
    # Higher than open rate
    assert trade.calc_profit(rate=0.00001234) == 0.00011753
    # Lower than open rate
    assert trade.calc_profit(rate=0.00000123) == -0.00089086

    # Custom closing rate and custom fee rate
    # Higher than open rate
    assert trade.calc_profit(rate=0.00001234, fee=0.003) == 0.00011697
    # Lower than open rate
    assert trade.calc_profit(rate=0.00000123, fee=0.003) == -0.00089092

    # Test when we apply a Sell order. Sell higher than open rate @ 0.00001173
    trade.update(limit_sell_order)
    assert trade.calc_profit() == 0.00006217

    # Test with a custom fee rate on the close trade
    assert trade.calc_profit(fee=0.003) == 0.00006163


@pytest.mark.usefixtures("init_persistence")
def test_calc_profit_percent(limit_buy_order, limit_sell_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
    )
    trade.open_order_id = 'profit_percent'
    trade.update(limit_buy_order)  # Buy @ 0.00001099

    # Get percent of profit with a custom rate (Higher than open rate)
    assert trade.calc_profit_percent(rate=0.00001234) == 0.1172387

    # Get percent of profit with a custom rate (Lower than open rate)
    assert trade.calc_profit_percent(rate=0.00000123) == -0.88863827

    # Test when we apply a Sell order. Sell higher than open rate @ 0.00001173
    trade.update(limit_sell_order)
    assert trade.calc_profit_percent() == 0.06201057

    # Test with a custom fee rate on the close trade
    assert trade.calc_profit_percent(fee=0.003) == 0.0614782


def test_clean_dry_run_db(default_conf, fee):
    init(default_conf)

    # Simulate dry_run entries
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        amount=123.0,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        open_rate=0.123,
        exchange='bittrex',
        open_order_id='dry_run_buy_12345'
    )
    Trade.session.add(trade)

    trade = Trade(
        pair='ETC/BTC',
        stake_amount=0.001,
        amount=123.0,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        open_rate=0.123,
        exchange='bittrex',
        open_order_id='dry_run_sell_12345'
    )
    Trade.session.add(trade)

    # Simulate prod entry
    trade = Trade(
        pair='ETC/BTC',
        stake_amount=0.001,
        amount=123.0,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        open_rate=0.123,
        exchange='bittrex',
        open_order_id='prod_buy_12345'
    )
    Trade.session.add(trade)

    # We have 3 entries: 2 dry_run, 1 prod
    assert len(Trade.query.filter(Trade.open_order_id.isnot(None)).all()) == 3

    clean_dry_run_db()

    # We have now only the prod
    assert len(Trade.query.filter(Trade.open_order_id.isnot(None)).all()) == 1


def test_migrate_old(mocker, default_conf, fee):
    """
    Test Database migration(starting with old pairformat)
    """
    amount = 103.223
    create_table_old = """CREATE TABLE IF NOT EXISTS "trades" (
                                id INTEGER NOT NULL,
                                exchange VARCHAR NOT NULL,
                                pair VARCHAR NOT NULL,
                                is_open BOOLEAN NOT NULL,
                                fee FLOAT NOT NULL,
                                open_rate FLOAT,
                                close_rate FLOAT,
                                close_profit FLOAT,
                                stake_amount FLOAT NOT NULL,
                                amount FLOAT,
                                open_date DATETIME NOT NULL,
                                close_date DATETIME,
                                open_order_id VARCHAR,
                                PRIMARY KEY (id),
                                CHECK (is_open IN (0, 1))
                                );"""
    insert_table_old = """INSERT INTO trades (exchange, pair, is_open, fee,
                          open_rate, stake_amount, amount, open_date)
                          VALUES ('BITTREX', 'BTC_ETC', 1, {fee},
                          0.00258580, {stake}, {amount},
                          '2017-11-28 12:44:24.000000')
                          """.format(fee=fee.return_value,
                                     stake=default_conf.get("stake_amount"),
                                     amount=amount
                                     )
    engine = create_engine('sqlite://')
    mocker.patch('freqtrade.persistence.create_engine', lambda *args, **kwargs: engine)

    # Create table using the old format
    engine.execute(create_table_old)
    engine.execute(insert_table_old)
    # Run init to test migration
    init(default_conf)

    assert len(Trade.query.filter(Trade.id == 1).all()) == 1
    trade = Trade.query.filter(Trade.id == 1).first()
    assert trade.fee_open == fee.return_value
    assert trade.fee_close == fee.return_value
    assert trade.open_rate_requested is None
    assert trade.close_rate_requested is None
    assert trade.is_open == 1
    assert trade.amount == amount
    assert trade.stake_amount == default_conf.get("stake_amount")
    assert trade.pair == "ETC/BTC"
    assert trade.exchange == "bittrex"
    assert trade.max_rate == 0.0
    assert trade.stop_loss == 0.0
    assert trade.initial_stop_loss == 0.0


def test_migrate_new(mocker, default_conf, fee, caplog):
    """
    Test Database migration (starting with new pairformat)
    """
    amount = 103.223
    create_table_old = """CREATE TABLE IF NOT EXISTS "trades" (
                                id INTEGER NOT NULL,
                                exchange VARCHAR NOT NULL,
                                pair VARCHAR NOT NULL,
                                is_open BOOLEAN NOT NULL,
                                fee FLOAT NOT NULL,
                                open_rate FLOAT,
                                close_rate FLOAT,
                                close_profit FLOAT,
                                stake_amount FLOAT NOT NULL,
                                amount FLOAT,
                                open_date DATETIME NOT NULL,
                                close_date DATETIME,
                                open_order_id VARCHAR,
                                PRIMARY KEY (id),
                                CHECK (is_open IN (0, 1))
                                );"""
    insert_table_old = """INSERT INTO trades (exchange, pair, is_open, fee,
                          open_rate, stake_amount, amount, open_date)
                          VALUES ('binance', 'ETC/BTC', 1, {fee},
                          0.00258580, {stake}, {amount},
                          '2019-11-28 12:44:24.000000')
                          """.format(fee=fee.return_value,
                                     stake=default_conf.get("stake_amount"),
                                     amount=amount
                                     )
    engine = create_engine('sqlite://')
    mocker.patch('freqtrade.persistence.create_engine', lambda *args, **kwargs: engine)

    # Create table using the old format
    engine.execute(create_table_old)
    engine.execute(insert_table_old)

    # fake previous backup
    engine.execute("create table trades_bak as select * from trades")

    engine.execute("create table trades_bak1 as select * from trades")
    # Run init to test migration
    init(default_conf)

    assert len(Trade.query.filter(Trade.id == 1).all()) == 1
    trade = Trade.query.filter(Trade.id == 1).first()
    assert trade.fee_open == fee.return_value
    assert trade.fee_close == fee.return_value
    assert trade.open_rate_requested is None
    assert trade.close_rate_requested is None
    assert trade.is_open == 1
    assert trade.amount == amount
    assert trade.stake_amount == default_conf.get("stake_amount")
    assert trade.pair == "ETC/BTC"
    assert trade.exchange == "binance"
    assert trade.max_rate == 0.0
    assert trade.stop_loss == 0.0
    assert trade.initial_stop_loss == 0.0
    assert trade.sell_reason is None
    assert trade.strategy is None
    assert trade.ticker_interval is None
    assert log_has("trying trades_bak1", caplog.record_tuples)
    assert log_has("trying trades_bak2", caplog.record_tuples)


def test_adjust_stop_loss(limit_buy_order, limit_sell_order, fee):
    trade = Trade(
        pair='ETH/BTC',
        stake_amount=0.001,
        fee_open=fee.return_value,
        fee_close=fee.return_value,
        exchange='bittrex',
        open_rate=1,
    )

    trade.adjust_stop_loss(trade.open_rate, 0.05, True)
    assert trade.stop_loss == 0.95
    assert trade.max_rate == 1
    assert trade.initial_stop_loss == 0.95

    # Get percent of profit with a lowre rate
    trade.adjust_stop_loss(0.96, 0.05)
    assert trade.stop_loss == 0.95
    assert trade.max_rate == 1
    assert trade.initial_stop_loss == 0.95

    # Get percent of profit with a custom rate (Higher than open rate)
    trade.adjust_stop_loss(1.3, -0.1)
    assert round(trade.stop_loss, 8) == 1.17
    assert trade.max_rate == 1.3
    assert trade.initial_stop_loss == 0.95

    # current rate lower again ... should not change
    trade.adjust_stop_loss(1.2, 0.1)
    assert round(trade.stop_loss, 8) == 1.17
    assert trade.max_rate == 1.3
    assert trade.initial_stop_loss == 0.95

    # current rate higher... should raise stoploss
    trade.adjust_stop_loss(1.4, 0.1)
    assert round(trade.stop_loss, 8) == 1.26
    assert trade.max_rate == 1.4
    assert trade.initial_stop_loss == 0.95

    #  Initial is true but stop_loss set - so doesn't do anything
    trade.adjust_stop_loss(1.7, 0.1, True)
    assert round(trade.stop_loss, 8) == 1.26
    assert trade.max_rate == 1.4
    assert trade.initial_stop_loss == 0.95
