# pragma pylint: disable=missing-docstring,W0212,C0103
from datetime import datetime
import os
from unittest.mock import MagicMock

import pandas as pd
import pytest

from freqtrade.optimize import load_tickerdata_file
from freqtrade.optimize.hyperopt import Hyperopt, start
from freqtrade.strategy.resolver import StrategyResolver
from freqtrade.tests.conftest import log_has, patch_exchange
from freqtrade.tests.optimize.test_backtesting import get_args


@pytest.fixture(scope='function')
def hyperopt(default_conf, mocker):
    patch_exchange(mocker)
    return Hyperopt(default_conf)


# Functions for recurrent object patching
def create_trials(mocker, hyperopt) -> None:
    """
    When creating trials, mock the hyperopt Trials so that *by default*
      - we don't create any pickle'd files in the filesystem
      - we might have a pickle'd file so make sure that we return
        false when looking for it
    """
    hyperopt.trials_file = os.path.join('freqtrade', 'tests', 'optimize', 'ut_trials.pickle')

    mocker.patch('freqtrade.optimize.hyperopt.os.path.exists', return_value=False)
    mocker.patch('freqtrade.optimize.hyperopt.os.path.getsize', return_value=1)
    mocker.patch('freqtrade.optimize.hyperopt.os.remove', return_value=True)
    mocker.patch('freqtrade.optimize.hyperopt.dump', return_value=None)

    return [{'loss': 1, 'result': 'foo', 'params': {}}]


def test_start(mocker, default_conf, caplog) -> None:
    start_mock = MagicMock()
    mocker.patch(
        'freqtrade.configuration.Configuration._load_config_file',
        lambda *args, **kwargs: default_conf
    )
    mocker.patch('freqtrade.optimize.hyperopt.Hyperopt.start', start_mock)
    patch_exchange(mocker)

    args = [
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
        'hyperopt',
        '--epochs', '5'
    ]
    args = get_args(args)
    StrategyResolver({'strategy': 'DefaultStrategy'})
    start(args)

    import pprint
    pprint.pprint(caplog.record_tuples)

    assert log_has(
        'Starting freqtrade in Hyperopt mode',
        caplog.record_tuples
    )
    assert start_mock.call_count == 1


def test_start_failure(mocker, default_conf, caplog) -> None:
    start_mock = MagicMock()
    mocker.patch(
        'freqtrade.configuration.Configuration._load_config_file',
        lambda *args, **kwargs: default_conf
    )
    mocker.patch('freqtrade.optimize.hyperopt.Hyperopt.start', start_mock)
    patch_exchange(mocker)

    args = [
        '--config', 'config.json',
        '--strategy', 'TestStrategy',
        'hyperopt',
        '--epochs', '5'
    ]
    args = get_args(args)
    StrategyResolver({'strategy': 'DefaultStrategy'})
    with pytest.raises(ValueError):
        start(args)
    assert log_has(
        "Please don't use --strategy for hyperopt.",
        caplog.record_tuples
    )


def test_loss_calculation_prefer_correct_trade_count(hyperopt) -> None:
    StrategyResolver({'strategy': 'DefaultStrategy'})

    correct = hyperopt.calculate_loss(1, hyperopt.target_trades, 20)
    over = hyperopt.calculate_loss(1, hyperopt.target_trades + 100, 20)
    under = hyperopt.calculate_loss(1, hyperopt.target_trades - 100, 20)
    assert over > correct
    assert under > correct


def test_loss_calculation_prefer_shorter_trades(hyperopt) -> None:
    shorter = hyperopt.calculate_loss(1, 100, 20)
    longer = hyperopt.calculate_loss(1, 100, 30)
    assert shorter < longer


def test_loss_calculation_has_limited_profit(hyperopt) -> None:
    correct = hyperopt.calculate_loss(hyperopt.expected_max_profit, hyperopt.target_trades, 20)
    over = hyperopt.calculate_loss(hyperopt.expected_max_profit * 2, hyperopt.target_trades, 20)
    under = hyperopt.calculate_loss(hyperopt.expected_max_profit / 2, hyperopt.target_trades, 20)
    assert over == correct
    assert under > correct


