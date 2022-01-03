""" KabuStation subclass """
import logging
from typing import Dict

from freqtrade.kabuto.exchange_beta import ExchangeBeta

logger = logging.getLogger(__name__)

"""
Equivalent of what? ccxt/binance or freqtrade/binance?
"""


class Kabus(ExchangeBeta):
    _ft_has: Dict = {
        'stoploss_on_exchange': True,
        'order_time_in_force': ['gtc', 'fok', 'ioc'],
        'time_in_force_parameter': 'timeInForce',
        'ohlcv_candle_limit': 1000,
        'trades_pagination': 'id',
        'trades_pagination_arg': 'fromId',
    }
