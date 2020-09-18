# pragma pylint: disable=missing-docstring, W0212, too-many-arguments

"""
This module contains the backtesting logic
"""
import logging
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from pandas import DataFrame

from freqtrade.configuration import TimeRange, remove_credentials, validate_config_consistency
from freqtrade.constants import DATETIME_PRINT_FORMAT
from freqtrade.data import history
from freqtrade.data.converter import trim_dataframe
from freqtrade.data.dataprovider import DataProvider
from freqtrade.exceptions import OperationalException
from freqtrade.exchange import timeframe_to_minutes, timeframe_to_seconds
from freqtrade.mixins import LoggingMixin
from freqtrade.optimize.optimize_reports import (generate_backtest_stats, show_backtest_results,
                                                 store_backtest_stats)
from freqtrade.persistence import PairLocks, Trade
from freqtrade.plugins.pairlistmanager import PairListManager
from freqtrade.plugins.protectionmanager import ProtectionManager
from freqtrade.resolvers import ExchangeResolver, StrategyResolver
from freqtrade.strategy.interface import IStrategy, SellCheckTuple, SellType


logger = logging.getLogger(__name__)

# Indexes for backtest tuples
DATE_IDX = 0
BUY_IDX = 1
OPEN_IDX = 2
CLOSE_IDX = 3
SELL_IDX = 4
LOW_IDX = 5
HIGH_IDX = 6


class BacktestResult(NamedTuple):
    """
    NamedTuple Defining BacktestResults inputs.
    """
    pair: str
    profit_percent: float
    profit_abs: float
    open_date: datetime
    open_rate: float
    open_fee: float
    close_date: datetime
    close_rate: float
    close_fee: float
    amount: float
    trade_duration: float
    open_at_end: bool
    sell_reason: SellType


