# pragma pylint: disable=missing-docstring, W0212, line-too-long, C0103, unused-argument

import random
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock

import numpy as np
import pandas as pd
import pytest
from arrow import Arrow

from freqtrade import constants
from freqtrade.commands.optimize_commands import (setup_optimize_configuration,
                                                  start_backtesting)
from freqtrade.configuration import TimeRange
from freqtrade.data import history
from freqtrade.data.btanalysis import evaluate_result_multi
from freqtrade.data.converter import clean_ohlcv_dataframe
from freqtrade.data.dataprovider import DataProvider
from freqtrade.data.history import get_timerange
from freqtrade.exceptions import DependencyException, OperationalException
from freqtrade.optimize.backtesting import Backtesting
from freqtrade.resolvers import StrategyResolver
from freqtrade.state import RunMode
from freqtrade.strategy.interface import SellType
from tests.conftest import (get_args, log_has, log_has_re, patch_exchange,
                            patched_configuration_load_config_file)

ORDER_TYPES = [
    {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': False
    },
    {
        'buy': 'limit',
        'sell': 'limit',
        'stoploss': 'limit',
        'stoploss_on_exchange': True
    }]


def trim_dictlist(dict_list, num):
    new = {}
    for pair, pair_data in dict_list.items():
        new[pair] = pair_data[num:].reset_index()
    return new


def load_data_test(what, testdatadir):
    timerange = TimeRange.parse_timerange('1510694220-1510700340')
    data = history.load_pair_history(pair='UNITTEST/BTC', datadir=testdatadir,
                                     timeframe='1m', timerange=timerange,
                                     drop_incomplete=False,
                                     fill_up_missing=False)

    base = 0.001
    if what == 'raise':
        data.loc[:, 'open'] = data.index * base
        data.loc[:, 'high'] = data.index * base + 0.0001
        data.loc[:, 'low'] = data.index * base - 0.0001
        data.loc[:, 'close'] = data.index * base

    if what == 'lower':
        data.loc[:, 'open'] = 1 - data.index * base
        data.loc[:, 'high'] = 1 - data.index * base + 0.0001
        data.loc[:, 'low'] = 1 - data.index * base - 0.0001
        data.loc[:, 'close'] = 1 - data.index * base

    if what == 'sine':
        hz = 0.1  # frequency
        data.loc[:, 'open'] = np.sin(data.index * hz) / 1000 + base
        data.loc[:, 'high'] = np.sin(data.index * hz) / 1000 + base + 0.0001
        data.loc[:, 'low'] = np.sin(data.index * hz) / 1000 + base - 0.0001
        data.loc[:, 'close'] = np.sin(data.index * hz) / 1000 + base

    return {'UNITTEST/BTC': clean_ohlcv_dataframe(data, timeframe='1m', pair='UNITTEST/BTC',
                                                  fill_missing=True)}


def simple_backtest(config, contour, num_results, mocker, testdatadir) -> None:
    patch_exchange(mocker)
    config['timeframe'] = '1m'
    backtesting = Backtesting(config)

    data = load_data_test(contour, testdatadir)
    processed = backtesting.strategy.ohlcvdata_to_dataframe(data)
    min_date, max_date = get_timerange(processed)
    assert isinstance(processed, dict)
    results = backtesting.backtest(
        processed=processed,
        stake_amount=config['stake_amount'],
        start_date=min_date,
        end_date=max_date,
        max_open_trades=1,
        position_stacking=False,
    )
    # results :: <class 'pandas.core.frame.DataFrame'>
    assert len(results) == num_results


# FIX: fixturize this?
def _make_backtest_conf(mocker, datadir, conf=None, pair='UNITTEST/BTC'):
    data = history.load_data(datadir=datadir, timeframe='1m', pairs=[pair])
    data = trim_dictlist(data, -201)
    patch_exchange(mocker)
    backtesting = Backtesting(conf)
    processed = backtesting.strategy.ohlcvdata_to_dataframe(data)
    min_date, max_date = get_timerange(processed)
    return {
        'processed': processed,
        'stake_amount': conf['stake_amount'],
        'start_date': min_date,
        'end_date': max_date,
        'max_open_trades': 10,
        'position_stacking': False,
    }


