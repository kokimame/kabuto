"""
Freqtrade is the main module of this bot. It contains the class Freqtrade()
"""
import copy
import logging
import traceback
from datetime import datetime, timezone
from math import isclose
from threading import Lock
from typing import Any, Dict, List, Optional

import arrow
from cachetools import TTLCache

from freqtrade import __version__, constants
from freqtrade.configuration import validate_config_consistency
from freqtrade.data.converter import order_book_to_dataframe
from freqtrade.data.dataprovider import DataProvider
from freqtrade.edge import Edge
from freqtrade.exceptions import (DependencyException, ExchangeError, InsufficientFundsError,
                                  InvalidOrderException, PricingError)
from freqtrade.exchange import timeframe_to_minutes, timeframe_to_seconds
from freqtrade.misc import safe_value_fallback, safe_value_fallback2
from freqtrade.mixins import LoggingMixin
from freqtrade.persistence import Order, PairLocks, Trade, cleanup_db, init_db
from freqtrade.plugins.pairlistmanager import PairListManager
from freqtrade.plugins.protectionmanager import ProtectionManager
from freqtrade.resolvers import ExchangeResolver, StrategyResolver
from freqtrade.rpc import RPCManager, RPCMessageType
from freqtrade.state import State
from freqtrade.strategy.interface import IStrategy, SellType
from freqtrade.strategy.strategy_wrapper import strategy_safe_wrapper
from freqtrade.wallets import Wallets


logger = logging.getLogger(__name__)


class FreqtradeBot(LoggingMixin):
    """
    Freqtrade is the main class of the bot.
    This is from here the bot start its logic.
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Init all variables and objects the bot needs to work
        :param config: configuration dict, you can use Configuration.get_config()
        to get the config dict.
        """

        logger.info('Starting freqtrade %s', __version__)

        # Init bot state
        self.state = State.STOPPED

        # Init objects
        self.config = config

        # Cache values for 1800 to avoid frequent polling of the exchange for prices
        # Caching only applies to RPC methods, so prices for open trades are still
        # refreshed once every iteration.
        self._sell_rate_cache: TTLCache = TTLCache(maxsize=100, ttl=1800)
        self._buy_rate_cache: TTLCache = TTLCache(maxsize=100, ttl=1800)

        self.strategy: IStrategy = StrategyResolver.load_strategy(self.config)

        # Check config consistency here since strategies can set certain options
        validate_config_consistency(config)

        self.exchange = ExchangeResolver.load_exchange(self.config['exchange']['name'], self.config)

        init_db(self.config.get('db_url', None), clean_open_orders=self.config['dry_run'])

        self.wallets = Wallets(self.config, self.exchange)

        PairLocks.timeframe = self.config['timeframe']

        self.pairlists = PairListManager(self.exchange, self.config)

        self.dataprovider = DataProvider(self.config, self.exchange, self.pairlists)

        self.protections = ProtectionManager(self.config)

        # Attach Dataprovider to Strategy baseclass
        IStrategy.dp = self.dataprovider
        # Attach Wallets to Strategy baseclass
        IStrategy.wallets = self.wallets

        # Initializing Edge only if enabled
        self.edge = Edge(self.config, self.exchange, self.strategy) if \
            self.config.get('edge', {}).get('enabled', False) else None

        self.active_pair_whitelist = self._refresh_active_whitelist()

        # Set initial bot state from config
        initial_state = self.config.get('initial_state')
        self.state = State[initial_state.upper()] if initial_state else State.STOPPED

        # RPC runs in separate threads, can start handling external commands just after
        # initialization, even before Freqtradebot has a chance to start its throttling,
        # so anything in the Freqtradebot instance should be ready (initialized), including
        # the initial state of the bot.
        # Keep this at the end of this initialization method.
        self.rpc: RPCManager = RPCManager(self)
        # Protect sell-logic from forcesell and viceversa
        self._sell_lock = Lock()
        LoggingMixin.__init__(self, logger, timeframe_to_seconds(self.strategy.timeframe))

    def notify_status(self, msg: str) -> None:
        """
        Public method for users of this class (worker, etc.) to send notifications
        via RPC about changes in the bot status.
        """
        self.rpc.send_msg({
            'type': RPCMessageType.STATUS_NOTIFICATION,
            'status': msg
        })

    def cleanup(self) -> None:
        """
        Cleanup pending resources on an already stopped bot
        :return: None
        """
        logger.info('Cleaning up modules ...')

        if self.config['cancel_open_orders_on_exit']:
            self.cancel_all_open_orders()

        self.check_for_open_trades()

        self.rpc.cleanup()
        cleanup_db()

    def startup(self) -> None:
        """
        Called on startup and after reloading the bot - triggers notifications and
        performs startup tasks
        """
        self.rpc.startup_messages(self.config, self.pairlists, self.protections)
        if not self.edge:
            # Adjust stoploss if it was changed
            Trade.stoploss_reinitialization(self.strategy.stoploss)

        # Only update open orders on startup
        # This will update the database after the initial migration
        self.update_open_orders()

    def process(self) -> None:
        """
        Queries the persistence layer for open trades and handles them,
        otherwise a new trade is created.
        :return: True if one or more trades has been created or closed, False otherwise
        """

        # Check whether markets have to be reloaded and reload them when it's needed
        self.exchange.reload_markets()

        self.update_closed_trades_without_assigned_fees()

        # Query trades from persistence layer
        trades = Trade.get_open_trades()

        self.active_pair_whitelist = self._refresh_active_whitelist(trades)

        # Refreshing candles
        self.dataprovider.refresh(self.pairlists.create_pair_list(self.active_pair_whitelist),
                                  self.strategy.informative_pairs())

        strategy_safe_wrapper(self.strategy.bot_loop_start, supress_error=True)()

        self.strategy.analyze(self.active_pair_whitelist)

        with self._sell_lock:
            # Check and handle any timed out open orders
            self.check_handle_timedout()

        # Protect from collisions with forcesell.
        # Without this, freqtrade my try to recreate stoploss_on_exchange orders
        # while selling is in process, since telegram messages arrive in an different thread.
        with self._sell_lock:
            # First process current opened trades (positions)
            self.exit_positions(trades)

        # Then looking for buy opportunities
        if self.get_free_open_trades():
            self.enter_positions()

        Trade.session.flush()

    def process_stopped(self) -> None:
        """
        Close all orders that were left open
        """
        if self.config['cancel_open_orders_on_exit']:
            self.cancel_all_open_orders()

    def check_for_open_trades(self):
        """
        Notify the user when the bot is stopped
        and there are still open trades active.
        """
        open_trades = Trade.get_trades([Trade.is_open.is_(True)]).all()

        if len(open_trades) != 0:
            msg = {
                'type': RPCMessageType.WARNING_NOTIFICATION,
                'status':  f"{len(open_trades)} open trades active.\n\n"
                           f"Handle these trades manually on {self.exchange.name}, "
                           f"or '/start' the bot again and use '/stopbuy' "
                           f"to handle open trades gracefully. \n"
                           f"{'Trades are simulated.' if self.config['dry_run'] else ''}",
            }
            self.rpc.send_msg(msg)

    def _refresh_active_whitelist(self, trades: List[Trade] = []) -> List[str]:
        """
        Refresh active whitelist from pairlist or edge and extend it with
        pairs that have open trades.
        """
        # Refresh whitelist
        self.pairlists.refresh_pairlist()
        _whitelist = self.pairlists.whitelist

        # Calculating Edge positioning
        if self.edge:
            self.edge.calculate()
            _whitelist = self.edge.adjust(_whitelist)

        if trades:
            # Extend active-pair whitelist with pairs of open trades
            # It ensures that candle (OHLCV) data are downloaded for open trades as well
            _whitelist.extend([trade.pair for trade in trades if trade.pair not in _whitelist])
        return _whitelist

    def get_free_open_trades(self):
        """
        Return the number of free open trades slots or 0 if
        max number of open trades reached
        """
        open_trades = len(Trade.get_open_trades())
        return max(0, self.config['max_open_trades'] - open_trades)

    def update_open_orders(self):
        """
        Updates open orders based on order list kept in the database.
        Mainly updates the state of orders - but may also close trades
        """
        if self.config['dry_run']:
            # Updating open orders in dry-run does not make sense and will fail.
            return

        orders = Order.get_open_orders()
        logger.info(f"Updating {len(orders)} open orders.")
        for order in orders:
            try:
                fo = self.exchange.fetch_order_or_stoploss_order(order.order_id, order.ft_pair,
                                                                 order.ft_order_side == 'stoploss')

                self.update_trade_state(order.trade, order.order_id, fo)

            except ExchangeError as e:

                logger.warning(f"Error updating Order {order.order_id} due to {e}")

    def update_closed_trades_without_assigned_fees(self):
        """
        Update closed trades without close fees assigned.
        Only acts when Orders are in the database, otherwise the last orderid is unknown.
        """
        if self.config['dry_run']:
            # Updating open orders in dry-run does not make sense and will fail.
            return

        trades: List[Trade] = Trade.get_sold_trades_without_assigned_fees()
        for trade in trades:

            if not trade.is_open and not trade.fee_updated('sell'):
                # Get sell fee
                order = trade.select_order('sell', False)
                if order:
                    logger.info(f"Updating sell-fee on trade {trade} for order {order.order_id}.")
                    self.update_trade_state(trade, order.order_id,
                                            stoploss_order=order.ft_order_side == 'stoploss')

        trades: List[Trade] = Trade.get_open_trades_without_assigned_fees()
        for trade in trades:
            if trade.is_open and not trade.fee_updated('buy'):
                order = trade.select_order('buy', False)
                if order:
                    logger.info(f"Updating buy-fee on trade {trade} for order {order.order_id}.")
                    self.update_trade_state(trade, order.order_id)

    def handle_insufficient_funds(self, trade: Trade):
        """
        Determine if we ever opened a sell order for this trade.
        If not, try update buy fees - otherwise "refind" the open order we obviously lost.
        """
        sell_order = trade.select_order('sell', None)
        if sell_order:
            self.refind_lost_order(trade)
        else:
            self.reupdate_buy_order_fees(trade)

    def reupdate_buy_order_fees(self, trade: Trade):
        """
        Get buy order from database, and try to reupdate.
        Handles trades where the initial fee-update did not work.
        """
        logger.info(f"Trying to reupdate buy fees for {trade}")
        order = trade.select_order('buy', False)
        if order:
            logger.info(f"Updating buy-fee on trade {trade} for order {order.order_id}.")
            self.update_trade_state(trade, order.order_id)

    def refind_lost_order(self, trade):
        """
        Try refinding a lost trade.
        Only used when InsufficientFunds appears on sell orders (stoploss or sell).
        Tries to walk the stored orders and sell them off eventually.
        """
        logger.info(f"Trying to refind lost order for {trade}")
        for order in trade.orders:
            logger.info(f"Trying to refind {order}")
            fo = None
            if not order.ft_is_open:
                logger.debug(f"Order {order} is no longer open.")
                continue
            if order.ft_order_side == 'buy':
                # Skip buy side - this is handled by reupdate_buy_order_fees
                continue
            try:
                fo = self.exchange.fetch_order_or_stoploss_order(order.order_id, order.ft_pair,
                                                                 order.ft_order_side == 'stoploss')
                if order.ft_order_side == 'stoploss':
                    if fo and fo['status'] == 'open':
                        # Assume this as the open stoploss order
                        trade.stoploss_order_id = order.order_id
                elif order.ft_order_side == 'sell':
                    if fo and fo['status'] == 'open':
                        # Assume this as the open order
                        trade.open_order_id = order.order_id
                if fo:
                    logger.info(f"Found {order} for trade {trade}.jj")
                    self.update_trade_state(trade, order.order_id, fo,
                                            stoploss_order=order.ft_order_side == 'stoploss')

            except ExchangeError:
                logger.warning(f"Error updating {order.order_id}.")

