# pragma pylint: disable=protected-access, invalid-name

"""
Unit test file for configuration.py
"""
import json
from copy import deepcopy
from unittest.mock import MagicMock
from argparse import Namespace

import pytest
from jsonschema import ValidationError

from freqtrade.arguments import Arguments
from freqtrade.configuration import Configuration
from freqtrade.constants import DEFAULT_DB_PROD_URL, DEFAULT_DB_DRYRUN_URL
from freqtrade.tests.conftest import log_has
from freqtrade import OperationalException


def test_configuration_object() -> None:
    """
    Test the Constants object has the mandatory Constants
    """
    assert hasattr(Configuration, 'load_config')
    assert hasattr(Configuration, '_load_config_file')
    assert hasattr(Configuration, '_validate_config')
    assert hasattr(Configuration, '_load_common_config')
    assert hasattr(Configuration, '_load_backtesting_config')
    assert hasattr(Configuration, '_load_hyperopt_config')
    assert hasattr(Configuration, 'get_config')


def test_load_config_invalid_pair(default_conf) -> None:
    """
    Test the configuration validator with an invalid PAIR format
    """
    conf = deepcopy(default_conf)
    conf['exchange']['pair_whitelist'].append('ETH-BTC')

    with pytest.raises(ValidationError, match=r'.*does not match.*'):
        configuration = Configuration(Namespace())
        configuration._validate_config(conf)


def test_load_config_missing_attributes(default_conf) -> None:
    """
    Test the configuration validator with a missing attribute
    """
    conf = deepcopy(default_conf)
    conf.pop('exchange')

    with pytest.raises(ValidationError, match=r'.*\'exchange\' is a required property.*'):
        configuration = Configuration(Namespace())
        configuration._validate_config(conf)


def test_load_config_incorrect_stake_amount(default_conf) -> None:
    """
    Test the configuration validator with a missing attribute
    """
    conf = deepcopy(default_conf)
    conf['stake_amount'] = 'fake'

    with pytest.raises(ValidationError, match=r'.*\'fake\' does not match \'unlimited\'.*'):
        configuration = Configuration(Namespace())
        configuration._validate_config(conf)


def test_load_config_file(default_conf, mocker, caplog) -> None:
    """
    Test Configuration._load_config_file() method
    """
    file_mock = mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    configuration = Configuration(Namespace())
    validated_conf = configuration._load_config_file('somefile')
    assert file_mock.call_count == 1
    assert validated_conf.items() >= default_conf.items()
    assert 'internals' in validated_conf
    assert log_has('Validating configuration ...', caplog.record_tuples)


def test_load_config_max_open_trades_zero(default_conf, mocker, caplog) -> None:
    """
    Test Configuration._load_config_file() method
    """
    conf = deepcopy(default_conf)
    conf['max_open_trades'] = 0
    file_mock = mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(conf)
    ))

    Configuration(Namespace())._load_config_file('somefile')
    assert file_mock.call_count == 1
    assert log_has('Validating configuration ...', caplog.record_tuples)


def test_load_config_file_exception(mocker) -> None:
    """
    Test Configuration._load_config_file() method
    """
    mocker.patch(
        'freqtrade.configuration.open',
        MagicMock(side_effect=FileNotFoundError('File not found'))
    )
    configuration = Configuration(Namespace())

    with pytest.raises(OperationalException, match=r'.*Config file "somefile" not found!*'):
        configuration._load_config_file('somefile')


def test_load_config(default_conf, mocker) -> None:
    """
    Test Configuration.load_config() without any cli params
    """
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    args = Arguments([], '').get_parsed_arg()
    configuration = Configuration(args)
    validated_conf = configuration.load_config()

    assert validated_conf.get('strategy') == 'DefaultStrategy'
    assert validated_conf.get('strategy_path') is None
    assert 'dynamic_whitelist' not in validated_conf


def test_load_config_with_params(default_conf, mocker) -> None:
    """
    Test Configuration.load_config() with cli params used
    """
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    arglist = [
        '--dynamic-whitelist', '10',
        '--strategy', 'TestStrategy',
        '--strategy-path', '/some/path',
        '--db-url', 'sqlite:///someurl',
    ]
    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()

    assert validated_conf.get('dynamic_whitelist') == 10
    assert validated_conf.get('strategy') == 'TestStrategy'
    assert validated_conf.get('strategy_path') == '/some/path'
    assert validated_conf.get('db_url') == 'sqlite:///someurl'

    conf = default_conf.copy()
    conf["dry_run"] = False
    del conf["db_url"]
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(conf)
    ))

    arglist = [
         '--dynamic-whitelist', '10',
         '--strategy', 'TestStrategy',
         '--strategy-path', '/some/path'
     ]
    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()
    assert validated_conf.get('db_url') == DEFAULT_DB_PROD_URL

    # Test dry=run with ProdURL
    conf = default_conf.copy()
    conf["dry_run"] = True
    conf["db_url"] = DEFAULT_DB_PROD_URL
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(conf)
    ))

    arglist = [
        '--dynamic-whitelist', '10',
        '--strategy', 'TestStrategy',
        '--strategy-path', '/some/path'
    ]
    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    validated_conf = configuration.load_config()
    assert validated_conf.get('db_url') == DEFAULT_DB_DRYRUN_URL


def test_load_custom_strategy(default_conf, mocker) -> None:
    """
    Test Configuration.load_config() without any cli params
    """
    custom_conf = deepcopy(default_conf)
    custom_conf.update({
        'strategy': 'CustomStrategy',
        'strategy_path': '/tmp/strategies',
    })
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(custom_conf)
    ))

    args = Arguments([], '').get_parsed_arg()
    configuration = Configuration(args)
    validated_conf = configuration.load_config()

    assert validated_conf.get('strategy') == 'CustomStrategy'
    assert validated_conf.get('strategy_path') == '/tmp/strategies'