def _trend(signals, buy_value, sell_value):
    n = len(signals['low'])
    buy = np.zeros(n)
    sell = np.zeros(n)
    for i in range(0, len(signals['buy'])):
        if random.random() > 0.5:  # Both buy and sell signals at same timeframe
            buy[i] = buy_value
            sell[i] = sell_value
    signals['buy'] = buy
    signals['sell'] = sell
    return signals


def _trend_alternate(dataframe=None, metadata=None):
    signals = dataframe
    low = signals['low']
    n = len(low)
    buy = np.zeros(n)
    sell = np.zeros(n)
    for i in range(0, len(buy)):
        if i % 2 == 0:
            buy[i] = 1
        else:
            sell[i] = 1
    signals['buy'] = buy
    signals['sell'] = sell
    return dataframe


# Unit tests
def test_setup_optimize_configuration_without_arguments(mocker, default_conf, caplog) -> None:
    patched_configuration_load_config_file(mocker, default_conf)

    args = [
        'backtesting',
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
    ]

    config = setup_optimize_configuration(get_args(args), RunMode.BACKTEST)
    assert 'max_open_trades' in config
    assert 'stake_currency' in config
    assert 'stake_amount' in config
    assert 'exchange' in config
    assert 'pair_whitelist' in config['exchange']
    assert 'datadir' in config
    assert log_has('Using data directory: {} ...'.format(config['datadir']), caplog)
    assert 'timeframe' in config
    assert not log_has_re('Parameter -i/--ticker-interval detected .*', caplog)

    assert 'position_stacking' not in config
    assert not log_has('Parameter --enable-position-stacking detected ...', caplog)

    assert 'timerange' not in config
    assert 'export' not in config
    assert 'runmode' in config
    assert config['runmode'] == RunMode.BACKTEST


def test_setup_bt_configuration_with_arguments(mocker, default_conf, caplog) -> None:
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch(
        'freqtrade.configuration.configuration.create_datadir',
        lambda c, x: x
    )

    args = [
        'backtesting',
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
        '--datadir', '/foo/bar',
        '--timeframe', '1m',
        '--enable-position-stacking',
        '--disable-max-market-positions',
        '--timerange', ':100',
        '--export', '/bar/foo',
        '--export-filename', 'foo_bar.json',
        '--fee', '0',
    ]

    config = setup_optimize_configuration(get_args(args), RunMode.BACKTEST)
    assert 'max_open_trades' in config
    assert 'stake_currency' in config
    assert 'stake_amount' in config
    assert 'exchange' in config
    assert 'pair_whitelist' in config['exchange']
    assert 'datadir' in config
    assert config['runmode'] == RunMode.BACKTEST

    assert log_has('Using data directory: {} ...'.format(config['datadir']), caplog)
    assert 'timeframe' in config
    assert log_has('Parameter -i/--timeframe detected ... Using timeframe: 1m ...',
                   caplog)

    assert 'position_stacking' in config
    assert log_has('Parameter --enable-position-stacking detected ...', caplog)

    assert 'use_max_market_positions' in config
    assert log_has('Parameter --disable-max-market-positions detected ...', caplog)
    assert log_has('max_open_trades set to unlimited ...', caplog)

    assert 'timerange' in config
    assert log_has('Parameter --timerange detected: {} ...'.format(config['timerange']), caplog)

    assert 'export' in config
    assert log_has('Parameter --export detected: {} ...'.format(config['export']), caplog)
    assert 'exportfilename' in config
    assert isinstance(config['exportfilename'], Path)
    assert log_has('Storing backtest results to {} ...'.format(config['exportfilename']), caplog)

    assert 'fee' in config
    assert log_has('Parameter --fee detected, setting fee to: {} ...'.format(config['fee']), caplog)


def test_setup_optimize_configuration_unlimited_stake_amount(mocker, default_conf, caplog) -> None:
    default_conf['stake_amount'] = constants.UNLIMITED_STAKE_AMOUNT

    patched_configuration_load_config_file(mocker, default_conf)

    args = [
        'backtesting',
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
    ]

    with pytest.raises(DependencyException, match=r'.`stake_amount`.*'):
        setup_optimize_configuration(get_args(args), RunMode.BACKTEST)