#
# BUY / enter positions / open trades logic and methods
#

    def enter_positions(self) -> int:
        """
        Tries to execute buy orders for new trades (positions)
        """
        trades_created = 0

        whitelist = copy.deepcopy(self.active_pair_whitelist)
        if not whitelist:
            logger.info("Active pair whitelist is empty.")
            return trades_created
        # Remove pairs for currently opened trades from the whitelist
        for trade in Trade.get_open_trades():
            if trade.pair in whitelist:
                whitelist.remove(trade.pair)
                logger.debug('Ignoring %s in pair whitelist', trade.pair)

        if not whitelist:
            logger.info("No currency pair in active pair whitelist, "
                        "but checking to sell open trades.")
            return trades_created
        if PairLocks.is_global_lock():
            lock = PairLocks.get_pair_longest_lock('*')
            if lock:
                self.log_once(f"Global pairlock active until "
                              f"{lock.lock_end_time.strftime(constants.DATETIME_PRINT_FORMAT)}. "
                              "Not creating new trades.", logger.info)
            else:
                self.log_once("Global pairlock active. Not creating new trades.", logger.info)
            return trades_created
        # Create entity and execute trade for each pair from whitelist
        for pair in whitelist:
            try:
                trades_created += self.create_trade(pair)
            except DependencyException as exception:
                logger.warning('Unable to create trade for %s: %s', pair, exception)

        if not trades_created:
            logger.debug("Found no buy signals for whitelisted currencies. Trying again...")

        return trades_created

    def get_buy_rate(self, pair: str, refresh: bool) -> float:
        """
        Calculates bid target between current ask price and last price
        :param pair: Pair to get rate for
        :param refresh: allow cached data
        :return: float: Price
        """
        if not refresh:
            rate = self._buy_rate_cache.get(pair)
            # Check if cache has been invalidated
            if rate:
                logger.debug(f"Using cached buy rate for {pair}.")
                return rate

        bid_strategy = self.config.get('bid_strategy', {})
        if 'use_order_book' in bid_strategy and bid_strategy.get('use_order_book', False):
            logger.info(
                f"Getting price from order book {bid_strategy['price_side'].capitalize()} side."
            )
            order_book_top = bid_strategy.get('order_book_top', 1)
            order_book = self.exchange.fetch_l2_order_book(pair, order_book_top)
            logger.debug('order_book %s', order_book)
            # top 1 = index 0
            try:
                rate_from_l2 = order_book[f"{bid_strategy['price_side']}s"][order_book_top - 1][0]
            except (IndexError, KeyError) as e:
                logger.warning(
                    "Buy Price from orderbook could not be determined."
                    f"Orderbook: {order_book}"
                 )
                raise PricingError from e
            logger.info(f'...top {order_book_top} order book buy rate {rate_from_l2:.8f}')
            used_rate = rate_from_l2
        else:
            logger.info(f"Using Last {bid_strategy['price_side'].capitalize()} / Last Price")
            ticker = self.exchange.fetch_ticker(pair)
            ticker_rate = ticker[bid_strategy['price_side']]
            if ticker['last'] and ticker_rate > ticker['last']:
                balance = self.config['bid_strategy']['ask_last_balance']
                ticker_rate = ticker_rate + balance * (ticker['last'] - ticker_rate)
            used_rate = ticker_rate

        self._buy_rate_cache[pair] = used_rate

        return used_rate

    def get_trade_stake_amount(self, pair: str) -> float:
        """
        Calculate stake amount for the trade
        :return: float: Stake amount
        :raise: DependencyException if the available stake amount is too low
        """
        stake_amount: float
        # Ensure wallets are uptodate.
        self.wallets.update()

        if self.edge:
            stake_amount = self.edge.stake_amount(
                pair,
                self.wallets.get_free(self.config['stake_currency']),
                self.wallets.get_total(self.config['stake_currency']),
                Trade.total_open_trades_stakes()
            )
        else:
            stake_amount = self.config['stake_amount']
            if stake_amount == constants.UNLIMITED_STAKE_AMOUNT:
                stake_amount = self._calculate_unlimited_stake_amount()

        return self._check_available_stake_amount(stake_amount)

    def _get_available_stake_amount(self) -> float:
        """
        Return the total currently available balance in stake currency,
        respecting tradable_balance_ratio.
        Calculated as
        <open_trade stakes> + free amount ) * tradable_balance_ratio - <open_trade stakes>
        """
        val_tied_up = Trade.total_open_trades_stakes()

        # Ensure <tradable_balance_ratio>% is used from the overall balance
        # Otherwise we'd risk lowering stakes with each open trade.
        # (tied up + current free) * ratio) - tied up
        available_amount = ((val_tied_up + self.wallets.get_free(self.config['stake_currency'])) *
                            self.config['tradable_balance_ratio']) - val_tied_up
        return available_amount

    def _calculate_unlimited_stake_amount(self) -> float:
        """
        Calculate stake amount for "unlimited" stake amount
        :return: 0 if max number of trades reached, else stake_amount to use.
        """
        free_open_trades = self.get_free_open_trades()
        if not free_open_trades:
            return 0

        available_amount = self._get_available_stake_amount()

        return available_amount / free_open_trades

    def _check_available_stake_amount(self, stake_amount: float) -> float:
        """
        Check if stake amount can be fulfilled with the available balance
        for the stake currency
        :return: float: Stake amount
        """
        available_amount = self._get_available_stake_amount()

        if self.config['amend_last_stake_amount']:
            # Remaining amount needs to be at least stake_amount * last_stake_amount_min_ratio
            # Otherwise the remaining amount is too low to trade.
            if available_amount > (stake_amount * self.config['last_stake_amount_min_ratio']):
                stake_amount = min(stake_amount, available_amount)
            else:
                stake_amount = 0

        if available_amount < stake_amount:
            raise DependencyException(
                f"Available balance ({available_amount} {self.config['stake_currency']}) is "
                f"lower than stake amount ({stake_amount} {self.config['stake_currency']})"
            )

        return stake_amount

    def _get_min_pair_stake_amount(self, pair: str, price: float) -> Optional[float]:
        try:
            market = self.exchange.markets[pair]
        except KeyError:
            raise ValueError(f"Can't get market information for symbol {pair}")

        if 'limits' not in market:
            return None

        min_stake_amounts = []
        limits = market['limits']
        if ('cost' in limits and 'min' in limits['cost']
                and limits['cost']['min'] is not None):
            min_stake_amounts.append(limits['cost']['min'])

        if ('amount' in limits and 'min' in limits['amount']
                and limits['amount']['min'] is not None):
            min_stake_amounts.append(limits['amount']['min'] * price)

        if not min_stake_amounts:
            return None

        # reserve some percent defined in config (5% default) + stoploss
        amount_reserve_percent = 1.0 - self.config.get('amount_reserve_percent',
                                                       constants.DEFAULT_AMOUNT_RESERVE_PERCENT)
        amount_reserve_percent += self.strategy.stoploss
        # it should not be more than 50%
        amount_reserve_percent = max(amount_reserve_percent, 0.5)

        # The value returned should satisfy both limits: for amount (base currency) and
        # for cost (quote, stake currency), so max() is used here.
        # See also #2575 at github.
        return max(min_stake_amounts) / amount_reserve_percent

    def create_trade(self, pair: str) -> bool:
        """
        Check the implemented trading strategy for buy signals.

        If the pair triggers the buy signal a new trade record gets created
        and the buy-order opening the trade gets issued towards the exchange.

        :return: True if a trade has been created.
        """
        logger.debug(f"create_trade for pair {pair}")

        analyzed_df, _ = self.dataprovider.get_analyzed_dataframe(pair, self.strategy.timeframe)
        nowtime = analyzed_df.iloc[-1]['date'] if len(analyzed_df) > 0 else None
        if self.strategy.is_pair_locked(pair, nowtime):
            lock = PairLocks.get_pair_longest_lock(pair, nowtime)
            if lock:
                self.log_once(f"Pair {pair} is still locked until "
                              f"{lock.lock_end_time.strftime(constants.DATETIME_PRINT_FORMAT)}.",
                              logger.info)
            else:
                self.log_once(f"Pair {pair} is still locked.", logger.info)
            return False

        # get_free_open_trades is checked before create_trade is called
        # but it is still used here to prevent opening too many trades within one iteration
        if not self.get_free_open_trades():
            logger.debug(f"Can't open a new trade for {pair}: max number of trades is reached.")
            return False

        # running get_signal on historical data fetched
        (buy, sell) = self.strategy.get_signal(pair, self.strategy.timeframe, analyzed_df)

        if buy and not sell:
            stake_amount = self.get_trade_stake_amount(pair)
            if not stake_amount:
                logger.debug(f"Stake amount is 0, ignoring possible trade for {pair}.")
                return False

            logger.info(f"Buy signal found: about create a new trade with stake_amount: "
                        f"{stake_amount} ...")

            bid_check_dom = self.config.get('bid_strategy', {}).get('check_depth_of_market', {})
            if ((bid_check_dom.get('enabled', False)) and
                    (bid_check_dom.get('bids_to_ask_delta', 0) > 0)):
                if self._check_depth_of_market_buy(pair, bid_check_dom):
                    logger.info(f'Executing Buy for {pair}.')
                    return self.execute_buy(pair, stake_amount)
                else:
                    return False

            logger.info(f'Executing Buy for {pair}')
            return self.execute_buy(pair, stake_amount)
        else:
            return False

    def _check_depth_of_market_buy(self, pair: str, conf: Dict) -> bool:
        """
        Checks depth of market before executing a buy
        """
        conf_bids_to_ask_delta = conf.get('bids_to_ask_delta', 0)
        logger.info(f"Checking depth of market for {pair} ...")
        order_book = self.exchange.fetch_l2_order_book(pair, 1000)
        order_book_data_frame = order_book_to_dataframe(order_book['bids'], order_book['asks'])
        order_book_bids = order_book_data_frame['b_size'].sum()
        order_book_asks = order_book_data_frame['a_size'].sum()
        bids_ask_delta = order_book_bids / order_book_asks
        logger.info(
            f"Bids: {order_book_bids}, Asks: {order_book_asks}, Delta: {bids_ask_delta}, "
            f"Bid Price: {order_book['bids'][0][0]}, Ask Price: {order_book['asks'][0][0]}, "
            f"Immediate Bid Quantity: {order_book['bids'][0][1]}, "
            f"Immediate Ask Quantity: {order_book['asks'][0][1]}."
        )
        if bids_ask_delta >= conf_bids_to_ask_delta:
            logger.info(f"Bids to asks delta for {pair} DOES satisfy condition.")
            return True
        else:
            logger.info(f"Bids to asks delta for {pair} does not satisfy condition.")
            return False

    def execute_buy(self, pair: str, stake_amount: float, price: Optional[float] = None) -> bool:
        """
        Executes a limit buy for the given pair
        :param pair: pair for which we want to create a LIMIT_BUY
        :return: True if a buy order is created, false if it fails.
        """
        time_in_force = self.strategy.order_time_in_force['buy']

        if price:
            buy_limit_requested = price
        else:
            # Calculate price
            buy_limit_requested = self.get_buy_rate(pair, True)

        if not buy_limit_requested:
            raise PricingError('Could not determine buy price.')

        min_stake_amount = self._get_min_pair_stake_amount(pair, buy_limit_requested)
        if min_stake_amount is not None and min_stake_amount > stake_amount:
            logger.warning(
                f"Can't open a new trade for {pair}: stake amount "
                f"is too small ({stake_amount} < {min_stake_amount})"
            )
            return False

        amount = stake_amount / buy_limit_requested
        order_type = self.strategy.order_types['buy']
        if not strategy_safe_wrapper(self.strategy.confirm_trade_entry, default_retval=True)(
                pair=pair, order_type=order_type, amount=amount, rate=buy_limit_requested,
                time_in_force=time_in_force):
            logger.info(f"User requested abortion of buying {pair}")
            return False
        amount = self.exchange.amount_to_precision(pair, amount)
        order = self.exchange.buy(pair=pair, ordertype=order_type,
                                  amount=amount, rate=buy_limit_requested,
                                  time_in_force=time_in_force)
        order_obj = Order.parse_from_ccxt_object(order, pair, 'buy')
        order_id = order['id']
        order_status = order.get('status', None)

        # we assume the order is executed at the price requested
        buy_limit_filled_price = buy_limit_requested
        amount_requested = amount

        if order_status == 'expired' or order_status == 'rejected':
            order_tif = self.strategy.order_time_in_force['buy']

            # return false if the order is not filled
            if float(order['filled']) == 0:
                logger.warning('Buy %s order with time in force %s for %s is %s by %s.'
                               ' zero amount is fulfilled.',
                               order_tif, order_type, pair, order_status, self.exchange.name)
                return False
            else:
                # the order is partially fulfilled
                # in case of IOC orders we can check immediately
                # if the order is fulfilled fully or partially
                logger.warning('Buy %s order with time in force %s for %s is %s by %s.'
                               ' %s amount fulfilled out of %s (%s remaining which is canceled).',
                               order_tif, order_type, pair, order_status, self.exchange.name,
                               order['filled'], order['amount'], order['remaining']
                               )
                stake_amount = order['cost']
                amount = safe_value_fallback(order, 'filled', 'amount')
                buy_limit_filled_price = safe_value_fallback(order, 'average', 'price')

        # in case of FOK the order may be filled immediately and fully
        elif order_status == 'closed':
            stake_amount = order['cost']
            amount = safe_value_fallback(order, 'filled', 'amount')
            buy_limit_filled_price = safe_value_fallback(order, 'average', 'price')

        # Fee is applied twice because we make a LIMIT_BUY and LIMIT_SELL
        fee = self.exchange.get_fee(symbol=pair, taker_or_maker='maker')
        trade = Trade(
            pair=pair,
            stake_amount=stake_amount,
            amount=amount,
            amount_requested=amount_requested,
            fee_open=fee,
            fee_close=fee,
            open_rate=buy_limit_filled_price,
            open_rate_requested=buy_limit_requested,
            open_date=datetime.utcnow(),
            exchange=self.exchange.id,
            open_order_id=order_id,
            strategy=self.strategy.get_strategy_name(),
            timeframe=timeframe_to_minutes(self.config['timeframe'])
        )
        trade.orders.append(order_obj)

        # Update fees if order is closed
        if order_status == 'closed':
            self.update_trade_state(trade, order_id, order)

        Trade.session.add(trade)
        Trade.session.flush()

        # Updating wallets
        self.wallets.update()

        self._notify_buy(trade, order_type)

        return True

    def _notify_buy(self, trade: Trade, order_type: str) -> None:
        """
        Sends rpc notification when a buy occured.
        """
        msg = {
            'trade_id': trade.id,
            'type': RPCMessageType.BUY_NOTIFICATION,
            'exchange': self.exchange.name.capitalize(),
            'pair': trade.pair,
            'limit': trade.open_rate,
            'order_type': order_type,
            'stake_amount': trade.stake_amount,
            'stake_currency': self.config['stake_currency'],
            'fiat_currency': self.config.get('fiat_display_currency', None),
            'amount': trade.amount,
            'open_date': trade.open_date or datetime.utcnow(),
            'current_rate': trade.open_rate_requested,
        }

        # Send the message
        self.rpc.send_msg(msg)

    def _notify_buy_cancel(self, trade: Trade, order_type: str, reason: str) -> None:
        """
        Sends rpc notification when a buy cancel occured.
        """
        current_rate = self.get_buy_rate(trade.pair, False)

        msg = {
            'trade_id': trade.id,
            'type': RPCMessageType.BUY_CANCEL_NOTIFICATION,
            'exchange': self.exchange.name.capitalize(),
            'pair': trade.pair,
            'limit': trade.open_rate,
            'order_type': order_type,
            'stake_amount': trade.stake_amount,
            'stake_currency': self.config['stake_currency'],
            'fiat_currency': self.config.get('fiat_display_currency', None),
            'amount': trade.amount,
            'open_date': trade.open_date,
            'current_rate': current_rate,
            'reason': reason,
        }

        # Send the message
        self.rpc.send_msg(msg)

