"""
Unit test file for rpc/rpc_manager.py
"""

import logging
from copy import deepcopy
from unittest.mock import MagicMock

from freqtrade.rpc.rpc_manager import RPCManager
from freqtrade.rpc.telegram import Telegram
from freqtrade.tests.conftest import log_has, get_patched_freqtradebot


def test_rpc_manager_object() -> None:
    """
    Test the Arguments object has the mandatory methods
    :return: None
    """
    assert hasattr(RPCManager, '_init')
    assert hasattr(RPCManager, 'send_msg')
    assert hasattr(RPCManager, 'cleanup')


def test__init__(mocker, default_conf) -> None:
    """
    Test __init__() method
    """
    init_mock = mocker.patch('freqtrade.rpc.rpc_manager.RPCManager._init', MagicMock())
    freqtradebot = get_patched_freqtradebot(mocker, default_conf)

    rpc_manager = RPCManager(freqtradebot)
    assert rpc_manager.freqtrade == freqtradebot
    assert rpc_manager.registered_modules == []
    assert rpc_manager.telegram is None
    assert init_mock.call_count == 1


def test_init_telegram_disabled(mocker, default_conf, caplog) -> None:
    """
    Test _init() method with Telegram disabled
    """
    caplog.set_level(logging.DEBUG)

    conf = deepcopy(default_conf)
    conf['telegram']['enabled'] = False

    freqtradebot = get_patched_freqtradebot(mocker, conf)
    rpc_manager = RPCManager(freqtradebot)

    assert not log_has('Enabling rpc.telegram ...', caplog.record_tuples)
    assert rpc_manager.registered_modules == []
    assert rpc_manager.telegram is None


def test_init_telegram_enabled(mocker, default_conf, caplog) -> None:
    """
    Test _init() method with Telegram enabled
    """
    caplog.set_level(logging.DEBUG)
    mocker.patch('freqtrade.rpc.telegram.Telegram._init', MagicMock())

    freqtradebot = get_patched_freqtradebot(mocker, default_conf)
    rpc_manager = RPCManager(freqtradebot)

    assert log_has('Enabling rpc.telegram ...', caplog.record_tuples)
    len_modules = len(rpc_manager.registered_modules)
    assert len_modules == 1
    assert 'telegram' in rpc_manager.registered_modules
    assert isinstance(rpc_manager.telegram, Telegram)


def test_cleanup_telegram_disabled(mocker, default_conf, caplog) -> None:
    """
    Test cleanup() method with Telegram disabled
    """
    caplog.set_level(logging.DEBUG)
    telegram_mock = mocker.patch('freqtrade.rpc.telegram.Telegram.cleanup', MagicMock())

    conf = deepcopy(default_conf)
    conf['telegram']['enabled'] = False

    freqtradebot = get_patched_freqtradebot(mocker, conf)
    rpc_manager = RPCManager(freqtradebot)
    rpc_manager.cleanup()

    assert not log_has('Cleaning up rpc.telegram ...', caplog.record_tuples)
    assert telegram_mock.call_count == 0


def test_cleanup_telegram_enabled(mocker, default_conf, caplog) -> None:
    """
    Test cleanup() method with Telegram enabled
    """
    caplog.set_level(logging.DEBUG)
    mocker.patch('freqtrade.rpc.telegram.Telegram._init', MagicMock())
    telegram_mock = mocker.patch('freqtrade.rpc.telegram.Telegram.cleanup', MagicMock())

    freqtradebot = get_patched_freqtradebot(mocker, default_conf)
    rpc_manager = RPCManager(freqtradebot)

    # Check we have Telegram as a registered modules
    assert 'telegram' in rpc_manager.registered_modules

    rpc_manager.cleanup()
    assert log_has('Cleaning up rpc.telegram ...', caplog.record_tuples)
    assert 'telegram' not in rpc_manager.registered_modules
    assert telegram_mock.call_count == 1


def test_send_msg_telegram_disabled(mocker, default_conf, caplog) -> None:
    """
    Test send_msg() method with Telegram disabled
    """
    telegram_mock = mocker.patch('freqtrade.rpc.telegram.Telegram.send_msg', MagicMock())

    conf = deepcopy(default_conf)
    conf['telegram']['enabled'] = False

    freqtradebot = get_patched_freqtradebot(mocker, conf)
    rpc_manager = RPCManager(freqtradebot)
    rpc_manager.send_msg('test')

    assert log_has('test', caplog.record_tuples)
    assert telegram_mock.call_count == 0


def test_send_msg_telegram_enabled(mocker, default_conf, caplog) -> None:
    """
    Test send_msg() method with Telegram disabled
    """
    telegram_mock = mocker.patch('freqtrade.rpc.telegram.Telegram.send_msg', MagicMock())
    mocker.patch('freqtrade.rpc.telegram.Telegram._init', MagicMock())

    freqtradebot = get_patched_freqtradebot(mocker, default_conf)
    rpc_manager = RPCManager(freqtradebot)
    rpc_manager.send_msg('test')

    assert log_has('test', caplog.record_tuples)
    assert telegram_mock.call_count == 1