def test_start(mocker, fee, default_conf, caplog) -> None:
    start_mock = MagicMock()
    mocker.patch('freqtrade.exchange.Exchange.get_fee', fee)
    patch_exchange(mocker)
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.start', start_mock)
    patched_configuration_load_config_file(mocker, default_conf)

    args = [
        'backtesting',
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
    ]
    pargs = get_args(args)
    start_backtesting(pargs)
    assert log_has('Starting freqtrade in Backtesting mode', caplog)
    assert start_mock.call_count == 1


@pytest.mark.parametrize("order_types", ORDER_TYPES)
def test_backtesting_init(mocker, default_conf, order_types) -> None:
    """
    Check that stoploss_on_exchange is set to False while backtesting
    since backtesting assumes a perfect stoploss anyway.
    """
    default_conf["order_types"] = order_types
    patch_exchange(mocker)
    get_fee = mocker.patch('freqtrade.exchange.Exchange.get_fee', MagicMock(return_value=0.5))
    backtesting = Backtesting(default_conf)
    assert backtesting.config == default_conf
    assert backtesting.timeframe == '5m'
    assert callable(backtesting.strategy.ohlcvdata_to_dataframe)
    assert callable(backtesting.strategy.advise_buy)
    assert callable(backtesting.strategy.advise_sell)
    assert isinstance(backtesting.strategy.dp, DataProvider)
    get_fee.assert_called()
    assert backtesting.fee == 0.5
    assert not backtesting.strategy.order_types["stoploss_on_exchange"]


def test_backtesting_init_no_timeframe(mocker, default_conf, caplog) -> None:
    patch_exchange(mocker)
    del default_conf['timeframe']
    default_conf['strategy_list'] = ['DefaultStrategy',
                                     'SampleStrategy']

    mocker.patch('freqtrade.exchange.Exchange.get_fee', MagicMock(return_value=0.5))
    with pytest.raises(OperationalException):
        Backtesting(default_conf)
    log_has("Ticker-interval needs to be set in either configuration "
            "or as cli argument `--ticker-interval 5m`", caplog)


def test_data_with_fee(default_conf, mocker, testdatadir) -> None:
    patch_exchange(mocker)
    default_conf['fee'] = 0.1234

    fee_mock = mocker.patch('freqtrade.exchange.Exchange.get_fee', MagicMock(return_value=0.5))
    backtesting = Backtesting(default_conf)
    assert backtesting.fee == 0.1234
    assert fee_mock.call_count == 0


def test_data_to_dataframe_bt(default_conf, mocker, testdatadir) -> None:
    patch_exchange(mocker)
    timerange = TimeRange.parse_timerange('1510694220-1510700340')
    data = history.load_data(testdatadir, '1m', ['UNITTEST/BTC'], timerange=timerange,
                             fill_up_missing=True)
    backtesting = Backtesting(default_conf)
    processed = backtesting.strategy.ohlcvdata_to_dataframe(data)
    assert len(processed['UNITTEST/BTC']) == 102

    # Load strategy to compare the result between Backtesting function and strategy are the same
    default_conf.update({'strategy': 'DefaultStrategy'})
    strategy = StrategyResolver.load_strategy(default_conf)

    processed2 = strategy.ohlcvdata_to_dataframe(data)
    assert processed['UNITTEST/BTC'].equals(processed2['UNITTEST/BTC'])


