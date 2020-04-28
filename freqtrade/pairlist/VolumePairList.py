"""
Volume PairList provider

Provides lists as configured in config.json

 """
import logging
from datetime import datetime
from typing import Any, Dict, List

from freqtrade.exceptions import OperationalException
from freqtrade.pairlist.IPairList import IPairList

logger = logging.getLogger(__name__)

SORT_VALUES = ['askVolume', 'bidVolume', 'quoteVolume']


class VolumePairList(IPairList):

    def __init__(self, exchange, pairlistmanager, config: Dict[str, Any], pairlistconfig: dict,
                 pairlist_pos: int) -> None:
        super().__init__(exchange, pairlistmanager, config, pairlistconfig, pairlist_pos)

        if 'number_assets' not in self._pairlistconfig:
            raise OperationalException(
                f'`number_assets` not specified. Please check your configuration '
                'for "pairlist.config.number_assets"')
        self._number_pairs = self._pairlistconfig['number_assets']
        self._sort_key = self._pairlistconfig.get('sort_key', 'quoteVolume')
        self._min_value = self._pairlistconfig.get('min_value', 0)
        self.refresh_period = self._pairlistconfig.get('refresh_period', 1800)

        if not self._exchange.exchange_has('fetchTickers'):
            raise OperationalException(
                'Exchange does not support dynamic whitelist.'
                'Please edit your config and restart the bot'
            )
        if not self._validate_keys(self._sort_key):
            raise OperationalException(
                f'key {self._sort_key} not in {SORT_VALUES}')

    @property
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requries tickers, an empty List is passed
        as tickers argument to filter_pairlist
        """
        return True

    def _validate_keys(self, key):
        return key in SORT_VALUES

    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        """
        return f"{self.name} - top {self._pairlistconfig['number_assets']} volume pairs."

    def filter_pairlist(self, pairlist: List[str], tickers: Dict) -> List[str]:
        """
        Filters and sorts pairlist and returns the whitelist again.
        Called on each bot iteration - please use internal caching if necessary
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers()). May be cached.
        :return: new whitelist
        """
        # Generate dynamic whitelist
        # Must always run if this pairlist is not the first in the list.
        if (self._pairlist_pos != 0 or
                (self._last_refresh + self.refresh_period < datetime.now().timestamp())):

            self._last_refresh = int(datetime.now().timestamp())
            pairs = self._gen_pair_whitelist(pairlist, tickers,
                                             self._config['stake_currency'],
                                             self._sort_key, self._min_value)
        else:
            pairs = pairlist
        self.log_on_refresh(logger.info, f"Searching {self._number_pairs} pairs: {pairs}")
        return pairs

    def _gen_pair_whitelist(self, pairlist: List[str], tickers: Dict,
                            base_currency: str, key: str, min_val: int) -> List[str]:
        """
        Updates the whitelist with with a dynamically generated list
        :param base_currency: base currency as str
        :param key: sort key (defaults to 'quoteVolume')
        :param tickers: Tickers (from exchange.get_tickers()).
        :return: List of pairs
        """
        if self._pairlist_pos == 0:
            # If VolumePairList is the first in the list, use fresh pairlist
            # Check if pair quote currency equals to the stake currency.
            filtered_tickers = [v for k, v in tickers.items()
                                if (self._exchange.get_pair_quote_currency(k) == base_currency
                                    and v[key] is not None)]
        else:
            # If other pairlist is in front, use the incomming pairlist.
            filtered_tickers = [v for k, v in tickers.items() if k in pairlist]

        if min_val > 0:
            filtered_tickers = list(filter(lambda t: t[key] > min_val, filtered_tickers))

        sorted_tickers = sorted(filtered_tickers, reverse=True, key=lambda t: t[key])

        # Validate whitelist to only have active market pairs
        pairs = self._whitelist_for_active_markets([s['symbol'] for s in sorted_tickers])
        pairs = self._verify_blacklist(pairs, aswarning=False)
        # Limit to X number of pairs
        pairs = pairs[:self._number_pairs]

        return pairs