#
# SELL / exit positions / close trades logic and methods
#

    def exit_positions(self, trades: List[Any]) -> int:
        """
        Tries to execute sell orders for open trades (positions)
        """
        trades_closed = 0
        for trade in trades:
            try:

                if (self.strategy.order_types.get('stoploss_on_exchange') and
                        self.handle_stoploss_on_exchange(trade)):
                    trades_closed += 1
                    continue
                # Check if we can sell our current pair
                if trade.open_order_id is None and trade.is_open and self.handle_trade(trade):
                    trades_closed += 1

            except DependencyException as exception:
                logger.warning('Unable to sell trade %s: %s', trade.pair, exception)

        # Updating wallets if any trade occured
        if trades_closed:
            self.wallets.update()

        return trades_closed

    def _order_book_gen(self, pair: str, side: str, order_book_max: int = 1,
                        order_book_min: int = 1):
        """
        Helper generator to query orderbook in loop (used for early sell-order placing)
        """
        order_book = self.exchange.fetch_l2_order_book(pair, order_book_max)
        for i in range(order_book_min, order_book_max + 1):
            yield order_book[side][i - 1][0]

    def get_sell_rate(self, pair: str, refresh: bool) -> float:
        """
        Get sell rate - either using ticker bid or first bid based on orderbook
        The orderbook portion is only used for rpc messaging, which would otherwise fail
        for BitMex (has no bid/ask in fetch_ticker)
        or remain static in any other case since it's not updating.
        :param pair: Pair to get rate for
        :param refresh: allow cached data
        :return: Bid rate
        """
        if not refresh:
            rate = self._sell_rate_cache.get(pair)
            # Check if cache has been invalidated
            if rate:
                logger.debug(f"Using cached sell rate for {pair}.")
                return rate

        ask_strategy = self.config.get('ask_strategy', {})
        if ask_strategy.get('use_order_book', False):
            # This code is only used for notifications, selling uses the generator directly
            logger.info(
                f"Getting price from order book {ask_strategy['price_side'].capitalize()} side."
            )
            try:
                rate = next(self._order_book_gen(pair, f"{ask_strategy['price_side']}s"))
            except (IndexError, KeyError) as e:
                logger.warning("Sell Price at location from orderbook could not be determined.")
                raise PricingError from e
        else:
            rate = self.exchange.fetch_ticker(pair)[ask_strategy['price_side']]
        if rate is None:
            raise PricingError(f"Sell-Rate for {pair} was empty.")
        self._sell_rate_cache[pair] = rate
        return rate

    def handle_trade(self, trade: Trade) -> bool:
        """
        Sells the current pair if the threshold is reached and updates the trade record.
        :return: True if trade has been sold, False otherwise
        """
        if not trade.is_open:
            raise DependencyException(f'Attempt to handle closed trade: {trade}')

        logger.debug('Handling %s ...', trade)

        (buy, sell) = (False, False)

        config_ask_strategy = self.config.get('ask_strategy', {})

        if (config_ask_strategy.get('use_sell_signal', True) or
                config_ask_strategy.get('ignore_roi_if_buy_signal', False)):
            analyzed_df, _ = self.dataprovider.get_analyzed_dataframe(trade.pair,
                                                                      self.strategy.timeframe)

            (buy, sell) = self.strategy.get_signal(trade.pair, self.strategy.timeframe, analyzed_df)

        if config_ask_strategy.get('use_order_book', False):
            order_book_min = config_ask_strategy.get('order_book_min', 1)
            order_book_max = config_ask_strategy.get('order_book_max', 1)
            logger.debug(f'Using order book between {order_book_min} and {order_book_max} '
                         f'for selling {trade.pair}...')

            order_book = self._order_book_gen(trade.pair, f"{config_ask_strategy['price_side']}s",
                                              order_book_min=order_book_min,
                                              order_book_max=order_book_max)
            for i in range(order_book_min, order_book_max + 1):
                try:
                    sell_rate = next(order_book)
                except (IndexError, KeyError) as e:
                    logger.warning(
                        f"Sell Price at location {i} from orderbook could not be determined."
                    )
                    raise PricingError from e
                logger.debug(f"  order book {config_ask_strategy['price_side']} top {i}: "
                             f"{sell_rate:0.8f}")
                # Assign sell-rate to cache - otherwise sell-rate is never updated in the cache,
                # resulting in outdated RPC messages
                self._sell_rate_cache[trade.pair] = sell_rate

                if self._check_and_execute_sell(trade, sell_rate, buy, sell):
                    return True

        else:
            logger.debug('checking sell')
            sell_rate = self.get_sell_rate(trade.pair, True)
            if self._check_and_execute_sell(trade, sell_rate, buy, sell):
                return True

        logger.debug('Found no sell signal for %s.', trade)
        return False

    def create_stoploss_order(self, trade: Trade, stop_price: float) -> bool:
        """
        Abstracts creating stoploss orders from the logic.
        Handles errors and updates the trade database object.
        Force-sells the pair (using EmergencySell reason) in case of Problems creating the order.
        :return: True if the order succeeded, and False in case of problems.
        """
        try:
            stoploss_order = self.exchange.stoploss(pair=trade.pair, amount=trade.amount,
                                                    stop_price=stop_price,
                                                    order_types=self.strategy.order_types)

            order_obj = Order.parse_from_ccxt_object(stoploss_order, trade.pair, 'stoploss')
            trade.orders.append(order_obj)
            trade.stoploss_order_id = str(stoploss_order['id'])
            return True
        except InsufficientFundsError as e:
            logger.warning(f"Unable to place stoploss order {e}.")
            # Try to figure out what went wrong
            self.handle_insufficient_funds(trade)

        except InvalidOrderException as e:
            trade.stoploss_order_id = None
            logger.error(f'Unable to place a stoploss order on exchange. {e}')
            logger.warning('Selling the trade forcefully')
            self.execute_sell(trade, trade.stop_loss, sell_reason=SellType.EMERGENCY_SELL)

        except ExchangeError:
            trade.stoploss_order_id = None
            logger.exception('Unable to place a stoploss order on exchange.')
        return False

    def handle_stoploss_on_exchange(self, trade: Trade) -> bool:
        """
        Check if trade is fulfilled in which case the stoploss
        on exchange should be added immediately if stoploss on exchange
        is enabled.
        """

        logger.debug('Handling stoploss on exchange %s ...', trade)

        stoploss_order = None

        try:
            # First we check if there is already a stoploss on exchange
            stoploss_order = self.exchange.fetch_stoploss_order(
                trade.stoploss_order_id, trade.pair) if trade.stoploss_order_id else None
        except InvalidOrderException as exception:
            logger.warning('Unable to fetch stoploss order: %s', exception)

        if stoploss_order:
            trade.update_order(stoploss_order)

        # We check if stoploss order is fulfilled
        if stoploss_order and stoploss_order['status'] in ('closed', 'triggered'):
            trade.sell_reason = SellType.STOPLOSS_ON_EXCHANGE.value
            self.update_trade_state(trade, trade.stoploss_order_id, stoploss_order,
                                    stoploss_order=True)
            # Lock pair for one candle to prevent immediate rebuys
            self.strategy.lock_pair(trade.pair, datetime.now(timezone.utc),
                                    reason='Auto lock')
            self._notify_sell(trade, "stoploss")
            return True

        if trade.open_order_id or not trade.is_open:
            # Trade has an open Buy or Sell order, Stoploss-handling can't happen in this case
            # as the Amount on the exchange is tied up in another trade.
            # The trade can be closed already (sell-order fill confirmation came in this iteration)
            return False

        # If buy order is fulfilled but there is no stoploss, we add a stoploss on exchange
        if not stoploss_order:
            stoploss = self.edge.stoploss(pair=trade.pair) if self.edge else self.strategy.stoploss
            stop_price = trade.open_rate * (1 + stoploss)

            if self.create_stoploss_order(trade=trade, stop_price=stop_price):
                trade.stoploss_last_update = datetime.utcnow()
                return False

        # If stoploss order is canceled for some reason we add it
        if stoploss_order and stoploss_order['status'] in ('canceled', 'cancelled'):
            if self.create_stoploss_order(trade=trade, stop_price=trade.stop_loss):
                return False
            else:
                trade.stoploss_order_id = None
                logger.warning('Stoploss order was cancelled, but unable to recreate one.')

        # Finally we check if stoploss on exchange should be moved up because of trailing.
        if stoploss_order and self.config.get('trailing_stop', False):
            # if trailing stoploss is enabled we check if stoploss value has changed
            # in which case we cancel stoploss order and put another one with new
            # value immediately
            self.handle_trailing_stoploss_on_exchange(trade, stoploss_order)

        return False

    def handle_trailing_stoploss_on_exchange(self, trade: Trade, order: dict) -> None:
        """
        Check to see if stoploss on exchange should be updated
        in case of trailing stoploss on exchange
        :param Trade: Corresponding Trade
        :param order: Current on exchange stoploss order
        :return: None
        """
        if self.exchange.stoploss_adjust(trade.stop_loss, order):
            # we check if the update is neccesary
            update_beat = self.strategy.order_types.get('stoploss_on_exchange_interval', 60)
            if (datetime.utcnow() - trade.stoploss_last_update).total_seconds() >= update_beat:
                # cancelling the current stoploss on exchange first
                logger.info(f"Cancelling current stoploss on exchange for pair {trade.pair} "
                            f"(orderid:{order['id']}) in order to add another one ...")
                try:
                    co = self.exchange.cancel_stoploss_order(order['id'], trade.pair)
                    trade.update_order(co)
                except InvalidOrderException:
                    logger.exception(f"Could not cancel stoploss order {order['id']} "
                                     f"for pair {trade.pair}")

                # Create new stoploss order
                if not self.create_stoploss_order(trade=trade, stop_price=trade.stop_loss):
                    logger.warning(f"Could not create trailing stoploss order "
                                   f"for pair {trade.pair}.")

    def _check_and_execute_sell(self, trade: Trade, sell_rate: float,
                                buy: bool, sell: bool) -> bool:
        """
        Check and execute sell
        """
        should_sell = self.strategy.should_sell(
            trade, sell_rate, datetime.utcnow(), buy, sell,
            force_stoploss=self.edge.stoploss(trade.pair) if self.edge else 0
        )

        if should_sell.sell_flag:
            logger.info(f'Executing Sell for {trade.pair}. Reason: {should_sell.sell_type}')
            self.execute_sell(trade, sell_rate, should_sell.sell_type)
            return True
        return False

    def _check_timed_out(self, side: str, order: dict) -> bool:
        """
        Check if timeout is active, and if the order is still open and timed out
        """
        timeout = self.config.get('unfilledtimeout', {}).get(side)
        ordertime = arrow.get(order['datetime']).datetime
        if timeout is not None:
            timeout_threshold = arrow.utcnow().shift(minutes=-timeout).datetime

            return (order['status'] == 'open' and order['side'] == side
                    and ordertime < timeout_threshold)
        return False

    def check_handle_timedout(self) -> None:
        """
        Check if any orders are timed out and cancel if neccessary
        :param timeoutvalue: Number of minutes until order is considered timed out
        :return: None
        """

        for trade in Trade.get_open_order_trades():
            try:
                if not trade.open_order_id:
                    continue
                order = self.exchange.fetch_order(trade.open_order_id, trade.pair)
            except (ExchangeError):
                logger.info('Cannot query order for %s due to %s', trade, traceback.format_exc())
                continue

            fully_cancelled = self.update_trade_state(trade, trade.open_order_id, order)

            if (order['side'] == 'buy' and (order['status'] == 'open' or fully_cancelled) and (
                    fully_cancelled
                    or self._check_timed_out('buy', order)
                    or strategy_safe_wrapper(self.strategy.check_buy_timeout,
                                             default_retval=False)(pair=trade.pair,
                                                                   trade=trade,
                                                                   order=order))):
                self.handle_cancel_buy(trade, order, constants.CANCEL_REASON['TIMEOUT'])

            elif (order['side'] == 'sell' and (order['status'] == 'open' or fully_cancelled) and (
                  fully_cancelled
                  or self._check_timed_out('sell', order)
                  or strategy_safe_wrapper(self.strategy.check_sell_timeout,
                                           default_retval=False)(pair=trade.pair,
                                                                 trade=trade,
                                                                 order=order))):
                self.handle_cancel_sell(trade, order, constants.CANCEL_REASON['TIMEOUT'])

    def cancel_all_open_orders(self) -> None:
        """
        Cancel all orders that are currently open
        :return: None
        """

        for trade in Trade.get_open_order_trades():
            try:
                order = self.exchange.fetch_order(trade.open_order_id, trade.pair)
            except (ExchangeError):
                logger.info('Cannot query order for %s due to %s', trade, traceback.format_exc())
                continue

            if order['side'] == 'buy':
                self.handle_cancel_buy(trade, order, constants.CANCEL_REASON['ALL_CANCELLED'])

            elif order['side'] == 'sell':
                self.handle_cancel_sell(trade, order, constants.CANCEL_REASON['ALL_CANCELLED'])

    def handle_cancel_buy(self, trade: Trade, order: Dict, reason: str) -> bool:
        """
        Buy cancel - cancel order
        :return: True if order was fully cancelled
        """
        was_trade_fully_canceled = False

        # Cancelled orders may have the status of 'canceled' or 'closed'
        if order['status'] not in ('canceled', 'closed'):
            corder = self.exchange.cancel_order_with_result(trade.open_order_id, trade.pair,
                                                            trade.amount)
            # Avoid race condition where the order could not be cancelled coz its already filled.
            # Simply bailing here is the only safe way - as this order will then be
            # handled in the next iteration.
            if corder.get('status') not in ('canceled', 'closed'):
                logger.warning(f"Order {trade.open_order_id} for {trade.pair} not cancelled.")
                return False
        else:
            # Order was cancelled already, so we can reuse the existing dict
            corder = order
            reason = constants.CANCEL_REASON['CANCELLED_ON_EXCHANGE']

        logger.info('Buy order %s for %s.', reason, trade)

        # Using filled to determine the filled amount
        filled_amount = safe_value_fallback2(corder, order, 'filled', 'filled')
        if isclose(filled_amount, 0.0, abs_tol=constants.MATH_CLOSE_PREC):
            logger.info('Buy order fully cancelled. Removing %s from database.', trade)
            # if trade is not partially completed, just delete the trade
            trade.delete()
            was_trade_fully_canceled = True
            reason += f", {constants.CANCEL_REASON['FULLY_CANCELLED']}"
        else:
            # if trade is partially complete, edit the stake details for the trade
            # and close the order
            # cancel_order may not contain the full order dict, so we need to fallback
            # to the order dict aquired before cancelling.
            # we need to fall back to the values from order if corder does not contain these keys.
            trade.amount = filled_amount
            trade.stake_amount = trade.amount * trade.open_rate
            self.update_trade_state(trade, trade.open_order_id, corder)

            trade.open_order_id = None
            logger.info('Partial buy order timeout for %s.', trade)
            reason += f", {constants.CANCEL_REASON['PARTIALLY_FILLED']}"

        self.wallets.update()
        self._notify_buy_cancel(trade, order_type=self.strategy.order_types['buy'],
                                reason=reason)
        return was_trade_fully_canceled

    def handle_cancel_sell(self, trade: Trade, order: Dict, reason: str) -> str:
        """
        Sell cancel - cancel order and update trade
        :return: Reason for cancel
        """
        # if trade is not partially completed, just cancel the order
        if order['remaining'] == order['amount'] or order.get('filled') == 0.0:
            if not self.exchange.check_order_canceled_empty(order):
                try:
                    # if trade is not partially completed, just delete the order
                    self.exchange.cancel_order(trade.open_order_id, trade.pair)
                except InvalidOrderException:
                    logger.exception(f"Could not cancel sell order {trade.open_order_id}")
                    return 'error cancelling order'
                logger.info('Sell order %s for %s.', reason, trade)
            else:
                reason = constants.CANCEL_REASON['CANCELLED_ON_EXCHANGE']
                logger.info('Sell order %s for %s.', reason, trade)

            trade.close_rate = None
            trade.close_rate_requested = None
            trade.close_profit = None
            trade.close_profit_abs = None
            trade.close_date = None
            trade.is_open = True
            trade.open_order_id = None
        else:
            # TODO: figure out how to handle partially complete sell orders
            reason = constants.CANCEL_REASON['PARTIALLY_FILLED_KEEP_OPEN']

        self.wallets.update()
        self._notify_sell_cancel(
            trade,
            order_type=self.strategy.order_types['sell'],
            reason=reason
        )
        return reason

    def _safe_sell_amount(self, pair: str, amount: float) -> float:
        """
        Get sellable amount.
        Should be trade.amount - but will fall back to the available amount if necessary.
        This should cover cases where get_real_amount() was not able to update the amount
        for whatever reason.
        :param pair: Pair we're trying to sell
        :param amount: amount we expect to be available
        :return: amount to sell
        :raise: DependencyException: if available balance is not within 2% of the available amount.
        """
        # Update wallets to ensure amounts tied up in a stoploss is now free!
        self.wallets.update()
        trade_base_currency = self.exchange.get_pair_base_currency(pair)
        wallet_amount = self.wallets.get_free(trade_base_currency)
        logger.debug(f"{pair} - Wallet: {wallet_amount} - Trade-amount: {amount}")
        if wallet_amount >= amount:
            return amount
        elif wallet_amount > amount * 0.98:
            logger.info(f"{pair} - Falling back to wallet-amount {wallet_amount} -> {amount}.")
            return wallet_amount
        else:
            raise DependencyException(
                f"Not enough amount to sell. Trade-amount: {amount}, Wallet: {wallet_amount}")

    def execute_sell(self, trade: Trade, limit: float, sell_reason: SellType) -> bool:
        """
        Executes a limit sell for the given trade and limit
        :param trade: Trade instance
        :param limit: limit rate for the sell order
        :param sellreason: Reason the sell was triggered
        :return: True if it succeeds (supported) False (not supported)
        """
        sell_type = 'sell'
        if sell_reason in (SellType.STOP_LOSS, SellType.TRAILING_STOP_LOSS):
            sell_type = 'stoploss'

        # if stoploss is on exchange and we are on dry_run mode,
        # we consider the sell price stop price
        if self.config['dry_run'] and sell_type == 'stoploss' \
           and self.strategy.order_types['stoploss_on_exchange']:
            limit = trade.stop_loss

        # First cancelling stoploss on exchange ...
        if self.strategy.order_types.get('stoploss_on_exchange') and trade.stoploss_order_id:
            try:
                self.exchange.cancel_stoploss_order(trade.stoploss_order_id, trade.pair)
            except InvalidOrderException:
                logger.exception(f"Could not cancel stoploss order {trade.stoploss_order_id}")

        order_type = self.strategy.order_types[sell_type]
        if sell_reason == SellType.EMERGENCY_SELL:
            # Emergency sells (default to market!)
            order_type = self.strategy.order_types.get("emergencysell", "market")

        amount = self._safe_sell_amount(trade.pair, trade.amount)
        time_in_force = self.strategy.order_time_in_force['sell']

        if not strategy_safe_wrapper(self.strategy.confirm_trade_exit, default_retval=True)(
                pair=trade.pair, trade=trade, order_type=order_type, amount=amount, rate=limit,
                time_in_force=time_in_force,
                sell_reason=sell_reason.value):
            logger.info(f"User requested abortion of selling {trade.pair}")
            return False

        try:
            # Execute sell and update trade record
            order = self.exchange.sell(pair=trade.pair,
                                       ordertype=order_type,
                                       amount=amount, rate=limit,
                                       time_in_force=time_in_force
                                       )
        except InsufficientFundsError as e:
            logger.warning(f"Unable to place order {e}.")
            # Try to figure out what went wrong
            self.handle_insufficient_funds(trade)
            return False

        order_obj = Order.parse_from_ccxt_object(order, trade.pair, 'sell')
        trade.orders.append(order_obj)

        trade.open_order_id = order['id']
        trade.close_rate_requested = limit
        trade.sell_reason = sell_reason.value
        # In case of market sell orders the order can be closed immediately
        if order.get('status', 'unknown') == 'closed':
            self.update_trade_state(trade, trade.open_order_id, order)
        Trade.session.flush()

        # Lock pair for one candle to prevent immediate rebuys
        self.strategy.lock_pair(trade.pair, datetime.now(timezone.utc),
                                reason='Auto lock')

        self._notify_sell(trade, order_type)

        return True

    def _notify_sell(self, trade: Trade, order_type: str) -> None:
        """
        Sends rpc notification when a sell occured.
        """
        profit_rate = trade.close_rate if trade.close_rate else trade.close_rate_requested
        profit_trade = trade.calc_profit(rate=profit_rate)
        # Use cached rates here - it was updated seconds ago.
        current_rate = self.get_sell_rate(trade.pair, False)
        profit_ratio = trade.calc_profit_ratio(profit_rate)
        gain = "profit" if profit_ratio > 0 else "loss"

        msg = {
            'type': RPCMessageType.SELL_NOTIFICATION,
            'trade_id': trade.id,
            'exchange': trade.exchange.capitalize(),
            'pair': trade.pair,
            'gain': gain,
            'limit': profit_rate,
            'order_type': order_type,
            'amount': trade.amount,
            'open_rate': trade.open_rate,
            'current_rate': current_rate,
            'profit_amount': profit_trade,
            'profit_ratio': profit_ratio,
            'sell_reason': trade.sell_reason,
            'open_date': trade.open_date,
            'close_date': trade.close_date or datetime.utcnow(),
            'stake_currency': self.config['stake_currency'],
            'fiat_currency': self.config.get('fiat_display_currency', None),
        }

        if 'fiat_display_currency' in self.config:
            msg.update({
                'fiat_currency': self.config['fiat_display_currency'],
            })

        # Send the message
        self.rpc.send_msg(msg)

    def _notify_sell_cancel(self, trade: Trade, order_type: str, reason: str) -> None:
        """
        Sends rpc notification when a sell cancel occured.
        """
        if trade.sell_order_status == reason:
            return
        else:
            trade.sell_order_status = reason

        profit_rate = trade.close_rate if trade.close_rate else trade.close_rate_requested
        profit_trade = trade.calc_profit(rate=profit_rate)
        current_rate = self.get_sell_rate(trade.pair, False)
        profit_ratio = trade.calc_profit_ratio(profit_rate)
        gain = "profit" if profit_ratio > 0 else "loss"

        msg = {
            'type': RPCMessageType.SELL_CANCEL_NOTIFICATION,
            'trade_id': trade.id,
            'exchange': trade.exchange.capitalize(),
            'pair': trade.pair,
            'gain': gain,
            'limit': profit_rate,
            'order_type': order_type,
            'amount': trade.amount,
            'open_rate': trade.open_rate,
            'current_rate': current_rate,
            'profit_amount': profit_trade,
            'profit_ratio': profit_ratio,
            'sell_reason': trade.sell_reason,
            'open_date': trade.open_date,
            'close_date': trade.close_date,
            'stake_currency': self.config['stake_currency'],
            'fiat_currency': self.config.get('fiat_display_currency', None),
            'reason': reason,
        }

        if 'fiat_display_currency' in self.config:
            msg.update({
                'fiat_currency': self.config['fiat_display_currency'],
            })

        # Send the message
        self.rpc.send_msg(msg)