def test_backtesting_start(default_conf, mocker, testdatadir, caplog) -> None:
    def get_timerange(input1):
        return Arrow(2017, 11, 14, 21, 17), Arrow(2017, 11, 14, 22, 59)

    mocker.patch('freqtrade.data.history.get_timerange', get_timerange)
    patch_exchange(mocker)
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.backtest')
    mocker.patch('freqtrade.optimize.backtesting.generate_backtest_stats')
    mocker.patch('freqtrade.optimize.backtesting.show_backtest_results')
    mocker.patch('freqtrade.pairlist.pairlistmanager.PairListManager.whitelist',
                 PropertyMock(return_value=['UNITTEST/BTC']))

    default_conf['timeframe'] = '1m'
    default_conf['datadir'] = testdatadir
    default_conf['export'] = None
    default_conf['timerange'] = '-1510694220'

    backtesting = Backtesting(default_conf)
    backtesting.start()
    # check the logs, that will contain the backtest result
    exists = [
        'Using stake_currency: BTC ...',
        'Using stake_amount: 0.001 ...',
        'Backtesting with data from 2017-11-14T21:17:00+00:00 '
        'up to 2017-11-14T22:59:00+00:00 (0 days)..'
    ]
    for line in exists:
        assert log_has(line, caplog)


def test_backtesting_start_no_data(default_conf, mocker, caplog, testdatadir) -> None:
    def get_timerange(input1):
        return Arrow(2017, 11, 14, 21, 17), Arrow(2017, 11, 14, 22, 59)

    mocker.patch('freqtrade.data.history.history_utils.load_pair_history',
                 MagicMock(return_value=pd.DataFrame()))
    mocker.patch('freqtrade.data.history.get_timerange', get_timerange)
    patch_exchange(mocker)
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.backtest')
    mocker.patch('freqtrade.pairlist.pairlistmanager.PairListManager.whitelist',
                 PropertyMock(return_value=['UNITTEST/BTC']))

    default_conf['timeframe'] = "1m"
    default_conf['datadir'] = testdatadir
    default_conf['export'] = None
    default_conf['timerange'] = '20180101-20180102'

    backtesting = Backtesting(default_conf)
    with pytest.raises(OperationalException, match='No data found. Terminating.'):
        backtesting.start()


def test_backtesting_no_pair_left(default_conf, mocker, caplog, testdatadir) -> None:
    mocker.patch('freqtrade.exchange.Exchange.exchange_has', MagicMock(return_value=True))
    mocker.patch('freqtrade.data.history.history_utils.load_pair_history',
                 MagicMock(return_value=pd.DataFrame()))
    mocker.patch('freqtrade.data.history.get_timerange', get_timerange)
    patch_exchange(mocker)
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.backtest')
    mocker.patch('freqtrade.pairlist.pairlistmanager.PairListManager.whitelist',
                 PropertyMock(return_value=[]))

    default_conf['timeframe'] = "1m"
    default_conf['datadir'] = testdatadir
    default_conf['export'] = None
    default_conf['timerange'] = '20180101-20180102'

    with pytest.raises(OperationalException, match='No pair in whitelist.'):
        Backtesting(default_conf)

    default_conf['pairlists'] = [{"method": "VolumePairList", "number_assets": 5}]
    with pytest.raises(OperationalException, match='VolumePairList not allowed for backtesting.'):
        Backtesting(default_conf)


