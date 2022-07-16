"""Kabus exchange subclass."""
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

from freqtrade.enums import TradingMode, MarginMode
from freqtrade.exchange import Exchange


logger = logging.getLogger(__name__)


class Kabusday(Exchange):
    """Kabus for Day Trading exchange class.

    Contains adjustments needed for Freqtrade to work with this exchange.

    Please note that this exchange is not included in the list of exchanges
    officially supported by the Freqtrade development team. So some features
    may still not work as expected.
    """

    _supported_trading_mode_margin_pairs: List[Tuple[TradingMode, MarginMode]] = [
        # TradingMode.SPOT always supported and not required in this list
        # (TradingMode.MARGIN, MarginMode.CROSS),
        # (TradingMode.FUTURES, MarginMode.CROSS),
        (TradingMode.FUTURES, MarginMode.ISOLATED)
    ]

    _ft_has: Dict = {
        # "stoploss_on_exchange": True,
        # "stoploss_order_types": {"limit": "stop_loss_limit"},
        # "order_time_in_force": ['gtc', 'fok', 'ioc'],
        # "time_in_force_parameter": "timeInForce",
        # "ohlcv_candle_limit": 1000,
        # "trades_pagination": "id",
        # "trades_pagination_arg": "fromId",
        # "l2_limit_range": [5, 10, 20, 50, 100, 500, 1000],
        "ccxt_futures_name": "future"
    }

    def get_funding_fees(
            self, pair: str, amount: float, is_short: bool, open_date: datetime) -> float:
        return 0.0

    def market_is_tradable(self, market: Dict[str, Any]) -> bool:
        """
        Check if the market symbol is tradable by Freqtrade.
        By default, checks if it's splittable by `/` and both sides correspond to base / quote
        """
        symbol_parts = market['symbol'].split('/')
        # return (len(symbol_parts) == 2 and
        #         len(symbol_parts[0]) > 0 and
        #         len(symbol_parts[1]) > 0 and
        #         symbol_parts[0] == market.get('base') and
        #         symbol_parts[1] == market.get('quote')
        #         )
        return True

    #
    # def stoploss_adjust(self, stop_loss: float, order: Dict) -> bool:
    #     """
    #     Verify stop_loss against stoploss-order value (limit or price)
    #     Returns True if adjustment is necessary.
    #     """
    #     return order['info'].get('stop') is not None and stop_loss > float(order['stopPrice'])
    #
    # def _get_stop_params(self, ordertype: str, stop_price: float) -> Dict:
    #
    #     params = self._params.copy()
    #     params.update({
    #         'stopPrice': stop_price,
    #         'stop': 'loss'
    #         })
    #     return params
