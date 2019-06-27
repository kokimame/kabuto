#!/usr/bin/env python3
"""
Script to display profits

Mandatory Cli parameters:
-p / --pair: pair to examine

Optional Cli parameters
-c / --config: specify configuration file
-s / --strategy: strategy to use
-d / --datadir: path to pair backtest data
--timerange: specify what timerange of data to use
--export-filename: Specify where the backtest export is located.
"""
import json
import logging
import sys
from argparse import Namespace
from pathlib import Path
from typing import List, Optional

import numpy as np
import plotly.graph_objs as go
from plotly import tools
from plotly.offline import plot

from freqtrade.arguments import Arguments, ARGS_PLOT_PROFIT
from freqtrade.configuration import Configuration
from freqtrade.data import history
from freqtrade.exchange import timeframe_to_seconds
from freqtrade.misc import common_datearray
from freqtrade.resolvers import StrategyResolver
from freqtrade.state import RunMode


logger = logging.getLogger(__name__)


# data:: [ pair,      profit-%,  enter,         exit,        time, duration]
# data:: ["ETH/BTC", 0.0023975, "1515598200", "1515602100", "2018-01-10 07:30:00+00:00", 65]
def make_profit_array(data: List, px: int, min_date: int,
                      interval: str,
                      filter_pairs: Optional[List] = None) -> np.ndarray:
    pg = np.zeros(px)
    filter_pairs = filter_pairs or []
    # Go through the trades
    # and make an total profit
    # array
    for trade in data:
        pair = trade[0]
        if filter_pairs and pair not in filter_pairs:
            continue
        profit = trade[1]
        trade_sell_time = int(trade[3])

        ix = define_index(min_date, trade_sell_time, interval)
        if ix < px:
            logger.debug('[%s]: Add profit %s on %s', pair, profit, trade[4])
            pg[ix] += profit

    # rewrite the pg array to go from
    # total profits at each timeframe
    # to accumulated profits
    pa = 0
    for x in range(0, len(pg)):
        p = pg[x]  # Get current total percent
        pa += p  # Add to the accumulated percent
        pg[x] = pa  # write back to save memory

    return pg


def plot_profit(args: Namespace) -> None:
    """
    Plots the total profit for all pairs.
    Note, the profit calculation isn't realistic.
    But should be somewhat proportional, and therefor useful
    in helping out to find a good algorithm.
    """

    # We need to use the same pairs, same ticker_interval
    # and same timeperiod as used in backtesting
    # to match the tickerdata against the profits-results
    timerange = Arguments.parse_timerange(args.timerange)

    config = Configuration(args, RunMode.OTHER).get_config()

    # Init strategy
    try:
        strategy = StrategyResolver({'strategy': config.get('strategy')}).strategy

    except AttributeError:
        logger.critical(
            'Impossible to load the strategy. Please check the file "user_data/strategies/%s.py"',
            config.get('strategy')
        )
        exit(1)

    # Load the profits results
    try:
        filename = args.exportfilename
        with open(filename) as file:
            data = json.load(file)
    except FileNotFoundError:
        logger.critical(
            'File "backtest-result.json" not found. This script require backtesting '
            'results to run.\nPlease run a backtesting with the parameter --export.')
        exit(1)

    # Take pairs from the cli otherwise switch to the pair in the config file
    if args.pairs:
        filter_pairs = args.pairs
        filter_pairs = filter_pairs.split(',')
    else:
        filter_pairs = config['exchange']['pair_whitelist']

    ticker_interval = strategy.ticker_interval
    pairs = config['exchange']['pair_whitelist']

    if filter_pairs:
        pairs = list(set(pairs) & set(filter_pairs))
        logger.info('Filter, keep pairs %s' % pairs)

    tickers = history.load_data(
        datadir=Path(str(config.get('datadir'))),
        pairs=pairs,
        ticker_interval=ticker_interval,
        refresh_pairs=False,
        timerange=timerange
    )
    dataframes = strategy.tickerdata_to_dataframe(tickers)

    # NOTE: the dataframes are of unequal length,
    # 'dates' is an merged date array of them all.

    dates = common_datearray(dataframes)
    min_date = int(min(dates).timestamp())
    max_date = int(max(dates).timestamp())
    num_iterations = define_index(min_date, max_date, ticker_interval) + 1

    # Make an average close price of all the pairs that was involved.
    # this could be useful to gauge the overall market trend
    # We are essentially saying:
    #  array <- sum dataframes[*]['close'] / num_items dataframes
    #  FIX: there should be some onliner numpy/panda for this
    avgclose = np.zeros(num_iterations)
    num = 0
    for pair, pair_data in dataframes.items():
        close = pair_data['close']
        maxprice = max(close)  # Normalize price to [0,1]
        logger.info('Pair %s has length %s' % (pair, len(close)))
        for x in range(0, len(close)):
            avgclose[x] += close[x] / maxprice
        # avgclose += close
        num += 1
    avgclose /= num

    # make an profits-growth array
    pg = make_profit_array(data, num_iterations, min_date, ticker_interval, filter_pairs)

    #
    # Plot the pairs average close prices, and total profit growth
    #

    avgclose = go.Scattergl(
        x=dates,
        y=avgclose,
        name='Avg close price',
    )

    profit = go.Scattergl(
        x=dates,
        y=pg,
        name='Profit',
    )

    fig = tools.make_subplots(rows=3, cols=1, shared_xaxes=True, row_width=[1, 1, 1])

    fig.append_trace(avgclose, 1, 1)
    fig.append_trace(profit, 2, 1)

    for pair in pairs:
        pg = make_profit_array(data, num_iterations, min_date, ticker_interval, [pair])
        pair_profit = go.Scattergl(
            x=dates,
            y=pg,
            name=pair,
        )
        fig.append_trace(pair_profit, 3, 1)

    plot(fig, filename=str(Path('user_data').joinpath('freqtrade-profit-plot.html')))


def define_index(min_date: int, max_date: int, ticker_interval: str) -> int:
    """
    Return the index of a specific date
    """
    interval_seconds = timeframe_to_seconds(ticker_interval)
    return int((max_date - min_date) / interval_seconds)


def plot_parse_args(args: List[str]) -> Namespace:
    """
    Parse args passed to the script
    :param args: Cli arguments
    :return: args: Array with all arguments
    """
    arguments = Arguments(args, 'Graph profits')
    arguments.build_args(optionlist=ARGS_PLOT_PROFIT)

    return arguments.parse_args()


def main(sysargv: List[str]) -> None:
    """
    This function will initiate the bot and start the trading loop.
    :return: None
    """
    logger.info('Starting Plot Dataframe')
    plot_profit(
        plot_parse_args(sysargv)
    )


if __name__ == '__main__':
    main(sys.argv[1:])