class Backtesting:
    """
    Backtesting class, this class contains all the logic to run a backtest

    To run a backtest:
    backtesting = Backtesting(config)
    backtesting.start()
    """

    def __init__(self, config: Dict[str, Any]) -> None:

        LoggingMixin.show_output = False
        self.config = config

        # Reset keys for backtesting
        remove_credentials(self.config)
        self.strategylist: List[IStrategy] = []
        self.all_results: Dict[str, Dict] = {}

        self.exchange = ExchangeResolver.load_exchange(self.config['exchange']['name'], self.config)

        dataprovider = DataProvider(self.config, self.exchange)
        IStrategy.dp = dataprovider

        if self.config.get('strategy_list', None):
            for strat in list(self.config['strategy_list']):
                stratconf = deepcopy(self.config)
                stratconf['strategy'] = strat
                self.strategylist.append(StrategyResolver.load_strategy(stratconf))
                validate_config_consistency(stratconf)

        else:
            # No strategy list specified, only one strategy
            self.strategylist.append(StrategyResolver.load_strategy(self.config))
            validate_config_consistency(self.config)

        if "timeframe" not in self.config:
            raise OperationalException("Timeframe (ticker interval) needs to be set in either "
                                       "configuration or as cli argument `--timeframe 5m`")
        self.timeframe = str(self.config.get('timeframe'))
        self.timeframe_min = timeframe_to_minutes(self.timeframe)

        self.pairlists = PairListManager(self.exchange, self.config)
        if 'VolumePairList' in self.pairlists.name_list:
            raise OperationalException("VolumePairList not allowed for backtesting.")
        if 'PerformanceFilter' in self.pairlists.name_list:
            raise OperationalException("PerformanceFilter not allowed for backtesting.")

        if len(self.strategylist) > 1 and 'PrecisionFilter' in self.pairlists.name_list:
            raise OperationalException(
                "PrecisionFilter not allowed for backtesting multiple strategies."
            )

        dataprovider.add_pairlisthandler(self.pairlists)
        self.pairlists.refresh_pairlist()

        if len(self.pairlists.whitelist) == 0:
            raise OperationalException("No pair in whitelist.")

        if config.get('fee', None) is not None:
            self.fee = config['fee']
        else:
            self.fee = self.exchange.get_fee(symbol=self.pairlists.whitelist[0])

        Trade.use_db = False
        Trade.reset_trades()
        PairLocks.timeframe = self.config['timeframe']
        PairLocks.use_db = False
        PairLocks.reset_locks()
        if self.config.get('enable_protections', False):
            self.protections = ProtectionManager(self.config)

        # Get maximum required startup period
        self.required_startup = max([strat.startup_candle_count for strat in self.strategylist])
        # Load one (first) strategy
        self._set_strategy(self.strategylist[0])

    def __del__(self):
        LoggingMixin.show_output = True
        PairLocks.use_db = True
        Trade.use_db = True

    def _set_strategy(self, strategy):
        """
        Load strategy into backtesting
        """
        self.strategy: IStrategy = strategy
        # Set stoploss_on_exchange to false for backtesting,
        # since a "perfect" stoploss-sell is assumed anyway
        # And the regular "stoploss" function would not apply to that case
        self.strategy.order_types['stoploss_on_exchange'] = False

    def load_bt_data(self) -> Tuple[Dict[str, DataFrame], TimeRange]:
        timerange = TimeRange.parse_timerange(None if self.config.get(
            'timerange') is None else str(self.config.get('timerange')))

        data = history.load_data(
            datadir=self.config['datadir'],
            pairs=self.pairlists.whitelist,
            timeframe=self.timeframe,
            timerange=timerange,
            startup_candles=self.required_startup,
            fail_without_data=True,
            data_format=self.config.get('dataformat_ohlcv', 'json'),
        )

        min_date, max_date = history.get_timerange(data)

        logger.info(f'Loading data from {min_date.strftime(DATETIME_PRINT_FORMAT)} '
                    f'up to {max_date.strftime(DATETIME_PRINT_FORMAT)} '
                    f'({(max_date - min_date).days} days)..')

        # Adjust startts forward if not enough data is available
        timerange.adjust_start_if_necessary(timeframe_to_seconds(self.timeframe),
                                            self.required_startup, min_date)

        return data, timerange

    def prepare_backtest(self, enable_protections):
        """
        Backtesting setup method - called once for every call to "backtest()".
        """
        PairLocks.use_db = False
        PairLocks.timeframe = self.config['timeframe']
        Trade.use_db = False
        if enable_protections:
            # Reset persisted data - used for protections only
            PairLocks.reset_locks()
            Trade.reset_trades()

    def _get_ohlcv_as_lists(self, processed: Dict[str, DataFrame]) -> Dict[str, Tuple]:
        """
        Helper function to convert a processed dataframes into lists for performance reasons.

        Used by backtest() - so keep this optimized for performance.
        """
        # Every change to this headers list must evaluate further usages of the resulting tuple
        # and eventually change the constants for indexes at the top
        headers = ['date', 'buy', 'open', 'close', 'sell', 'low', 'high']
        data: Dict = {}
        # Create dict with data
        for pair, pair_data in processed.items():
            pair_data.loc[:, 'buy'] = 0  # cleanup from previous run
            pair_data.loc[:, 'sell'] = 0  # cleanup from previous run

            df_analyzed = self.strategy.advise_sell(
                self.strategy.advise_buy(pair_data, {'pair': pair}), {'pair': pair})[headers].copy()

            # To avoid using data from future, we use buy/sell signals shifted
            # from the previous candle
            df_analyzed.loc[:, 'buy'] = df_analyzed.loc[:, 'buy'].shift(1)
            df_analyzed.loc[:, 'sell'] = df_analyzed.loc[:, 'sell'].shift(1)

            df_analyzed.drop(df_analyzed.head(1).index, inplace=True)

            # Convert from Pandas to list for performance reasons
            # (Looping Pandas is slow.)
            data[pair] = [x for x in df_analyzed.itertuples(index=False, name=None)]
        return data

    def _get_close_rate(self, sell_row: Tuple, trade: Trade, sell: SellCheckTuple,
                        trade_dur: int) -> float:
        """
        Get close rate for backtesting result
        """
        # Special handling if high or low hit STOP_LOSS or ROI
        if sell.sell_type in (SellType.STOP_LOSS, SellType.TRAILING_STOP_LOSS):
            # Set close_rate to stoploss
            return trade.stop_loss
        elif sell.sell_type == (SellType.ROI):
            roi_entry, roi = self.strategy.min_roi_reached_entry(trade_dur)
            if roi is not None and roi_entry is not None:
                if roi == -1 and roi_entry % self.timeframe_min == 0:
                    # When forceselling with ROI=-1, the roi time will always be equal to trade_dur.
                    # If that entry is a multiple of the timeframe (so on candle open)
                    # - we'll use open instead of close
                    return sell_row[OPEN_IDX]

                # - (Expected abs profit + open_rate + open_fee) / (fee_close -1)
                close_rate = - (trade.open_rate * roi + trade.open_rate *
                                (1 + trade.fee_open)) / (trade.fee_close - 1)

                if (trade_dur > 0 and trade_dur == roi_entry
                        and roi_entry % self.timeframe_min == 0
                        and sell_row[OPEN_IDX] > close_rate):
                    # new ROI entry came into effect.
                    # use Open rate if open_rate > calculated sell rate
                    return sell_row[OPEN_IDX]

                # Use the maximum between close_rate and low as we
                # cannot sell outside of a candle.
                # Applies when a new ROI setting comes in place and the whole candle is above that.
                return max(close_rate, sell_row[LOW_IDX])

            else:
                # This should not be reached...
                return sell_row[OPEN_IDX]
        else:
            return sell_row[OPEN_IDX]

    def _get_sell_trade_entry(self, trade: Trade, sell_row: Tuple) -> Optional[BacktestResult]:

        sell = self.strategy.should_sell(trade, sell_row[OPEN_IDX], sell_row[DATE_IDX],
                                         sell_row[BUY_IDX], sell_row[SELL_IDX],
                                         low=sell_row[LOW_IDX], high=sell_row[HIGH_IDX])
        if sell.sell_flag:
            trade_dur = int((sell_row[DATE_IDX] - trade.open_date).total_seconds() // 60)
            closerate = self._get_close_rate(sell_row, trade, sell, trade_dur)

            trade.close_date = sell_row[DATE_IDX]
            trade.sell_reason = sell.sell_type
            trade.close(closerate, show_msg=False)

            return BacktestResult(pair=trade.pair,
                                  profit_percent=trade.calc_profit_ratio(rate=closerate),
                                  profit_abs=trade.calc_profit(rate=closerate),
                                  open_date=trade.open_date,
                                  open_rate=trade.open_rate,
                                  open_fee=self.fee,
                                  close_date=sell_row[DATE_IDX],
                                  close_rate=closerate,
                                  close_fee=self.fee,
                                  amount=trade.amount,
                                  trade_duration=trade_dur,
                                  open_at_end=False,
                                  sell_reason=sell.sell_type
                                  )
        return None

    def handle_left_open(self, open_trades: Dict[str, List[Trade]],
                         data: Dict[str, List[Tuple]]) -> List[BacktestResult]:
        """
        Handling of left open trades at the end of backtesting
        """
        trades = []
        for pair in open_trades.keys():
            if len(open_trades[pair]) > 0:
                for trade in open_trades[pair]:
                    sell_row = data[pair][-1]

                    trade_entry = BacktestResult(pair=trade.pair,
                                                 profit_percent=trade.calc_profit_ratio(
                                                     rate=sell_row[OPEN_IDX]),
                                                 profit_abs=trade.calc_profit(sell_row[OPEN_IDX]),
                                                 open_date=trade.open_date,
                                                 open_rate=trade.open_rate,
                                                 open_fee=self.fee,
                                                 close_date=sell_row[DATE_IDX],
                                                 close_rate=sell_row[OPEN_IDX],
                                                 close_fee=self.fee,
                                                 amount=trade.amount,
                                                 trade_duration=int((
                                                     sell_row[DATE_IDX] - trade.open_date
                                                 ).total_seconds() // 60),
                                                 open_at_end=True,
                                                 sell_reason=SellType.FORCE_SELL
                                                 )
                    trades.append(trade_entry)
        return trades

    def backtest(self, processed: Dict, stake_amount: float,
                 start_date: datetime, end_date: datetime,
                 max_open_trades: int = 0, position_stacking: bool = False,
                 enable_protections: bool = False) -> DataFrame:
        """
        Implement backtesting functionality

        NOTE: This method is used by Hyperopt at each iteration. Please keep it optimized.
        Of course try to not have ugly code. By some accessor are sometime slower than functions.
        Avoid extensive logging in this method and functions it calls.

        :param processed: a processed dictionary with format {pair, data}
        :param stake_amount: amount to use for each trade
        :param start_date: backtesting timerange start datetime
        :param end_date: backtesting timerange end datetime
        :param max_open_trades: maximum number of concurrent trades, <= 0 means unlimited
        :param position_stacking: do we allow position stacking?
        :param enable_protections: Should protections be enabled?
        :return: DataFrame with trades (results of backtesting)
        """
        logger.debug(f"Run backtest, stake_amount: {stake_amount}, "
                     f"start_date: {start_date}, end_date: {end_date}, "
                     f"max_open_trades: {max_open_trades}, position_stacking: {position_stacking}"
                     )
        trades = []
        self.prepare_backtest(enable_protections)

        # Use dict of lists with data for performance
        # (looping lists is a lot faster than pandas DataFrames)
        data: Dict = self._get_ohlcv_as_lists(processed)

        # Indexes per pair, so some pairs are allowed to have a missing start.
        indexes: Dict = {}
        tmp = start_date + timedelta(minutes=self.timeframe_min)

        open_trades: Dict[str, List] = defaultdict(list)
        open_trade_count = 0

        # Loop timerange and get candle for each pair at that point in time
        while tmp <= end_date:
            open_trade_count_start = open_trade_count

            for i, pair in enumerate(data):
                if pair not in indexes:
                    indexes[pair] = 0

                try:
                    row = data[pair][indexes[pair]]
                except IndexError:
                    # missing Data for one pair at the end.
                    # Warnings for this are shown during data loading
                    continue

                # Waits until the time-counter reaches the start of the data for this pair.
                if row[DATE_IDX] > tmp:
                    continue
                indexes[pair] += 1

                # without positionstacking, we can only have one open trade per pair.
                # max_open_trades must be respected
                # don't open on the last row
                if ((position_stacking or len(open_trades[pair]) == 0)
                        and (max_open_trades <= 0 or open_trade_count_start < max_open_trades)
                        and tmp != end_date
                        and row[BUY_IDX] == 1 and row[SELL_IDX] != 1
                        and not PairLocks.is_pair_locked(pair, row[DATE_IDX])):
                    # Enter trade
                    trade = Trade(
                        pair=pair,
                        open_rate=row[OPEN_IDX],
                        open_date=row[DATE_IDX],
                        stake_amount=stake_amount,
                        amount=round(stake_amount / row[OPEN_IDX], 8),
                        fee_open=self.fee,
                        fee_close=self.fee,
                        is_open=True,
                    )
                    # TODO: hacky workaround to avoid opening > max_open_trades
                    # This emulates previous behaviour - not sure if this is correct
                    # Prevents buying if the trade-slot was freed in this candle
                    open_trade_count_start += 1
                    open_trade_count += 1
                    # logger.debug(f"{pair} - Backtesting emulates creation of new trade: {trade}.")
                    open_trades[pair].append(trade)
                    Trade.trades.append(trade)

                for trade in open_trades[pair]:
                    # since indexes has been incremented before, we need to go one step back to
                    # also check the buying candle for sell conditions.
                    trade_entry = self._get_sell_trade_entry(trade, row)
                    # Sell occured
                    if trade_entry:
                        # logger.debug(f"{pair} - Backtesting sell {trade}")
                        open_trade_count -= 1
                        open_trades[pair].remove(trade)
                        trades.append(trade_entry)
                        if enable_protections:
                            self.protections.stop_per_pair(pair, row[DATE_IDX])
                            self.protections.global_stop(tmp)

            # Move time one configured time_interval ahead.
            tmp += timedelta(minutes=self.timeframe_min)

        trades += self.handle_left_open(open_trades, data=data)

        return DataFrame.from_records(trades, columns=BacktestResult._fields)

    def backtest_one_strategy(self, strat: IStrategy, data: Dict[str, Any], timerange: TimeRange):
        logger.info("Running backtesting for Strategy %s", strat.get_strategy_name())
        self._set_strategy(strat)

        # Use max_open_trades in backtesting, except --disable-max-market-positions is set
        if self.config.get('use_max_market_positions', True):
            # Must come from strategy config, as the strategy may modify this setting.
            max_open_trades = self.strategy.config['max_open_trades']
        else:
            logger.info(
                'Ignoring max_open_trades (--disable-max-market-positions was used) ...')
            max_open_trades = 0

        # need to reprocess data every time to populate signals
        preprocessed = self.strategy.ohlcvdata_to_dataframe(data)

        # Trim startup period from analyzed dataframe
        for pair, df in preprocessed.items():
            preprocessed[pair] = trim_dataframe(df, timerange)
        min_date, max_date = history.get_timerange(preprocessed)

        logger.info(f'Backtesting with data from {min_date.strftime(DATETIME_PRINT_FORMAT)} '
                    f'up to {max_date.strftime(DATETIME_PRINT_FORMAT)} '
                    f'({(max_date - min_date).days} days)..')
        # Execute backtest and store results
        results = self.backtest(
            processed=preprocessed,
            stake_amount=self.config['stake_amount'],
            start_date=min_date.datetime,
            end_date=max_date.datetime,
            max_open_trades=max_open_trades,
            position_stacking=self.config.get('position_stacking', False),
            enable_protections=self.config.get('enable_protections', False),
        )
        self.all_results[self.strategy.get_strategy_name()] = {
            'results': results,
            'config': self.strategy.config,
            'locks': PairLocks.locks,
        }
        return min_date, max_date

    def start(self) -> None:
        """
        Run backtesting end-to-end
        :return: None
        """
        data: Dict[str, Any] = {}

        data, timerange = self.load_bt_data()

        min_date = None
        max_date = None
        for strat in self.strategylist:
            min_date, max_date = self.backtest_one_strategy(strat, data, timerange)

        stats = generate_backtest_stats(data, self.all_results,
                                        min_date=min_date, max_date=max_date)

        if self.config.get('export', False):
            store_backtest_stats(self.config['exportfilename'], stats)

        # Show backtest results
        show_backtest_results(self.config, stats)
