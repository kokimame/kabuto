import pandas as pd

from freqtrade.edge import PairInfo
from freqtrade.optimize.optimize_reports import (
    generate_edge_table, generate_text_table, generate_text_table_sell_reason,
    generate_text_table_strategy)
from freqtrade.strategy.interface import SellType


def test_generate_text_table(default_conf, mocker):

    results = pd.DataFrame(
        {
            'pair': ['ETH/BTC', 'ETH/BTC'],
            'profit_percent': [0.1, 0.2],
            'profit_abs': [0.2, 0.4],
            'trade_duration': [10, 30],
            'profit': [2, 0],
            'loss': [0, 0]
        }
    )

    result_str = (
        '| Pair    |   Buy Count |   Avg Profit % |   Cum Profit % |   Tot Profit BTC '
        '|   Tot Profit % | Avg Duration   |   Wins |   Losses |\n'
        '|:--------|------------:|---------------:|---------------:|-----------------:'
        '|---------------:|:---------------|-------:|---------:|\n'
        '| ETH/BTC |           2 |          15.00 |          30.00 |       0.60000000 '
        '|          15.00 | 0:20:00        |      2 |        0 |\n'
        '| TOTAL   |           2 |          15.00 |          30.00 |       0.60000000 '
        '|          15.00 | 0:20:00        |      2 |        0 |'
    )
    assert generate_text_table(data={'ETH/BTC': {}},
                               stake_currency='BTC', max_open_trades=2,
                               results=results) == result_str


def test_generate_text_table_sell_reason(default_conf, mocker):

    results = pd.DataFrame(
        {
            'pair': ['ETH/BTC', 'ETH/BTC', 'ETH/BTC'],
            'profit_percent': [0.1, 0.2, -0.1],
            'profit_abs': [0.2, 0.4, -0.2],
            'trade_duration': [10, 30, 10],
            'profit': [2, 0, 0],
            'loss': [0, 0, 1],
            'sell_reason': [SellType.ROI, SellType.ROI, SellType.STOP_LOSS]
        }
    )

    result_str = (
        '| Sell Reason   |   Sell Count |   Wins |   Losses |   Avg Profit % |'
        '   Cum Profit % |   Tot Profit BTC |   Tot Profit % |\n'
        '|:--------------|-------------:|-------:|---------:|---------------:|'
        '---------------:|-----------------:|---------------:|\n'
        '| roi           |            2 |      2 |        0 |             15 |'
        '             30 |              0.6 |             15 |\n'
        '| stop_loss     |            1 |      0 |        1 |            -10 |'
        '            -10 |             -0.2 |             -5 |'
    )
    assert generate_text_table_sell_reason(
        data={'ETH/BTC': {}},
        stake_currency='BTC', max_open_trades=2,
        results=results) == result_str


def test_generate_text_table_strategy(default_conf, mocker):
    results = {}
    results['ETH/BTC'] = pd.DataFrame(
        {
            'pair': ['ETH/BTC', 'ETH/BTC', 'ETH/BTC'],
            'profit_percent': [0.1, 0.2, 0.3],
            'profit_abs': [0.2, 0.4, 0.5],
            'trade_duration': [10, 30, 10],
            'profit': [2, 0, 0],
            'loss': [0, 0, 1],
            'sell_reason': [SellType.ROI, SellType.ROI, SellType.STOP_LOSS]
        }
    )
    results['LTC/BTC'] = pd.DataFrame(
        {
            'pair': ['LTC/BTC', 'LTC/BTC', 'LTC/BTC'],
            'profit_percent': [0.4, 0.2, 0.3],
            'profit_abs': [0.4, 0.4, 0.5],
            'trade_duration': [15, 30, 15],
            'profit': [4, 1, 0],
            'loss': [0, 0, 1],
            'sell_reason': [SellType.ROI, SellType.ROI, SellType.STOP_LOSS]
        }
    )

    result_str = (
        '| Strategy   |   buy count |   avg profit % |   cum profit % '
        '|   tot profit BTC |   tot profit % | avg duration   |   profit |   loss |\n'
        '|:-----------|------------:|---------------:|---------------:'
        '|-----------------:|---------------:|:---------------|---------:|-------:|\n'
        '| ETH/BTC    |           3 |          20.00 |          60.00 '
        '|       1.10000000 |          30.00 | 0:17:00        |        3 |      0 |\n'
        '| LTC/BTC    |           3 |          30.00 |          90.00 '
        '|       1.30000000 |          45.00 | 0:20:00        |        3 |      0 |'
    )
    assert generate_text_table_strategy('BTC', 2, all_results=results) == result_str


def test_generate_edge_table(edge_conf, mocker):

    results = {}
    results['ETH/BTC'] = PairInfo(-0.01, 0.60, 2, 1, 3, 10, 60)

    assert generate_edge_table(results).count(':|') == 7
    assert generate_edge_table(results).count('| ETH/BTC |') == 1
    assert generate_edge_table(results).count(
        '|   risk reward ratio |   required risk reward |   expectancy |') == 1