def test_backtest(default_conf, fee, mocker, testdatadir) -> None:
    default_conf['ask_strategy']['use_sell_signal'] = False
    mocker.patch('freqtrade.exchange.Exchange.get_fee', fee)
    patch_exchange(mocker)
    backtesting = Backtesting(default_conf)
    pair = 'UNITTEST/BTC'
    timerange = TimeRange('date', None, 1517227800, 0)
    data = history.load_data(datadir=testdatadir, timeframe='5m', pairs=['UNITTEST/BTC'],
                             timerange=timerange)
    processed = backtesting.strategy.ohlcvdata_to_dataframe(data)
    min_date, max_date = get_timerange(processed)
    results = backtesting.backtest(
        processed=processed,
        stake_amount=default_conf['stake_amount'],
        start_date=min_date,
        end_date=max_date,
        max_open_trades=10,
        position_stacking=False,
    )
    assert not results.empty
    assert len(results) == 2

    expected = pd.DataFrame(
        {'pair': [pair, pair],
         'profit_percent': [0.0, 0.0],
         'profit_abs': [0.0, 0.0],
         'open_time': pd.to_datetime([Arrow(2018, 1, 29, 18, 40, 0).datetime,
                                      Arrow(2018, 1, 30, 3, 30, 0).datetime], utc=True
                                     ),
         'close_time': pd.to_datetime([Arrow(2018, 1, 29, 22, 35, 0).datetime,
                                       Arrow(2018, 1, 30, 4, 10, 0).datetime], utc=True),
         'open_index': [78, 184],
         'close_index': [125, 192],
         'trade_duration': [235, 40],
         'open_at_end': [False, False],
         'open_rate': [0.104445, 0.10302485],
         'close_rate': [0.104969, 0.103541],
         'sell_reason': [SellType.ROI, SellType.ROI]
         })
    pd.testing.assert_frame_equal(results, expected)
    data_pair = processed[pair]
    for _, t in results.iterrows():
        ln = data_pair.loc[data_pair["date"] == t["open_time"]]
        # Check open trade rate alignes to open rate
        assert ln is not None
        assert round(ln.iloc[0]["open"], 6) == round(t["open_rate"], 6)
        # check close trade rate alignes to close rate or is between high and low
        ln = data_pair.loc[data_pair["date"] == t["close_time"]]
        assert (round(ln.iloc[0]["open"], 6) == round(t["close_rate"], 6) or
                round(ln.iloc[0]["low"], 6) < round(
                t["close_rate"], 6) < round(ln.iloc[0]["high"], 6))


def test_backtest_1min_timeframe(default_conf, fee, mocker, testdatadir) -> None:
    default_conf['ask_strategy']['use_sell_signal'] = False
    mocker.patch('freqtrade.exchange.Exchange.get_fee', fee)
    patch_exchange(mocker)
    backtesting = Backtesting(default_conf)

    # Run a backtesting for an exiting 1min timeframe
    timerange = TimeRange.parse_timerange('1510688220-1510700340')
    data = history.load_data(datadir=testdatadir, timeframe='1m', pairs=['UNITTEST/BTC'],
                             timerange=timerange)
    processed = backtesting.strategy.ohlcvdata_to_dataframe(data)
    min_date, max_date = get_timerange(processed)
    results = backtesting.backtest(
        processed=processed,
        stake_amount=default_conf['stake_amount'],
        start_date=min_date,
        end_date=max_date,
        max_open_trades=1,
        position_stacking=False,
    )
    assert not results.empty
    assert len(results) == 1


def test_processed(default_conf, mocker, testdatadir) -> None:
    patch_exchange(mocker)
    backtesting = Backtesting(default_conf)

    dict_of_tickerrows = load_data_test('raise', testdatadir)
    dataframes = backtesting.strategy.ohlcvdata_to_dataframe(dict_of_tickerrows)
    dataframe = dataframes['UNITTEST/BTC']
    cols = dataframe.columns
    # assert the dataframe got some of the indicator columns
    for col in ['close', 'high', 'low', 'open', 'date',
                'ema10', 'rsi', 'fastd', 'plus_di']:
        assert col in cols


def test_backtest_pricecontours(default_conf, fee, mocker, testdatadir) -> None:
    # TODO: Evaluate usefullness of this, the patterns and buy-signls are unrealistic
    mocker.patch('freqtrade.exchange.Exchange.get_fee', fee)
    tests = [['raise', 19], ['lower', 0], ['sine', 35]]

    for [contour, numres] in tests:
        simple_backtest(default_conf, contour, numres, mocker, testdatadir)


def test_backtest_clash_buy_sell(mocker, default_conf, testdatadir):
    # Override the default buy trend function in our default_strategy
    def fun(dataframe=None, pair=None):
        buy_value = 1
        sell_value = 1
        return _trend(dataframe, buy_value, sell_value)

    backtest_conf = _make_backtest_conf(mocker, conf=default_conf, datadir=testdatadir)
    backtesting = Backtesting(default_conf)
    backtesting.strategy.advise_buy = fun  # Override
    backtesting.strategy.advise_sell = fun  # Override
    results = backtesting.backtest(**backtest_conf)
    assert results.empty


