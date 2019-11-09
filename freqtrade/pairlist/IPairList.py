"""
Static List provider

Provides lists as configured in config.json

 """
import logging
from abc import ABC, abstractmethod, abstractproperty
from typing import Dict, List

from freqtrade.exchange import market_is_active

logger = logging.getLogger(__name__)


class IPairList(ABC):

    def __init__(self, exchange, config, pairlistconfig: dict) -> None:
        self._exchange = exchange
        self._config = config
        self._pairlistconfig = pairlistconfig

    @property
    def name(self) -> str:
        """
        Gets name of the class
        -> no need to overwrite in subclasses
        """
        return self.__class__.__name__

    @abstractproperty
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requries tickers, an empty List is passed
        as tickers argument to filter_pairlist
        """

    @abstractmethod
    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        -> Please overwrite in subclasses
        """

    @abstractmethod
    def filter_pairlist(self, pairlist: List[str], tickers: List[Dict]) -> List[str]:
        """
        Filters and sorts pairlist and returns the whitelist again.
        Called on each bot iteration - please use internal caching if necessary
        -> Please overwrite in subclasses
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers()). May be cached.
        :return: new whitelist
        """

    def _whitelist_for_active_markets(self, whitelist: List[str]) -> List[str]:
        """
        Check available markets and remove pair from whitelist if necessary
        :param whitelist: the sorted list of pairs the user might want to trade
        :return: the list of pairs the user wants to trade without those unavailable or
        black_listed
        """
        markets = self._exchange.markets

        sanitized_whitelist: List[str] = []
        for pair in whitelist:
            # pair is not in the generated dynamic market or has the wrong stake currency
            if (pair not in markets or not pair.endswith(self._config['stake_currency'])):
                logger.warning(f"Pair {pair} is not compatible with exchange "
                               f"{self._exchange.name}. Removing it from whitelist..")
                continue
            # Check if market is active
            market = markets[pair]
            if not market_is_active(market):
                logger.info(f"Ignoring {pair} from whitelist. Market is not active.")
                continue
            if pair not in sanitized_whitelist:
                sanitized_whitelist.append(pair)

        # We need to remove pairs that are unknown
        return sanitized_whitelist