def test_show_info(default_conf, mocker, caplog) -> None:
    """
    Test Configuration.show_info()
    """
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    arglist = [
        '--dynamic-whitelist', '10',
        '--strategy', 'TestStrategy',
        '--db-url', 'sqlite:///tmp/testdb',
    ]
    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    configuration.get_config()

    assert log_has(
        'Parameter --dynamic-whitelist detected. '
        'Using dynamically generated whitelist. '
        '(not applicable with Backtesting and Hyperopt)',
        caplog.record_tuples
    )

    assert log_has('Using DB: "sqlite:///tmp/testdb"', caplog.record_tuples)
    assert log_has('Dry run is enabled', caplog.record_tuples)


def test_setup_configuration_without_arguments(mocker, default_conf, caplog) -> None:
    """
    Test setup_configuration() function
    """
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    arglist = [
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
        'backtesting'
    ]

    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    config = configuration.get_config()
    assert 'max_open_trades' in config
    assert 'stake_currency' in config
    assert 'stake_amount' in config
    assert 'exchange' in config
    assert 'pair_whitelist' in config['exchange']
    assert 'datadir' in config
    assert log_has(
        'Using data folder: {} ...'.format(config['datadir']),
        caplog.record_tuples
    )
    assert 'ticker_interval' in config
    assert not log_has('Parameter -i/--ticker-interval detected ...', caplog.record_tuples)

    assert 'live' not in config
    assert not log_has('Parameter -l/--live detected ...', caplog.record_tuples)

    assert 'realistic_simulation' not in config
    assert not log_has('Parameter --realistic-simulation detected ...', caplog.record_tuples)

    assert 'refresh_pairs' not in config
    assert not log_has('Parameter -r/--refresh-pairs-cached detected ...', caplog.record_tuples)

    assert 'timerange' not in config
    assert 'export' not in config


def test_setup_configuration_with_arguments(mocker, default_conf, caplog) -> None:
    """
    Test setup_configuration() function
    """
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    arglist = [
        '--config', 'config.json',
        '--strategy', 'DefaultStrategy',
        '--datadir', '/foo/bar',
        'backtesting',
        '--ticker-interval', '1m',
        '--live',
        '--realistic-simulation',
        '--refresh-pairs-cached',
        '--timerange', ':100',
        '--export', '/bar/foo'
    ]

    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    config = configuration.get_config()
    assert 'max_open_trades' in config
    assert 'stake_currency' in config
    assert 'stake_amount' in config
    assert 'exchange' in config
    assert 'pair_whitelist' in config['exchange']
    assert 'datadir' in config
    assert log_has(
        'Using data folder: {} ...'.format(config['datadir']),
        caplog.record_tuples
    )
    assert 'ticker_interval' in config
    assert log_has('Parameter -i/--ticker-interval detected ...', caplog.record_tuples)
    assert log_has(
        'Using ticker_interval: 1m ...',
        caplog.record_tuples
    )

    assert 'live' in config
    assert log_has('Parameter -l/--live detected ...', caplog.record_tuples)

    assert 'realistic_simulation'in config
    assert log_has('Parameter --realistic-simulation detected ...', caplog.record_tuples)
    assert log_has('Using max_open_trades: 1 ...', caplog.record_tuples)

    assert 'refresh_pairs'in config
    assert log_has('Parameter -r/--refresh-pairs-cached detected ...', caplog.record_tuples)
    assert 'timerange' in config
    assert log_has(
        'Parameter --timerange detected: {} ...'.format(config['timerange']),
        caplog.record_tuples
    )

    assert 'export' in config
    assert log_has(
        'Parameter --export detected: {} ...'.format(config['export']),
        caplog.record_tuples
    )


def test_hyperopt_with_arguments(mocker, default_conf, caplog) -> None:
    """
    Test setup_configuration() function
    """
    mocker.patch('freqtrade.configuration.open', mocker.mock_open(
        read_data=json.dumps(default_conf)
    ))

    arglist = [
        'hyperopt',
        '--epochs', '10',
        '--spaces', 'all',
    ]

    args = Arguments(arglist, '').get_parsed_arg()

    configuration = Configuration(args)
    config = configuration.get_config()

    assert 'epochs' in config
    assert int(config['epochs']) == 10
    assert log_has('Parameter --epochs detected ...', caplog.record_tuples)
    assert log_has('Will run Hyperopt with for 10 epochs ...', caplog.record_tuples)

    assert 'spaces' in config
    assert config['spaces'] == ['all']
    assert log_has('Parameter -s/--spaces detected: [\'all\']', caplog.record_tuples)


def test_check_exchange(default_conf) -> None:
    """
    Test the configuration validator with a missing attribute
    """
    conf = deepcopy(default_conf)
    configuration = Configuration(Namespace())

    # Test a valid exchange
    conf.get('exchange').update({'name': 'BITTREX'})
    assert configuration.check_exchange(conf)

    # Test a valid exchange
    conf.get('exchange').update({'name': 'binance'})
    assert configuration.check_exchange(conf)

    # Test a invalid exchange
    conf.get('exchange').update({'name': 'unknown_exchange'})
    configuration.config = conf

    with pytest.raises(
        OperationalException,
        match=r'.*Exchange "unknown_exchange" not supported.*'
    ):
        configuration.check_exchange(conf)