def test_backtest_only_sell(mocker, default_conf, testdatadir):
    # Override the default buy trend function in our default_strategy
    def fun(dataframe=None, pair=None):
        buy_value = 0
        sell_value = 1
        return _trend(dataframe, buy_value, sell_value)

    backtest_conf = _make_backtest_conf(mocker, conf=default_conf, datadir=testdatadir)
    backtesting = Backtesting(default_conf)
    backtesting.strategy.advise_buy = fun  # Override
    backtesting.strategy.advise_sell = fun  # Override
    results = backtesting.backtest(**backtest_conf)
    assert results.empty


def test_backtest_alternate_buy_sell(default_conf, fee, mocker, testdatadir):
    mocker.patch('freqtrade.exchange.Exchange.get_fee', fee)
    backtest_conf = _make_backtest_conf(mocker, conf=default_conf,
                                        pair='UNITTEST/BTC', datadir=testdatadir)
    default_conf['timeframe'] = '1m'
    backtesting = Backtesting(default_conf)
    backtesting.strategy.advise_buy = _trend_alternate  # Override
    backtesting.strategy.advise_sell = _trend_alternate  # Override
    results = backtesting.backtest(**backtest_conf)
    # 200 candles in backtest data
    # won't buy on first (shifted by 1)
    # 100 buys signals
    assert len(results) == 100
    # One trade was force-closed at the end
    assert len(results.loc[results.open_at_end]) == 0


@pytest.mark.parametrize("pair", ['ADA/BTC', 'LTC/BTC'])
@pytest.mark.parametrize("tres", [0, 20, 30])
def test_backtest_multi_pair(default_conf, fee, mocker, tres, pair, testdatadir):

    def _trend_alternate_hold(dataframe=None, metadata=None):
        """
        Buy every xth candle - sell every other xth -2 (hold on to pairs a bit)
        """
        if metadata['pair'] in ('ETH/BTC', 'LTC/BTC'):
            multi = 20
        else:
            multi = 18
        dataframe['buy'] = np.where(dataframe.index % multi == 0, 1, 0)
        dataframe['sell'] = np.where((dataframe.index + multi - 2) % multi == 0, 1, 0)
        return dataframe

    mocker.patch('freqtrade.exchange.Exchange.get_fee', fee)
    patch_exchange(mocker)

    pairs = ['ADA/BTC', 'DASH/BTC', 'ETH/BTC', 'LTC/BTC', 'NXT/BTC']
    data = history.load_data(datadir=testdatadir, timeframe='5m', pairs=pairs)
    # Only use 500 lines to increase performance
    data = trim_dictlist(data, -500)

    # Remove data for one pair from the beginning of the data
    data[pair] = data[pair][tres:].reset_index()
    default_conf['timeframe'] = '5m'

    backtesting = Backtesting(default_conf)
    backtesting.strategy.advise_buy = _trend_alternate_hold  # Override
    backtesting.strategy.advise_sell = _trend_alternate_hold  # Override

    processed = backtesting.strategy.ohlcvdata_to_dataframe(data)
    min_date, max_date = get_timerange(processed)
    backtest_conf = {
        'processed': processed,
        'stake_amount': default_conf['stake_amount'],
        'start_date': min_date,
        'end_date': max_date,
        'max_open_trades': 3,
        'position_stacking': False,
    }

    results = backtesting.backtest(**backtest_conf)

    # Make sure we have parallel trades
    assert len(evaluate_result_multi(results, '5m', 2)) > 0
    # make sure we don't have trades with more than configured max_open_trades
    assert len(evaluate_result_multi(results, '5m', 3)) == 0

    backtest_conf = {
        'processed': processed,
        'stake_amount': default_conf['stake_amount'],
        'start_date': min_date,
        'end_date': max_date,
        'max_open_trades': 1,
        'position_stacking': False,
    }
    results = backtesting.backtest(**backtest_conf)
    assert len(evaluate_result_multi(results, '5m', 1)) == 0


