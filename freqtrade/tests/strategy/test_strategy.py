# pragma pylint: disable=missing-docstring, protected-access, C0103

import logging
import os

import pytest

from freqtrade.strategy.interface import IStrategy
from freqtrade.strategy.resolver import StrategyResolver


def test_search_strategy():
    default_location = os.path.join(os.path.dirname(
        os.path.realpath(__file__)), '..', '..', 'strategy'
    )
    assert isinstance(
        StrategyResolver._search_strategy(default_location, 'DefaultStrategy'), IStrategy
    )
    assert StrategyResolver._search_strategy(default_location, 'NotFoundStrategy') is None


def test_load_strategy(result):
    resolver = StrategyResolver()
    resolver._load_strategy('TestStrategy')
    assert hasattr(resolver.strategy, 'populate_indicators')
    assert 'adx' in resolver.strategy.populate_indicators(result)


def test_load_strategy_custom_directory(result):
    resolver = StrategyResolver()
    extra_dir = os.path.join('some', 'path')
    with pytest.raises(
            FileNotFoundError,
            match=r".*No such file or directory: '{}'".format(extra_dir)):
        resolver._load_strategy('TestStrategy', extra_dir)

    assert hasattr(resolver.strategy, 'populate_indicators')
    assert 'adx' in resolver.strategy.populate_indicators(result)


def test_load_not_found_strategy():
    strategy = StrategyResolver()
    with pytest.raises(ImportError,
                       match=r'Impossible to load Strategy \'NotFoundStrategy\'.'
                             r' This class does not exist or contains Python code errors'):
        strategy._load_strategy('NotFoundStrategy')


def test_strategy(result):
    resolver = StrategyResolver({'strategy': 'DefaultStrategy'})

    assert hasattr(resolver.strategy, 'minimal_roi')
    assert resolver.strategy.minimal_roi[0] == 0.04

    assert hasattr(resolver.strategy, 'stoploss')
    assert resolver.strategy.stoploss == -0.10

    assert hasattr(resolver.strategy, 'populate_indicators')
    assert 'adx' in resolver.strategy.populate_indicators(result)

    assert hasattr(resolver.strategy, 'populate_buy_trend')
    dataframe = resolver.strategy.populate_buy_trend(resolver.strategy.populate_indicators(result))
    assert 'buy' in dataframe.columns

    assert hasattr(resolver.strategy, 'populate_sell_trend')
    dataframe = resolver.strategy.populate_sell_trend(resolver.strategy.populate_indicators(result))
    assert 'sell' in dataframe.columns


def test_strategy_override_minimal_roi(caplog):
    caplog.set_level(logging.INFO)
    config = {
        'strategy': 'DefaultStrategy',
        'minimal_roi': {
            "0": 0.5
        }
    }
    resolver = StrategyResolver(config)

    assert hasattr(resolver.strategy, 'minimal_roi')
    assert resolver.strategy.minimal_roi[0] == 0.5
    assert ('freqtrade.strategy.resolver',
            logging.INFO,
            'Override strategy \'minimal_roi\' with value in config file.'
            ) in caplog.record_tuples


def test_strategy_override_stoploss(caplog):
    caplog.set_level(logging.INFO)
    config = {
        'strategy': 'DefaultStrategy',
        'stoploss': -0.5
    }
    resolver = StrategyResolver(config)

    assert hasattr(resolver.strategy, 'stoploss')
    assert resolver.strategy.stoploss == -0.5
    assert ('freqtrade.strategy.resolver',
            logging.INFO,
            'Override strategy \'stoploss\' with value in config file: -0.5.'
            ) in caplog.record_tuples


def test_strategy_override_ticker_interval(caplog):
    caplog.set_level(logging.INFO)

    config = {
        'strategy': 'DefaultStrategy',
        'ticker_interval': 60
    }
    resolver = StrategyResolver(config)

    assert hasattr(resolver.strategy, 'ticker_interval')
    assert resolver.strategy.ticker_interval == 60
    assert ('freqtrade.strategy.resolver',
            logging.INFO,
            'Override strategy \'ticker_interval\' with value in config file: 60.'
            ) in caplog.record_tuples
