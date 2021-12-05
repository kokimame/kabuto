""" Tokyo Stock Exchange subclass """
import logging
from typing import Dict, List

import arrow

from freqtrade.exceptions import (DDosProtection, InsufficientFundsError, InvalidOrderException,
                                  OperationalException, TemporaryError)
from freqtrade.exchange.common import retrier
from freqtrade.exchange.exchange_beta import ExchangeBeta

logger = logging.getLogger(__name__)

"""
Equivalent of what? ccxt/binance or freqtrade/binance?
"""
class Tse(ExchangeBeta):

    _ft_has: Dict = {
        'stoploss_on_exchange': True,
        'order_time_in_force': ['gtc', 'fok', 'ioc'],
        'time_in_force_parameter': 'timeInForce',
        'ohlcv_candle_limit': 1000,
        'trades_pagination': 'id',
        'trades_pagination_arg': 'fromId',
    }