def test_log_results_if_loss_improves(hyperopt, capsys) -> None:
    hyperopt.current_best_loss = 2
    hyperopt.log_results(
        {
            'loss': 1,
            'current_tries': 1,
            'total_tries': 2,
            'result': 'foo'
        }
    )
    out, err = capsys.readouterr()
    assert '    1/2: foo. Loss 1.00000' in out


def test_no_log_if_loss_does_not_improve(hyperopt, caplog) -> None:
    hyperopt.current_best_loss = 2
    hyperopt.log_results(
        {
            'loss': 3,
        }
    )
    assert caplog.record_tuples == []


def test_save_trials_saves_trials(mocker, hyperopt, caplog) -> None:
    trials = create_trials(mocker, hyperopt)
    mock_dump = mocker.patch('freqtrade.optimize.hyperopt.dump', return_value=None)
    hyperopt.trials = trials
    hyperopt.save_trials()

    trials_file = os.path.join('freqtrade', 'tests', 'optimize', 'ut_trials.pickle')
    assert log_has(
        'Saving 1 evaluations to \'{}\''.format(trials_file),
        caplog.record_tuples
    )
    mock_dump.assert_called_once()


def test_read_trials_returns_trials_file(mocker, hyperopt, caplog) -> None:
    trials = create_trials(mocker, hyperopt)
    mock_load = mocker.patch('freqtrade.optimize.hyperopt.load', return_value=trials)
    hyperopt_trial = hyperopt.read_trials()
    trials_file = os.path.join('freqtrade', 'tests', 'optimize', 'ut_trials.pickle')
    assert log_has(
        'Reading Trials from \'{}\''.format(trials_file),
        caplog.record_tuples
    )
    assert hyperopt_trial == trials
    mock_load.assert_called_once()


def test_roi_table_generation(hyperopt) -> None:
    params = {
        'roi_t1': 5,
        'roi_t2': 10,
        'roi_t3': 15,
        'roi_p1': 1,
        'roi_p2': 2,
        'roi_p3': 3,
    }

    assert hyperopt.generate_roi_table(params) == {0: 6, 15: 3, 25: 1, 30: 0}


def test_start_calls_optimizer(mocker, default_conf, caplog) -> None:
    dumper = mocker.patch('freqtrade.optimize.hyperopt.dump', MagicMock())
    mocker.patch('freqtrade.optimize.hyperopt.load_data', MagicMock())
    mocker.patch('freqtrade.optimize.hyperopt.multiprocessing.cpu_count', MagicMock(return_value=1))
    parallel = mocker.patch(
        'freqtrade.optimize.hyperopt.Hyperopt.run_optimizer_parallel',
        MagicMock(return_value=[{'loss': 1, 'result': 'foo result', 'params': {}}])
    )
    patch_exchange(mocker)

    default_conf.update({'config': 'config.json.example'})
    default_conf.update({'epochs': 1})
    default_conf.update({'timerange': None})
    default_conf.update({'spaces': 'all'})

    hyperopt = Hyperopt(default_conf)
    hyperopt.strategy.tickerdata_to_dataframe = MagicMock()

    hyperopt.start()
    parallel.assert_called_once()

    assert 'Best result:\nfoo result\nwith values:\n{}' in caplog.text
    assert dumper.called


def test_format_results(hyperopt):
    # Test with BTC as stake_currency
    trades = [
        ('ETH/BTC', 2, 2, 123),
        ('LTC/BTC', 1, 1, 123),
        ('XPR/BTC', -1, -2, -246)
    ]
    labels = ['currency', 'profit_percent', 'profit_abs', 'trade_duration']
    df = pd.DataFrame.from_records(trades, columns=labels)

    result = hyperopt.format_results(df)
    assert result.find(' 66.67%')
    assert result.find('Total profit 1.00000000 BTC')
    assert result.find('2.0000Σ %')

    # Test with EUR as stake_currency
    trades = [
        ('ETH/EUR', 2, 2, 123),
        ('LTC/EUR', 1, 1, 123),
        ('XPR/EUR', -1, -2, -246)
    ]
    df = pd.DataFrame.from_records(trades, columns=labels)
    result = hyperopt.format_results(df)
    assert result.find('Total profit 1.00000000 EUR')


