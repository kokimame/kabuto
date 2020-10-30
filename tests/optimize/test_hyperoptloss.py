from datetime import datetime
from unittest.mock import MagicMock

import pytest

from freqtrade.exceptions import OperationalException
from freqtrade.optimize.default_hyperopt_loss import ShortTradeDurHyperOptLoss
from freqtrade.resolvers.hyperopt_resolver import HyperOptLossResolver


def test_hyperoptlossresolver_noname(default_conf):
    with pytest.raises(OperationalException,
                       match="No Hyperopt loss set. Please use `--hyperopt-loss` to specify "
                             "the Hyperopt-Loss class to use."):
        HyperOptLossResolver.load_hyperoptloss(default_conf)


def test_hyperoptlossresolver(mocker, default_conf) -> None:

    hl = ShortTradeDurHyperOptLoss
    mocker.patch(
        'freqtrade.resolvers.hyperopt_resolver.HyperOptLossResolver.load_object',
        MagicMock(return_value=hl)
    )
    default_conf.update({'hyperopt_loss': 'SharpeHyperOptLossDaily'})
    x = HyperOptLossResolver.load_hyperoptloss(default_conf)
    assert hasattr(x, "hyperopt_loss_function")


def test_hyperoptlossresolver_wrongname(default_conf) -> None:
    default_conf.update({'hyperopt_loss': "NonExistingLossClass"})

    with pytest.raises(OperationalException, match=r'Impossible to load HyperoptLoss.*'):
        HyperOptLossResolver.load_hyperoptloss(default_conf)


def test_loss_calculation_prefer_correct_trade_count(hyperopt_conf, hyperopt_results) -> None:
    hl = HyperOptLossResolver.load_hyperoptloss(hyperopt_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, 600,
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(hyperopt_results, 600 + 100,
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(hyperopt_results, 600 - 100,
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over > correct
    assert under > correct


def test_loss_calculation_prefer_shorter_trades(hyperopt_conf, hyperopt_results) -> None:
    resultsb = hyperopt_results.copy()
    resultsb.loc[1, 'trade_duration'] = 20

    hl = HyperOptLossResolver.load_hyperoptloss(hyperopt_conf)
    longer = hl.hyperopt_loss_function(hyperopt_results, 100,
                                       datetime(2019, 1, 1), datetime(2019, 5, 1))
    shorter = hl.hyperopt_loss_function(resultsb, 100,
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert shorter < longer


def test_loss_calculation_has_limited_profit(hyperopt_conf, hyperopt_results) -> None:
    results_over = hyperopt_results.copy()
    results_over['profit_percent'] = hyperopt_results['profit_percent'] * 2
    results_under = hyperopt_results.copy()
    results_under['profit_percent'] = hyperopt_results['profit_percent'] / 2

    hl = HyperOptLossResolver.load_hyperoptloss(hyperopt_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, 600,
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(results_over, 600,
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(results_under, 600,
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over < correct
    assert under > correct


def test_sharpe_loss_prefers_higher_profits(default_conf, hyperopt_results) -> None:
    results_over = hyperopt_results.copy()
    results_over['profit_percent'] = hyperopt_results['profit_percent'] * 2
    results_under = hyperopt_results.copy()
    results_under['profit_percent'] = hyperopt_results['profit_percent'] / 2

    default_conf.update({'hyperopt_loss': 'SharpeHyperOptLoss'})
    hl = HyperOptLossResolver.load_hyperoptloss(default_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, len(hyperopt_results),
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(results_over, len(hyperopt_results),
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(results_under, len(hyperopt_results),
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over < correct
    assert under > correct


def test_sharpe_loss_daily_prefers_higher_profits(default_conf, hyperopt_results) -> None:
    results_over = hyperopt_results.copy()
    results_over['profit_percent'] = hyperopt_results['profit_percent'] * 2
    results_under = hyperopt_results.copy()
    results_under['profit_percent'] = hyperopt_results['profit_percent'] / 2

    default_conf.update({'hyperopt_loss': 'SharpeHyperOptLossDaily'})
    hl = HyperOptLossResolver.load_hyperoptloss(default_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, len(hyperopt_results),
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(results_over, len(hyperopt_results),
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(results_under, len(hyperopt_results),
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over < correct
    assert under > correct


def test_sortino_loss_prefers_higher_profits(default_conf, hyperopt_results) -> None:
    results_over = hyperopt_results.copy()
    results_over['profit_percent'] = hyperopt_results['profit_percent'] * 2
    results_under = hyperopt_results.copy()
    results_under['profit_percent'] = hyperopt_results['profit_percent'] / 2

    default_conf.update({'hyperopt_loss': 'SortinoHyperOptLoss'})
    hl = HyperOptLossResolver.load_hyperoptloss(default_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, len(hyperopt_results),
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(results_over, len(hyperopt_results),
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(results_under, len(hyperopt_results),
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over < correct
    assert under > correct


def test_sortino_loss_daily_prefers_higher_profits(default_conf, hyperopt_results) -> None:
    results_over = hyperopt_results.copy()
    results_over['profit_percent'] = hyperopt_results['profit_percent'] * 2
    results_under = hyperopt_results.copy()
    results_under['profit_percent'] = hyperopt_results['profit_percent'] / 2

    default_conf.update({'hyperopt_loss': 'SortinoHyperOptLossDaily'})
    hl = HyperOptLossResolver.load_hyperoptloss(default_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, len(hyperopt_results),
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(results_over, len(hyperopt_results),
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(results_under, len(hyperopt_results),
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over < correct
    assert under > correct


def test_onlyprofit_loss_prefers_higher_profits(default_conf, hyperopt_results) -> None:
    results_over = hyperopt_results.copy()
    results_over['profit_percent'] = hyperopt_results['profit_percent'] * 2
    results_under = hyperopt_results.copy()
    results_under['profit_percent'] = hyperopt_results['profit_percent'] / 2

    default_conf.update({'hyperopt_loss': 'OnlyProfitHyperOptLoss'})
    hl = HyperOptLossResolver.load_hyperoptloss(default_conf)
    correct = hl.hyperopt_loss_function(hyperopt_results, len(hyperopt_results),
                                        datetime(2019, 1, 1), datetime(2019, 5, 1))
    over = hl.hyperopt_loss_function(results_over, len(hyperopt_results),
                                     datetime(2019, 1, 1), datetime(2019, 5, 1))
    under = hl.hyperopt_loss_function(results_under, len(hyperopt_results),
                                      datetime(2019, 1, 1), datetime(2019, 5, 1))
    assert over < correct
    assert under > correct