#
# Common update trade state methods
#

    def update_trade_state(self, trade: Trade, order_id: str, action_order: Dict[str, Any] = None,
                           stoploss_order: bool = False) -> bool:
        """
        Checks trades with open orders and updates the amount if necessary
        Handles closing both buy and sell orders.
        :param trade: Trade object of the trade we're analyzing
        :param order_id: Order-id of the order we're analyzing
        :param action_order: Already aquired order object
        :return: True if order has been cancelled without being filled partially, False otherwise
        """
        if not order_id:
            logger.warning(f'Orderid for trade {trade} is empty.')
            return False

        # Update trade with order values
        logger.info('Found open order for %s', trade)
        try:
            order = action_order or self.exchange.fetch_order_or_stoploss_order(order_id,
                                                                                trade.pair,
                                                                                stoploss_order)
        except InvalidOrderException as exception:
            logger.warning('Unable to fetch order %s: %s', order_id, exception)
            return False

        trade.update_order(order)

        # Try update amount (binance-fix)
        try:
            new_amount = self.get_real_amount(trade, order)
            if not isclose(safe_value_fallback(order, 'filled', 'amount'), new_amount,
                           abs_tol=constants.MATH_CLOSE_PREC):
                order['amount'] = new_amount
                order.pop('filled', None)
                trade.recalc_open_trade_value()
        except DependencyException as exception:
            logger.warning("Could not update trade amount: %s", exception)

        if self.exchange.check_order_canceled_empty(order):
            # Trade has been cancelled on exchange
            # Handling of this will happen in check_handle_timeout.
            return True
        trade.update(order)

        # Updating wallets when order is closed
        if not trade.is_open:
            self.protections.stop_per_pair(trade.pair)
            self.protections.global_stop()
            self.wallets.update()
        return False

    def apply_fee_conditional(self, trade: Trade, trade_base_currency: str,
                              amount: float, fee_abs: float) -> float:
        """
        Applies the fee to amount (either from Order or from Trades).
        Can eat into dust if more than the required asset is available.
        """
        self.wallets.update()
        if fee_abs != 0 and self.wallets.get_free(trade_base_currency) >= amount:
            # Eat into dust if we own more than base currency
            logger.info(f"Fee amount for {trade} was in base currency - "
                        f"Eating Fee {fee_abs} into dust.")
        elif fee_abs != 0:
            real_amount = self.exchange.amount_to_precision(trade.pair, amount - fee_abs)
            logger.info(f"Applying fee on amount for {trade} "
                        f"(from {amount} to {real_amount}).")
            return real_amount
        return amount

    def get_real_amount(self, trade: Trade, order: Dict) -> float:
        """
        Detect and update trade fee.
        Calls trade.update_fee() uppon correct detection.
        Returns modified amount if the fee was taken from the destination currency.
        Necessary for exchanges which charge fees in base currency (e.g. binance)
        :return: identical (or new) amount for the trade
        """
        # Init variables
        order_amount = safe_value_fallback(order, 'filled', 'amount')
        # Only run for closed orders
        if trade.fee_updated(order.get('side', '')) or order['status'] == 'open':
            return order_amount

        trade_base_currency = self.exchange.get_pair_base_currency(trade.pair)
        # use fee from order-dict if possible
        if self.exchange.order_has_fee(order):
            fee_cost, fee_currency, fee_rate = self.exchange.extract_cost_curr_rate(order)
            logger.info(f"Fee for Trade {trade} [{order.get('side')}]: "
                        f"{fee_cost:.8g} {fee_currency} - rate: {fee_rate}")
            if fee_rate is None or fee_rate < 0.02:
                # Reject all fees that report as > 2%.
                # These are most likely caused by a parsing bug in ccxt
                # due to multiple trades (https://github.com/ccxt/ccxt/issues/8025)
                trade.update_fee(fee_cost, fee_currency, fee_rate, order.get('side', ''))
                if trade_base_currency == fee_currency:
                    # Apply fee to amount
                    return self.apply_fee_conditional(trade, trade_base_currency,
                                                      amount=order_amount, fee_abs=fee_cost)
                return order_amount
        return self.fee_detection_from_trades(trade, order, order_amount)

    def fee_detection_from_trades(self, trade: Trade, order: Dict, order_amount: float) -> float:
        """
        fee-detection fallback to Trades. Parses result of fetch_my_trades to get correct fee.
        """
        trades = self.exchange.get_trades_for_order(order['id'], trade.pair,
                                                    trade.open_date)

        if len(trades) == 0:
            logger.info("Applying fee on amount for %s failed: myTrade-Dict empty found", trade)
            return order_amount
        fee_currency = None
        amount = 0
        fee_abs = 0.0
        fee_cost = 0.0
        trade_base_currency = self.exchange.get_pair_base_currency(trade.pair)
        fee_rate_array: List[float] = []
        for exectrade in trades:
            amount += exectrade['amount']
            if self.exchange.order_has_fee(exectrade):
                fee_cost_, fee_currency, fee_rate_ = self.exchange.extract_cost_curr_rate(exectrade)
                fee_cost += fee_cost_
                if fee_rate_ is not None:
                    fee_rate_array.append(fee_rate_)
                # only applies if fee is in quote currency!
                if trade_base_currency == fee_currency:
                    fee_abs += fee_cost_
        # Ensure at least one trade was found:
        if fee_currency:
            # fee_rate should use mean
            fee_rate = sum(fee_rate_array) / float(len(fee_rate_array)) if fee_rate_array else None
            trade.update_fee(fee_cost, fee_currency, fee_rate, order.get('side', ''))

        if not isclose(amount, order_amount, abs_tol=constants.MATH_CLOSE_PREC):
            logger.warning(f"Amount {amount} does not match amount {trade.amount}")
            raise DependencyException("Half bought? Amounts don't match")

        if fee_abs != 0:
            return self.apply_fee_conditional(trade, trade_base_currency,
                                              amount=amount, fee_abs=fee_abs)
        else:
            return amount