def test_backtest_start_timerange(default_conf, mocker, caplog, testdatadir):

    patch_exchange(mocker)
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.backtest')
    mocker.patch('freqtrade.optimize.backtesting.generate_backtest_stats')
    mocker.patch('freqtrade.optimize.backtesting.show_backtest_results')
    mocker.patch('freqtrade.pairlist.pairlistmanager.PairListManager.whitelist',
                 PropertyMock(return_value=['UNITTEST/BTC']))
    patched_configuration_load_config_file(mocker, default_conf)

    args = [
        'backtesting',
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
        '--datadir', str(testdatadir),
        '--timeframe', '1m',
        '--timerange', '1510694220-1510700340',
        '--enable-position-stacking',
        '--disable-max-market-positions'
    ]
    args = get_args(args)
    start_backtesting(args)
    # check the logs, that will contain the backtest result
    exists = [
        'Parameter -i/--timeframe detected ... Using timeframe: 1m ...',
        'Ignoring max_open_trades (--disable-max-market-positions was used) ...',
        'Parameter --timerange detected: 1510694220-1510700340 ...',
        f'Using data directory: {testdatadir} ...',
        'Using stake_currency: BTC ...',
        'Using stake_amount: 0.001 ...',
        'Loading data from 2017-11-14T20:57:00+00:00 '
        'up to 2017-11-14T22:58:00+00:00 (0 days)..',
        'Backtesting with data from 2017-11-14T21:17:00+00:00 '
        'up to 2017-11-14T22:58:00+00:00 (0 days)..',
        'Parameter --enable-position-stacking detected ...'
    ]

    for line in exists:
        assert log_has(line, caplog)


@pytest.mark.filterwarnings("ignore:deprecated")
def test_backtest_start_multi_strat(default_conf, mocker, caplog, testdatadir):

    patch_exchange(mocker)
    backtestmock = MagicMock()
    mocker.patch('freqtrade.pairlist.pairlistmanager.PairListManager.whitelist',
                 PropertyMock(return_value=['UNITTEST/BTC']))
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.backtest', backtestmock)
    text_table_mock = MagicMock()
    sell_reason_mock = MagicMock()
    strattable_mock = MagicMock()
    strat_summary = MagicMock()

    mocker.patch.multiple('freqtrade.optimize.optimize_reports',
                          text_table_bt_results=text_table_mock,
                          text_table_strategy=strattable_mock,
                          generate_pair_metrics=MagicMock(),
                          generate_sell_reason_stats=sell_reason_mock,
                          generate_strategy_metrics=strat_summary,
                          )
    patched_configuration_load_config_file(mocker, default_conf)

    args = [
        'backtesting',
        '--config', 'config.json',
        '--datadir', str(testdatadir),
        '--strategy-path', str(Path(__file__).parents[1] / 'strategy/strats'),
        '--timeframe', '1m',
        '--timerange', '1510694220-1510700340',
        '--enable-position-stacking',
        '--disable-max-market-positions',
        '--strategy-list',
        'DefaultStrategy',
        'TestStrategyLegacy',
    ]
    args = get_args(args)
    start_backtesting(args)
    # 2 backtests, 4 tables
    assert backtestmock.call_count == 2
    assert text_table_mock.call_count == 4
    assert strattable_mock.call_count == 1
    assert sell_reason_mock.call_count == 2
    assert strat_summary.call_count == 1

    # check the logs, that will contain the backtest result
    exists = [
        'Parameter -i/--timeframe detected ... Using timeframe: 1m ...',
        'Ignoring max_open_trades (--disable-max-market-positions was used) ...',
        'Parameter --timerange detected: 1510694220-1510700340 ...',
        f'Using data directory: {testdatadir} ...',
        'Using stake_currency: BTC ...',
        'Using stake_amount: 0.001 ...',
        'Loading data from 2017-11-14T20:57:00+00:00 '
        'up to 2017-11-14T22:58:00+00:00 (0 days)..',
        'Backtesting with data from 2017-11-14T21:17:00+00:00 '
        'up to 2017-11-14T22:58:00+00:00 (0 days)..',
        'Parameter --enable-position-stacking detected ...',
        'Running backtesting for Strategy DefaultStrategy',
        'Running backtesting for Strategy TestStrategyLegacy',
    ]

    for line in exists:
        assert log_has(line, caplog)


