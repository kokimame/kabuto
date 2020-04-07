"""
Dataprovider
Responsible to provide data to the bot
including ticker and orderbook data, live and historical candle (OHLCV) data
Common Interface for bot and strategy to access data.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

from pandas import DataFrame

from freqtrade.data.history import load_pair_history
from freqtrade.exchange import Exchange
from freqtrade.state import RunMode

logger = logging.getLogger(__name__)


class DataProvider:

    def __init__(self, config: dict, exchange: Exchange) -> None:
        self._config = config
        self._exchange = exchange

    def refresh(self,
                pairlist: List[Tuple[str, str]],
                helping_pairs: List[Tuple[str, str]] = None) -> None:
        """
        Refresh data, called with each cycle
        """
        if helping_pairs:
            self._exchange.refresh_latest_ohlcv(pairlist + helping_pairs)
        else:
            self._exchange.refresh_latest_ohlcv(pairlist)

    @property
    def available_pairs(self) -> List[Tuple[str, str]]:
        """
        Return a list of tuples containing (pair, timeframe) for which data is currently cached.
        Should be whitelist + open trades.
        """
        return list(self._exchange._klines.keys())

    def ohlcv(self, pair: str, timeframe: str = None, copy: bool = True) -> DataFrame:
        """
        Get candle (OHLCV) data for the given pair as DataFrame
        Please use the `available_pairs` method to verify which pairs are currently cached.
        :param pair: pair to get the data for
        :param timeframe: Timeframe to get data for
        :param copy: copy dataframe before returning if True.
                     Use False only for read-only operations (where the dataframe is not modified)
        """
        if self.runmode in (RunMode.DRY_RUN, RunMode.LIVE):
            return self._exchange.klines((pair, timeframe or self._config['ticker_interval']),
                                         copy=copy)
        else:
            return DataFrame()

    def historic_ohlcv(self, pair: str, timeframe: str = None) -> DataFrame:
        """
        Get stored historical candle (OHLCV) data
        :param pair: pair to get the data for
        :param timeframe: timeframe to get data for
        """
        return load_pair_history(pair=pair,
                                 timeframe=timeframe or self._config['ticker_interval'],
                                 datadir=self._config['datadir']
                                 )

    def get_pair_dataframe(self, pair: str, timeframe: str = None) -> DataFrame:
        """
        Return pair candle (OHLCV) data, either live or cached historical -- depending
        on the runmode.
        :param pair: pair to get the data for
        :param timeframe: timeframe to get data for
        :return: Dataframe for this pair
        """
        if self.runmode in (RunMode.DRY_RUN, RunMode.LIVE):
            # Get live OHLCV data.
            data = self.ohlcv(pair=pair, timeframe=timeframe)
        else:
            # Get historical OHLCV data (cached on disk).
            data = self.historic_ohlcv(pair=pair, timeframe=timeframe)
        if len(data) == 0:
            logger.warning(f"No data found for ({pair}, {timeframe}).")
        return data

    def market(self, pair: str) -> Optional[Dict[str, Any]]:
        """
        Return market data for the pair
        :param pair: Pair to get the data for
        :return: Market data dict from ccxt or None if market info is not available for the pair
        """
        return self._exchange.markets.get(pair)

    def ticker(self, pair: str):
        """
        Return last ticker data
        """
        # TODO: Implement me
        pass

    def orderbook(self, pair: str, maximum: int) -> Dict[str, List]:
        """
        fetch latest orderbook data
        :param pair: pair to get the data for
        :param maximum: Maximum number of orderbook entries to query
        :return: dict including bids/asks with a total of `maximum` entries.
        """
        return self._exchange.get_order_book(pair, maximum)

    @property
    def runmode(self) -> RunMode:
        """
        Get runmode of the bot
        can be "live", "dry-run", "backtest", "edgecli", "hyperopt" or "other".
        """
        return RunMode(self._config.get('runmode', RunMode.OTHER))
