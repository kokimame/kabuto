# pragma pylint: disable=missing-docstring

from copy import deepcopy
from unittest.mock import MagicMock, PropertyMock

import pytest

from freqtrade import OperationalException
from freqtrade.configuration import Arguments
from freqtrade.freqtradebot import FreqtradeBot
from freqtrade.main import main
from freqtrade.state import State
from freqtrade.worker import Worker
from tests.conftest import (log_has, patch_exchange,
                            patched_configuration_load_config_file)


def test_parse_args_backtesting(mocker) -> None:
    """
    Test that main() can start backtesting and also ensure we can pass some specific arguments
    further argument parsing is done in test_arguments.py
    """
    backtesting_mock = mocker.patch('freqtrade.optimize.start_backtesting', MagicMock())
    backtesting_mock.__name__ = PropertyMock("start_backtesting")
    # it's sys.exit(0) at the end of backtesting
    with pytest.raises(SystemExit):
        main(['backtesting'])
    assert backtesting_mock.call_count == 1
    call_args = backtesting_mock.call_args[0][0]
    assert call_args["config"] == ['config.json']
    assert call_args["verbosity"] == 0
    assert call_args["subparser"] == 'backtesting'
    assert call_args["func"] is not None
    assert callable(call_args["func"])
    assert call_args["ticker_interval"] is None


def test_main_start_hyperopt(mocker) -> None:
    hyperopt_mock = mocker.patch('freqtrade.optimize.start_hyperopt', MagicMock())
    hyperopt_mock.__name__ = PropertyMock("start_hyperopt")
    # it's sys.exit(0) at the end of hyperopt
    with pytest.raises(SystemExit):
        main(['hyperopt'])
    assert hyperopt_mock.call_count == 1
    call_args = hyperopt_mock.call_args[0][0]
    assert call_args["config"] == ['config.json']
    assert call_args["verbosity"] == 0
    assert call_args["subparser"] == 'hyperopt'
    assert call_args["func"] is not None
    assert callable(call_args["func"])


def test_main_fatal_exception(mocker, default_conf, caplog) -> None:
    patch_exchange(mocker)
    mocker.patch('freqtrade.freqtradebot.FreqtradeBot.cleanup', MagicMock())
    mocker.patch('freqtrade.worker.Worker._worker', MagicMock(side_effect=Exception))
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch('freqtrade.freqtradebot.RPCManager', MagicMock())
    mocker.patch('freqtrade.freqtradebot.persistence.init', MagicMock())

    args = ['-c', 'config.json.example']

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has('Using config: config.json.example ...', caplog)
    assert log_has('Fatal exception!', caplog)


def test_main_keyboard_interrupt(mocker, default_conf, caplog) -> None:
    patch_exchange(mocker)
    mocker.patch('freqtrade.freqtradebot.FreqtradeBot.cleanup', MagicMock())
    mocker.patch('freqtrade.worker.Worker._worker', MagicMock(side_effect=KeyboardInterrupt))
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch('freqtrade.freqtradebot.RPCManager', MagicMock())
    mocker.patch('freqtrade.freqtradebot.persistence.init', MagicMock())

    args = ['-c', 'config.json.example']

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has('Using config: config.json.example ...', caplog)
    assert log_has('SIGINT received, aborting ...', caplog)


def test_main_operational_exception(mocker, default_conf, caplog) -> None:
    patch_exchange(mocker)
    mocker.patch('freqtrade.freqtradebot.FreqtradeBot.cleanup', MagicMock())
    mocker.patch(
        'freqtrade.worker.Worker._worker',
        MagicMock(side_effect=OperationalException('Oh snap!'))
    )
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch('freqtrade.freqtradebot.RPCManager', MagicMock())
    mocker.patch('freqtrade.freqtradebot.persistence.init', MagicMock())

    args = ['-c', 'config.json.example']

    # Test Main + the KeyboardInterrupt exception
    with pytest.raises(SystemExit):
        main(args)
    assert log_has('Using config: config.json.example ...', caplog)
    assert log_has('Oh snap!', caplog)


def test_main_reload_conf(mocker, default_conf, caplog) -> None:
    patch_exchange(mocker)
    mocker.patch('freqtrade.freqtradebot.FreqtradeBot.cleanup', MagicMock())
    # Simulate Running, reload, running workflow
    worker_mock = MagicMock(side_effect=[State.RUNNING,
                                         State.RELOAD_CONF,
                                         State.RUNNING,
                                         OperationalException("Oh snap!")])
    mocker.patch('freqtrade.worker.Worker._worker', worker_mock)
    patched_configuration_load_config_file(mocker, default_conf)
    reconfigure_mock = mocker.patch('freqtrade.main.Worker._reconfigure', MagicMock())

    mocker.patch('freqtrade.freqtradebot.RPCManager', MagicMock())
    mocker.patch('freqtrade.freqtradebot.persistence.init', MagicMock())

    args = Arguments(['-c', 'config.json.example']).get_parsed_arg()
    worker = Worker(args=args, config=default_conf)
    with pytest.raises(SystemExit):
        main(['-c', 'config.json.example'])

    assert log_has('Using config: config.json.example ...', caplog)
    assert worker_mock.call_count == 4
    assert reconfigure_mock.call_count == 1
    assert isinstance(worker.freqtrade, FreqtradeBot)


def test_reconfigure(mocker, default_conf) -> None:
    patch_exchange(mocker)
    mocker.patch('freqtrade.freqtradebot.FreqtradeBot.cleanup', MagicMock())
    mocker.patch(
        'freqtrade.worker.Worker._worker',
        MagicMock(side_effect=OperationalException('Oh snap!'))
    )
    patched_configuration_load_config_file(mocker, default_conf)
    mocker.patch('freqtrade.freqtradebot.RPCManager', MagicMock())
    mocker.patch('freqtrade.freqtradebot.persistence.init', MagicMock())

    args = Arguments(['-c', 'config.json.example']).get_parsed_arg()
    worker = Worker(args=args, config=default_conf)
    freqtrade = worker.freqtrade

    # Renew mock to return modified data
    conf = deepcopy(default_conf)
    conf['stake_amount'] += 1
    patched_configuration_load_config_file(mocker, conf)

    worker._config = conf
    # reconfigure should return a new instance
    worker._reconfigure()
    freqtrade2 = worker.freqtrade

    # Verify we have a new instance with the new config
    assert freqtrade is not freqtrade2
    assert freqtrade.config['stake_amount'] + 1 == freqtrade2.config['stake_amount']