def test_has_space(hyperopt):
    hyperopt.config.update({'spaces': ['buy', 'roi']})
    assert hyperopt.has_space('roi')
    assert hyperopt.has_space('buy')
    assert not hyperopt.has_space('stoploss')

    hyperopt.config.update({'spaces': ['all']})
    assert hyperopt.has_space('buy')


def test_populate_indicators(hyperopt) -> None:
    tick = load_tickerdata_file(None, 'UNITTEST/BTC', '1m')
    tickerlist = {'UNITTEST/BTC': tick}
    dataframes = hyperopt.strategy.tickerdata_to_dataframe(tickerlist)
    dataframe = hyperopt.populate_indicators(dataframes['UNITTEST/BTC'], {'pair': 'UNITTEST/BTC'})

    # Check if some indicators are generated. We will not test all of them
    assert 'adx' in dataframe
    assert 'mfi' in dataframe
    assert 'rsi' in dataframe


def test_buy_strategy_generator(hyperopt) -> None:
    tick = load_tickerdata_file(None, 'UNITTEST/BTC', '1m')
    tickerlist = {'UNITTEST/BTC': tick}
    dataframes = hyperopt.strategy.tickerdata_to_dataframe(tickerlist)
    dataframe = hyperopt.populate_indicators(dataframes['UNITTEST/BTC'], {'pair': 'UNITTEST/BTC'})

    populate_buy_trend = hyperopt.buy_strategy_generator(
        {
            'adx-value': 20,
            'fastd-value': 20,
            'mfi-value': 20,
            'rsi-value': 20,
            'adx-enabled': True,
            'fastd-enabled': True,
            'mfi-enabled': True,
            'rsi-enabled': True,
            'trigger': 'bb_lower'
        }
    )
    result = populate_buy_trend(dataframe, {'pair': 'UNITTEST/BTC'})
    # Check if some indicators are generated. We will not test all of them
    assert 'buy' in result
    assert 1 in result['buy']


def test_generate_optimizer(mocker, default_conf) -> None:
    default_conf.update({'config': 'config.json.example'})
    default_conf.update({'timerange': None})
    default_conf.update({'spaces': 'all'})

    trades = [
        ('POWR/BTC', 0.023117, 0.000233, 100)
    ]
    labels = ['currency', 'profit_percent', 'profit_abs', 'trade_duration']
    backtest_result = pd.DataFrame.from_records(trades, columns=labels)

    mocker.patch(
        'freqtrade.optimize.hyperopt.Hyperopt.backtest',
        MagicMock(return_value=backtest_result)
    )
    mocker.patch(
        'freqtrade.optimize.hyperopt.get_timeframe',
        MagicMock(return_value=(datetime(2017, 12, 10), datetime(2017, 12, 13)))
    )
    patch_exchange(mocker)
    mocker.patch('freqtrade.optimize.hyperopt.load', MagicMock())

    optimizer_param = {
        'adx-value': 0,
        'fastd-value': 35,
        'mfi-value': 0,
        'rsi-value': 0,
        'adx-enabled': False,
        'fastd-enabled': True,
        'mfi-enabled': False,
        'rsi-enabled': False,
        'trigger': 'macd_cross_signal',
        'roi_t1': 60.0,
        'roi_t2': 30.0,
        'roi_t3': 20.0,
        'roi_p1': 0.01,
        'roi_p2': 0.01,
        'roi_p3': 0.1,
        'stoploss': -0.4,
    }
    response_expected = {
        'loss': 1.9840569076926293,
        'result': '     1 trades. Avg profit  2.31%. Total profit  0.00023300 BTC '
                  '(0.0231Σ%). Avg duration 100.0 mins.',
        'params': optimizer_param
    }

    hyperopt = Hyperopt(default_conf)
    generate_optimizer_value = hyperopt.generate_optimizer(list(optimizer_param.values()))
    assert generate_optimizer_value == response_expected
