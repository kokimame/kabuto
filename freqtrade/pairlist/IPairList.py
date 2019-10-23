"""
Static List provider

Provides lists as configured in config.json

 """
import logging
from abc import ABC, abstractmethod
from typing import List

from freqtrade.exchange import market_is_active


logger = logging.getLogger(__name__)


class IPairList(ABC):

    def __init__(self, freqtrade, config: dict) -> None:
        self._freqtrade = freqtrade
        self._config = config
        self._whitelist = self._config['exchange']['pair_whitelist']
        self._blacklist = self._config['exchange'].get('pair_blacklist', [])

    @property
    def name(self) -> str:
        """
        Gets name of the class
        -> no need to overwrite in subclasses
        """
        return self.__class__.__name__

    @property
    def whitelist(self) -> List[str]:
        """
        Has the current whitelist
        -> no need to overwrite in subclasses
        """
        return self._whitelist

    @property
    def blacklist(self) -> List[str]:
        """
        Has the current blacklist
        -> no need to overwrite in subclasses
        """
        return self._blacklist

    @abstractmethod
    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        -> Please overwrite in subclasses
        """

    @abstractmethod
    def refresh_pairlist(self) -> None:
        """
        Refreshes pairlists and assigns them to self._whitelist and self._blacklist respectively
        -> Please overwrite in subclasses
        """

    def _validate_whitelist(self, whitelist: List[str]) -> List[str]:
        """
        Check available markets and remove pair from whitelist if necessary
        :param whitelist: the sorted list of pairs the user might want to trade
        :return: the list of pairs the user wants to trade without those unavailable or
        black_listed
        """
        markets = self._freqtrade.exchange.markets

        sanitized_whitelist = set()
        for pair in whitelist:
            # pair is not in the generated dynamic market, or in the blacklist ... ignore it
            if (pair in self.blacklist or pair not in markets
                    or not pair.endswith(self._config['stake_currency'])):
                logger.warning(f"Pair {pair} is not compatible with exchange "
                               f"{self._freqtrade.exchange.name} or contained in "
                               f"your blacklist. Removing it from whitelist..")
                continue
            # Check if market is active
            market = markets[pair]
            if not market_is_active(market):
                logger.info(f"Ignoring {pair} from whitelist. Market is not active.")
                continue
            sanitized_whitelist.add(pair)

        # We need to remove pairs that are unknown
        return list(sanitized_whitelist)