@pytest.mark.filterwarnings("ignore:deprecated")
def test_backtest_start_multi_strat_nomock(default_conf, mocker, caplog, testdatadir, capsys):

    patch_exchange(mocker)
    backtestmock = MagicMock(side_effect=[
        pd.DataFrame({'pair': ['XRP/BTC', 'LTC/BTC'],
                      'profit_percent': [0.0, 0.0],
                      'profit_abs': [0.0, 0.0],
                      'open_time': pd.to_datetime(['2018-01-29 18:40:00',
                                                   '2018-01-30 03:30:00', ], utc=True
                                                  ),
                      'close_time': pd.to_datetime(['2018-01-29 20:45:00',
                                                    '2018-01-30 05:35:00', ], utc=True),
                      'open_index': [78, 184],
                      'close_index': [125, 192],
                      'trade_duration': [235, 40],
                      'open_at_end': [False, False],
                      'open_rate': [0.104445, 0.10302485],
                      'close_rate': [0.104969, 0.103541],
                      'sell_reason': [SellType.ROI, SellType.ROI]
                      }),
        pd.DataFrame({'pair': ['XRP/BTC', 'LTC/BTC', 'ETH/BTC'],
                      'profit_percent': [0.03, 0.01, 0.1],
                      'profit_abs': [0.01, 0.02, 0.2],
                      'open_time': pd.to_datetime(['2018-01-29 18:40:00',
                                                   '2018-01-30 03:30:00',
                                                   '2018-01-30 05:30:00'], utc=True
                                                  ),
                      'close_time': pd.to_datetime(['2018-01-29 20:45:00',
                                                    '2018-01-30 05:35:00',
                                                    '2018-01-30 08:30:00'], utc=True),
                      'open_index': [78, 184, 185],
                      'close_index': [125, 224, 205],
                      'trade_duration': [47, 40, 20],
                      'open_at_end': [False, False, False],
                      'open_rate': [0.104445, 0.10302485, 0.122541],
                      'close_rate': [0.104969, 0.103541, 0.123541],
                      'sell_reason': [SellType.ROI, SellType.ROI, SellType.STOP_LOSS]
                      }),
    ])
    mocker.patch('freqtrade.pairlist.pairlistmanager.PairListManager.whitelist',
                 PropertyMock(return_value=['UNITTEST/BTC']))
    mocker.patch('freqtrade.optimize.backtesting.Backtesting.backtest', backtestmock)

    patched_configuration_load_config_file(mocker, default_conf)

    args = [
        'backtesting',
        '--config', 'config.json',
        '--datadir', str(testdatadir),
        '--strategy-path', str(Path(__file__).parents[1] / 'strategy/strats'),
        '--timeframe', '1m',
        '--timerange', '1510694220-1510700340',
        '--enable-position-stacking',
        '--disable-max-market-positions',
        '--strategy-list',
        'DefaultStrategy',
        'TestStrategyLegacy',
    ]
    args = get_args(args)
    start_backtesting(args)

    # check the logs, that will contain the backtest result
    exists = [
        'Parameter -i/--timeframe detected ... Using timeframe: 1m ...',
        'Ignoring max_open_trades (--disable-max-market-positions was used) ...',
        'Parameter --timerange detected: 1510694220-1510700340 ...',
        f'Using data directory: {testdatadir} ...',
        'Using stake_currency: BTC ...',
        'Using stake_amount: 0.001 ...',
        'Loading data from 2017-11-14T20:57:00+00:00 '
        'up to 2017-11-14T22:58:00+00:00 (0 days)..',
        'Backtesting with data from 2017-11-14T21:17:00+00:00 '
        'up to 2017-11-14T22:58:00+00:00 (0 days)..',
        'Parameter --enable-position-stacking detected ...',
        'Running backtesting for Strategy DefaultStrategy',
        'Running backtesting for Strategy TestStrategyLegacy',
    ]

    for line in exists:
        assert log_has(line, caplog)

    captured = capsys.readouterr()
    assert 'BACKTESTING REPORT' in captured.out
    assert 'SELL REASON STATS' in captured.out
    assert 'LEFT OPEN TRADES REPORT' in captured.out
    assert 'STRATEGY SUMMARY' in captured.out
