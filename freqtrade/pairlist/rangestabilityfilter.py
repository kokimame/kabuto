"""
Rate of change pairlist filter
"""
import logging
from typing import Any, Dict

import arrow
from cachetools.ttl import TTLCache

from freqtrade.exceptions import OperationalException
from freqtrade.misc import plural
from freqtrade.pairlist.IPairList import IPairList


logger = logging.getLogger(__name__)


class RangeStabilityFilter(IPairList):

    def __init__(self, exchange, pairlistmanager,
                 config: Dict[str, Any], pairlistconfig: Dict[str, Any],
                 pairlist_pos: int) -> None:
        super().__init__(exchange, pairlistmanager, config, pairlistconfig, pairlist_pos)

        self._days = pairlistconfig.get('lookback_days', 10)
        self._min_rate_of_change = pairlistconfig.get('min_rate_of_change', 0.01)
        self._refresh_period = pairlistconfig.get('refresh_period', 1440)

        self._pair_cache: TTLCache = TTLCache(maxsize=100, ttl=self._refresh_period)

        if self._days < 1:
            raise OperationalException("RangeStabilityFilter requires lookback_days to be >= 1")
        if self._days > exchange.ohlcv_candle_limit:
            raise OperationalException("RangeStabilityFilter requires lookback_days to not "
                                       "exceed exchange max request size "
                                       f"({exchange.ohlcv_candle_limit})")

    @property
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requires tickers, an empty List is passed
        as tickers argument to filter_pairlist
        """
        return True

    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        """
        return (f"{self.name} - Filtering pairs with rate of change below "
                f"{self._min_rate_of_change} over the last {plural(self._days, 'day')}.")

    def _validate_pair(self, ticker: Dict) -> bool:
        """
        Validate trading range
        :param ticker: ticker dict as returned from ccxt.load_markets()
        :return: True if the pair can stay, False if it should be removed
        """
        pair = ticker['symbol']
        # Check symbol in cache
        if pair in self._pair_cache:
            return self._pair_cache[pair]

        since_ms = int(arrow.utcnow()
                       .floor('day')
                       .shift(days=-self._days)
                       .float_timestamp) * 1000

        daily_candles = self._exchange.get_historic_ohlcv_as_df(pair=pair,
                                                                timeframe='1d',
                                                                since_ms=since_ms)
        result = False
        if daily_candles is not None and not daily_candles.empty:
            highest_high = daily_candles['high'].max()
            lowest_low = daily_candles['low'].min()
            pct_change = ((highest_high - lowest_low) / lowest_low) if lowest_low > 0 else 0
            if pct_change >= self._min_rate_of_change:
                result = True
            else:
                self.log_on_refresh(logger.info,
                                    f"Removed {pair} from whitelist, "
                                    f"because rate of change over {plural(self._days, 'day')} is "
                                    f"{pct_change:.3f}, which is below the "
                                    f"threshold of {self._min_rate_of_change}.")
                result = False
            self._pair_cache[pair] = result

        return result
