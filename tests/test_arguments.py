# pragma pylint: disable=missing-docstring, C0103
import argparse
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from freqtrade.configuration import Arguments
from freqtrade.configuration.cli_options import check_int_positive


# Parse common command-line-arguments. Used for all tools
def test_parse_args_none() -> None:
    arguments = Arguments([])
    assert isinstance(arguments, Arguments)
    x = arguments.get_parsed_arg()
    assert isinstance(x, dict)
    assert isinstance(arguments.parser, argparse.ArgumentParser)


def test_parse_args_defaults() -> None:
    args = Arguments([]).get_parsed_arg()
    assert args["config"] == ['config.json']
    assert args["strategy_path"] is None
    assert args["datadir"] is None
    assert args["verbosity"] == 0


def test_parse_args_config() -> None:
    args = Arguments(['-c', '/dev/null']).get_parsed_arg()
    assert args["config"] == ['/dev/null']

    args = Arguments(['--config', '/dev/null']).get_parsed_arg()
    assert args["config"] == ['/dev/null']

    args = Arguments(['--config', '/dev/null',
                      '--config', '/dev/zero'],).get_parsed_arg()
    assert args["config"] == ['/dev/null', '/dev/zero']


def test_parse_args_db_url() -> None:
    args = Arguments(['--db-url', 'sqlite:///test.sqlite']).get_parsed_arg()
    assert args["db_url"] == 'sqlite:///test.sqlite'


def test_parse_args_verbose() -> None:
    args = Arguments(['-v']).get_parsed_arg()
    assert args["verbosity"] == 1

    args = Arguments(['--verbose']).get_parsed_arg()
    assert args["verbosity"] == 1


def test_common_scripts_options() -> None:
    args = Arguments(['download-data', '-p', 'ETH/BTC', 'XRP/BTC']).get_parsed_arg()

    assert args["pairs"] == ['ETH/BTC', 'XRP/BTC']
    assert "func" in args


def test_parse_args_version() -> None:
    with pytest.raises(SystemExit, match=r'0'):
        Arguments(['--version']).get_parsed_arg()


def test_parse_args_invalid() -> None:
    with pytest.raises(SystemExit, match=r'2'):
        Arguments(['-c']).get_parsed_arg()


def test_parse_args_strategy() -> None:
    args = Arguments(['--strategy', 'SomeStrategy']).get_parsed_arg()
    assert args["strategy"] == 'SomeStrategy'


def test_parse_args_strategy_invalid() -> None:
    with pytest.raises(SystemExit, match=r'2'):
        Arguments(['--strategy']).get_parsed_arg()


def test_parse_args_strategy_path() -> None:
    args = Arguments(['--strategy-path', '/some/path']).get_parsed_arg()
    assert args["strategy_path"] == '/some/path'


def test_parse_args_strategy_path_invalid() -> None:
    with pytest.raises(SystemExit, match=r'2'):
        Arguments(['--strategy-path']).get_parsed_arg()


def test_parse_args_backtesting_invalid() -> None:
    with pytest.raises(SystemExit, match=r'2'):
        Arguments(['backtesting --ticker-interval']).get_parsed_arg()

    with pytest.raises(SystemExit, match=r'2'):
        Arguments(['backtesting --ticker-interval', 'abc']).get_parsed_arg()


def test_parse_args_backtesting_custom() -> None:
    args = [
        '-c', 'test_conf.json',
        'backtesting',
        '--ticker-interval', '1m',
        '--strategy-list',
        'DefaultStrategy',
        'SampleStrategy'
        ]
    call_args = Arguments(args).get_parsed_arg()
    assert call_args["config"] == ['test_conf.json']
    assert call_args["verbosity"] == 0
    assert call_args["subparser"] == 'backtesting'
    assert call_args["func"] is not None
    assert call_args["ticker_interval"] == '1m'
    assert type(call_args["strategy_list"]) is list
    assert len(call_args["strategy_list"]) == 2


def test_parse_args_hyperopt_custom() -> None:
    args = [
        '-c', 'test_conf.json',
        'hyperopt',
        '--epochs', '20',
        '--spaces', 'buy'
    ]
    call_args = Arguments(args).get_parsed_arg()
    assert call_args["config"] == ['test_conf.json']
    assert call_args["epochs"] == 20
    assert call_args["verbosity"] == 0
    assert call_args["subparser"] == 'hyperopt'
    assert call_args["spaces"] == ['buy']
    assert call_args["func"] is not None
    assert callable(call_args["func"])


def test_download_data_options() -> None:
    args = [
        '--datadir', 'datadir/directory',
        'download-data',
        '--pairs-file', 'file_with_pairs',
        '--days', '30',
        '--exchange', 'binance'
    ]
    pargs = Arguments(args).get_parsed_arg()

    assert pargs["pairs_file"] == 'file_with_pairs'
    assert pargs["datadir"] == 'datadir/directory'
    assert pargs["days"] == 30
    assert pargs["exchange"] == 'binance'


def test_plot_dataframe_options() -> None:
    args = [
        '-c', 'config.json.example',
        'plot-dataframe',
        '--indicators1', 'sma10', 'sma100',
        '--indicators2', 'macd', 'fastd', 'fastk',
        '--plot-limit', '30',
        '-p', 'UNITTEST/BTC',
    ]
    pargs = Arguments(args).get_parsed_arg()

    assert pargs["indicators1"] == ["sma10", "sma100"]
    assert pargs["indicators2"] == ["macd", "fastd", "fastk"]
    assert pargs["plot_limit"] == 30
    assert pargs["pairs"] == ["UNITTEST/BTC"]


def test_plot_profit_options() -> None:
    args = [
        'plot-profit',
        '-p', 'UNITTEST/BTC',
        '--trade-source', 'DB',
        "--db-url", "sqlite:///whatever.sqlite",
    ]
    pargs = Arguments(args).get_parsed_arg()

    assert pargs["trade_source"] == "DB"
    assert pargs["pairs"] == ["UNITTEST/BTC"]
    assert pargs["db_url"] == "sqlite:///whatever.sqlite"


def test_config_notallowed(mocker) -> None:
    mocker.patch.object(Path, "is_file", MagicMock(return_value=False))
    args = [
        'create-userdir',
    ]
    pargs = Arguments(args).get_parsed_arg()

    assert pargs["config"] is None

    # When file exists:
    mocker.patch.object(Path, "is_file", MagicMock(return_value=True))
    args = [
        'create-userdir',
    ]
    pargs = Arguments(args).get_parsed_arg()
    # config is not added even if it exists, since create-userdir is in the notallowed list
    assert pargs["config"] is None


def test_config_notrequired(mocker) -> None:
    mocker.patch.object(Path, "is_file", MagicMock(return_value=False))
    args = [
        'download-data',
    ]
    pargs = Arguments(args).get_parsed_arg()

    assert pargs["config"] is None

    # When file exists:
    mocker.patch.object(Path, "is_file", MagicMock(return_value=True))
    args = [
        'download-data',
    ]
    pargs = Arguments(args).get_parsed_arg()
    # config is added if it exists
    assert pargs["config"] == ['config.json']


def test_check_int_positive() -> None:
    assert check_int_positive("3") == 3
    assert check_int_positive("1") == 1
    assert check_int_positive("100") == 100

    with pytest.raises(argparse.ArgumentTypeError):
        check_int_positive("-2")

    with pytest.raises(argparse.ArgumentTypeError):
        check_int_positive("0")

    with pytest.raises(argparse.ArgumentTypeError):
        check_int_positive("3.5")

    with pytest.raises(argparse.ArgumentTypeError):
        check_int_positive("DeadBeef")
