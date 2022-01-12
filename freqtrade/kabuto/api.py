"""
So far this is a nameless API to a stock market.
Based on ccxt/base/exchange.py
"""
# eddsa signing
import numpy as np

from freqtrade.kabuto.kabusapi import fetch_order_book

try:
    import axolotl_curve25519 as eddsa
except ImportError:
    eddsa = None


# -----------------------------------------------------------------------------

from ccxt.base.decimal_to_precision import decimal_to_precision
from ccxt.base.decimal_to_precision import DECIMAL_PLACES, NO_PADDING, TRUNCATE, ROUND, ROUND_UP, ROUND_DOWN
from ccxt.base.decimal_to_precision import number_to_string
from ccxt.base.precise import Precise

# -----------------------------------------------------------------------------

__all__ = [
    'API',
]

# -----------------------------------------------------------------------------

# Python 2 & 3
import types
import logging
import base64
import calendar
import collections
import datetime
from email.utils import parsedate
import functools
import gzip
import hashlib
import hmac
import io
import json
import math
import random
from numbers import Number
import re
from requests import Session
from requests.utils import default_user_agent
from requests.exceptions import HTTPError, Timeout, TooManyRedirects, RequestException, ConnectionError as requestsConnectionError
# import socket
from ssl import SSLError
# import sys
import time
import uuid
import zlib
from decimal import Decimal
from time import mktime
from wsgiref.handlers import format_date_time

# -----------------------------------------------------------------------------

try:
    basestring  # basestring was removed in Python 3
except NameError:
    basestring = str

try:
    long  # long integer was removed in Python 3
except NameError:
    long = int

# -----------------------------------------------------------------------------

try:
    import urllib.parse as _urlencode    # Python 3
except ImportError:
    import urllib as _urlencode          # Python 2


class API(object):
    """Base exchange class"""
    id = None
    name = None
    version = None
    certified = False  # if certified by the CCXT dev team
    pro = False  # if it is integrated with CCXT Pro for WebSocket support
    alias = False  # whether this exchange is an alias to another exchange
    # rate limiter settings
    enableRateLimit = True
    rateLimit = 2000  # milliseconds = seconds * 1000
    timeout = 10000  # milliseconds = seconds * 1000
    asyncio_loop = None
    aiohttp_proxy = None
    aiohttp_trust_env = False
    session = None  # Session () by default
    verify = True  # SSL verification
    logger = None  # logging.getLogger(__name__) by default
    userAgent = None
    userAgents = {
        'chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
        'chrome39': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
    }
    verbose = False
    markets = None
    symbols = None
    codes = None
    timeframes = None
    fees = {
        'trading': {
            'percentage': True,  # subclasses should rarely have to redefine this
        },
        'funding': {
            'withdraw': {},
            'deposit': {},
        },
    }
    loaded_fees = {
        'trading': {
            'percentage': True,
        },
        'funding': {
            'withdraw': {},
            'deposit': {},
        },
    }
    ids = None
    urls = None
    api = None
    parseJsonResponse = True
    proxy = ''
    origin = '*'  # CORS origin
    proxies = None
    hostname = None  # in case of inaccessibility of the "main" domain
    apiKey = ''
    secret = ''
    password = ''
    uid = ''
    privateKey = ''  # a "0x"-prefixed hexstring private key for a wallet
    walletAddress = ''  # the wallet address "0x"-prefixed hexstring
    token = ''  # reserved for HTTP auth in some cases
    twofa = None
    markets_by_id = None
    currencies_by_id = None
    precision = None
    exceptions = None
    limits = {
        'amount': {
            'min': None,
            'max': None,
        },
        'price': {
            'min': None,
            'max': None,
        },
        'cost': {
            'min': None,
            'max': None,
        },
    }

    headers = None
    balance = None
    orderbooks = None
    orders = None
    myTrades = None
    trades = None
    transactions = None
    ohlcvs = None
    tickers = None
    base_currencies = None
    quote_currencies = None
    currencies = None
    options = None  # Python does not allow to define properties in run-time with setattr
    accounts = None
    positions = None

    status = {
        'status': 'ok',
        'updated': None,
        'eta': None,
        'url': None,
    }

    requiredCredentials = {
        'apiKey': True,
        'secret': True,
        'uid': False,
        'login': False,
        'password': False,
        'twofa': False,  # 2-factor authentication (one-time password key)
        'privateKey': False,  # a "0x"-prefixed hexstring private key for a wallet
        'walletAddress': False,  # the wallet address "0x"-prefixed hexstring
        'token': False,  # reserved for HTTP auth in some cases
    }

    # API method metainfo
    has = {
        'loadMarkets': True,
        'cancelAllOrders': False,
        'cancelOrder': True,
        'cancelOrders': False,
        'CORS': False,
        'createDepositAddress': False,
        'createLimitOrder': True,
        'createMarketOrder': True,
        'createOrder': True,
        'deposit': False,
        'editOrder': 'emulated',
        'fetchBalance': True,
        'fetchClosedOrders': False,
        'fetchCurrencies': False,
        'fetchDepositAddress': False,
        'fetchDeposits': False,
        'fetchL2OrderBook': True,
        'fetchLedger': False,
        'fetchMarkets': True,
        'fetchMyTrades': False,
        'fetchOHLCV': 'emulated',
        'fetchOpenOrders': False,
        'fetchOrder': False,
        'fetchOrderBook': True,
        'fetchOrderBooks': False,
        'fetchOrders': False,
        'fetchOrderTrades': False,
        'fetchStatus': 'emulated',
        'fetchTicker': True,
        'fetchTickers': False,
        'fetchTime': False,
        'fetchTrades': True,
        'fetchTradingFee': False,
        'fetchTradingFees': False,
        'fetchFundingFee': False,
        'fetchFundingFees': False,
        'fetchTradingLimits': False,
        'fetchTransactions': False,
        'fetchWithdrawals': False,
        'privateAPI': True,
        'publicAPI': True,
        'signIn': False,
        'withdraw': False,
    }
    precisionMode = DECIMAL_PLACES
    paddingMode = NO_PADDING
    minFundingAddressLength = 1  # used in check_address
    substituteCommonCurrencyCodes = True
    quoteJsonNumbers = True
    number = float  # or str (a pointer to a class)
    # whether fees should be summed by currency code
    reduceFees = True
    lastRestRequestTimestamp = 0
    lastRestPollTimestamp = 0
    restRequestQueue = None
    restPollerLoopIsRunning = False
    rateLimitTokens = 16
    rateLimitMaxTokens = 16
    rateLimitUpdateTime = 0
    enableLastHttpResponse = True
    enableLastJsonResponse = True
    enableLastResponseHeaders = True
    last_http_response = None
    last_json_response = None
    last_response_headers = None

    requiresEddsa = False
    base58_encoder = None
    base58_decoder = None
    # no lower case l or upper case I, O
    base58_alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

    commonCurrencies = {
        'XBT': 'BTC',
        'BCC': 'BCH',
        'DRK': 'DASH',
        'BCHABC': 'BCH',
        'BCHSV': 'BSV',
    }

    def __init__(self, config={}):
        self.id = "kabus"
        self.name = "KabuStation"
        self.version = "v0"
        self.certified = False  # if certified by the CCXT dev team
        self.pro = False  # if it is integrated with CCXT Pro for WebSocket support
        self.alias = False  # whether this exchange is an alias to another exchange
        # rate limiter settings
        self.enableRateLimit = True
        self.rateLimit = 2000  # milliseconds = seconds * 1000
        self.timeout = 10000  # milliseconds = seconds * 1000
        self.asyncio_loop = None
        self.aiohttp_proxy = None
        self.aiohttp_trust_env = False
        self.session = None  # Session () by default
        self.verify = True  # SSL verification
        self.logger = None  # logging.getLogger(__name__) by default
        self.userAgent = None
        self.userAgents = {
            'chrome': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.94 Safari/537.36',
            'chrome39': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        }
        self.verbose = False
        self.markets = None
        self.symbols = None
        self.codes = None
        self.timeframes = {
                '1m': 'MINUTE_1',
                '5m': 'MINUTE_5',
                '1h': 'HOUR_1',
                '1d': 'DAY_1',
        }
        self.fees = {
            'trading': {
                'percentage': True,  # subclasses should rarely have to redefine this
            },
            'funding': {
                'withdraw': {},
                'deposit': {},
            },
        }
        self.loaded_fees = {
            'trading': {
                'percentage': True,
            },
            'funding': {
                'withdraw': {},
                'deposit': {},
            },
        }
        self.ids = None
        self.urls = None
        self.api = None
        self.parseJsonResponse = True
        self.proxy = ''
        self.origin = '*'  # CORS origin
        self.proxies = None
        self.hostname = None  # in case of inaccessibility of the "main" domain
        self.apiKey = ''
        self.secret = ''
        self.password = ''
        self.uid = ''
        self.privateKey = ''  # a "0x"-prefixed hexstring private key for a wallet
        self.walletAddress = ''  # the wallet address "0x"-prefixed hexstring
        self.token = ''  # reserved for HTTP auth in some cases
        self.twofa = None
        self.markets_by_id = None
        self.currencies_by_id = None
        # NOTE: This probably means how many floating each values can take
        self.precision = {
            'amount': 0,
            'price': 0,
            'cost': 0
        }
        self.exceptions = None
        self.limits = {
            'amount': {
                'min': None,
                'max': None,
            },
            'price': {
                'min': None,
                'max': None,
            },
            'cost': {
                'min': None,
                'max': None,
            },
        }
        self.httpExceptions = {}
        self.headers = None
        self.balance = None
        self.orderbooks = None
        self.orders = None
        self.myTrades = None
        self.trades = None
        self.transactions = None
        self.ohlcvs = None
        self.tickers = None
        self.base_currencies = None
        self.quote_currencies = None
        self.currencies = None
        self.options = None  # Python does not allow to define properties in run-time with setattr
        self.accounts = None
        self.positions = None

        self.status = {
            'status': 'ok',
            'updated': None,
            'eta': None,
            'url': None,
        }

        self.requiredCredentials = {
            'apiKey': True,
            'secret': True,
            'uid': False,
            'login': False,
            'password': False,
            'twofa': False,  # 2-factor authentication (one-time password key)
            'privateKey': False,  # a "0x"-prefixed hexstring private key for a wallet
            'walletAddress': False,  # the wallet address "0x"-prefixed hexstring
            'token': False,  # reserved for HTTP auth in some cases
        }

        # API method metainfo
        self.has = {
            'loadMarkets': True,
            'cancelAllOrders': False,
            'cancelOrder': True,
            'cancelOrders': False,
            'CORS': False,
            'createDepositAddress': False,
            'createLimitOrder': True,
            'createMarketOrder': True,
            'createOrder': True,
            'deposit': False,
            'editOrder': 'emulated',
            'fetchBalance': True,
            'fetchClosedOrders': False,
            'fetchCurrencies': False,
            'fetchDepositAddress': False,
            'fetchDeposits': False,
            'fetchL2OrderBook': True,
            'fetchLedger': False,
            'fetchMarkets': True,
            'fetchMyTrades': False,
            'fetchOHLCV': 'emulated',
            'fetchOpenOrders': False,
            'fetchOrder': False,
            'fetchOrderBook': True,
            'fetchOrderBooks': False,
            'fetchOrders': False,
            'fetchOrderTrades': False,
            'fetchStatus': 'emulated',
            'fetchTicker': True,
            'fetchTickers': False,
            'fetchTime': False,
            'fetchTrades': True,
            'fetchTradingFee': False,
            'fetchTradingFees': False,
            'fetchFundingFee': False,
            'fetchFundingFees': False,
            'fetchTradingLimits': False,
            'fetchTransactions': False,
            'fetchWithdrawals': False,
            'privateAPI': True,
            'publicAPI': True,
            'signIn': False,
            'withdraw': False,
        }
        # precisionMode = DECIMAL_PLACES
        # paddingMode = NO_PADDING
        self.minFundingAddressLength = 1  # used in check_address
        self.substituteCommonCurrencyCodes = True
        self.quoteJsonNumbers = True
        self.number = float  # or str (a pointer to a class)
        # whether fees should be summed by currency code
        self.reduceFees = True
        self.lastRestRequestTimestamp = 0
        self.lastRestPollTimestamp = 0
        self.restRequestQueue = None
        self.restPollerLoopIsRunning = False
        self.rateLimitTokens = 16
        self.rateLimitMaxTokens = 16
        self.rateLimitUpdateTime = 0
        self.enableLastHttpResponse = True
        self.enableLastJsonResponse = True
        self.enableLastResponseHeaders = True
        self.last_http_response = None
        self.last_json_response = None
        self.last_response_headers = None

        self.requiresEddsa = False
        self.base58_encoder = None
        self.base58_decoder = None
        # no lower case l or upper case I, O
        self.base58_alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

        self.commonCurrencies = {
            'XBT': 'BTC',
            'BCC': 'BCH',
            'DRK': 'DASH',
            'BCHABC': 'BCH',
            'BCHSV': 'BSV',
        }

        self.precision = dict() if self.precision is None else self.precision
        self.limits = dict() if self.limits is None else self.limits
        self.exceptions = dict() if self.exceptions is None else self.exceptions
        self.headers = dict() if self.headers is None else self.headers
        self.balance = dict() if self.balance is None else self.balance
        self.orderbooks = dict() if self.orderbooks is None else self.orderbooks
        self.tickers = dict() if self.tickers is None else self.tickers
        self.trades = dict() if self.trades is None else self.trades
        self.transactions = dict() if self.transactions is None else self.transactions
        self.positions = dict() if self.positions is None else self.positions
        self.ohlcvs = dict() if self.ohlcvs is None else self.ohlcvs
        self.currencies = dict() if self.currencies is None else self.currencies
        self.options = dict() if self.options is None else self.options  # Python does not allow to define properties in run-time with setattr
        self.decimal_to_precision = decimal_to_precision
        self.number_to_string = number_to_string

        # version = '.'.join(map(str, sys.version_info[:3]))
        # self.userAgent = {
        #     'User-Agent': 'ccxt/' + __version__ + ' (+https://github.com/ccxt/ccxt) Python/' + version
        # }

        self.origin = self.uuid()
        self.userAgent = default_user_agent()

        settings = self.deep_extend(self.describe(), config)

        for key in settings:
            if hasattr(self, key) and isinstance(getattr(self, key), dict):
                setattr(self, key, self.deep_extend(getattr(self, key), settings[key]))
            else:
                setattr(self, key, settings[key])

        if self.api:
            self.define_rest_api(self.api, 'request')

        if self.markets:
            self.set_markets(self.markets)

        # convert all properties from underscore notation foo_bar to camelcase notation fooBar
        cls = type(self)
        for name in dir(self):
            if name[0] != '_' and name[-1] != '_' and '_' in name:
                parts = name.split('_')
                # fetch_ohlcv → fetchOHLCV (not fetchOhlcv!)
                exceptions = {'ohlcv': 'OHLCV', 'le': 'LE', 'be': 'BE'}
                camelcase = parts[0] + ''.join(
                    exceptions.get(i, self.capitalize(i)) for i in parts[1:])
                attr = getattr(self, name)
                if isinstance(attr, types.MethodType):
                    setattr(cls, camelcase, getattr(cls, name))
                else:
                    setattr(self, camelcase, attr)

        self.tokenBucket = self.extend({
            'refillRate': 1.0 / self.rateLimit if self.rateLimit > 0 else float('inf'),
            'delay': 0.001,
            'capacity': 1.0,
            'defaultCost': 1.0,
        }, getattr(self, 'tokenBucket', {}))

        self.session = self.session if self.session or self.asyncio_loop else Session()
        self.logger = self.logger if self.logger else logging.getLogger(__name__)

        self.dummy_l2_order_book = None
        self.kabuto_config = config['kabuto']

    def describe(self):
        return {}

    def load_markets(self, reload=False, params={}):
        if not reload:
            if self.markets:
                if not self.markets_by_id:
                    return self.set_markets(self.markets)
                return self.markets
        currencies = None
        if self.has['fetchCurrencies']:
            currencies = self.fetch_currencies()
        markets = self.fetch_markets(params)
        return self.set_markets(markets, currencies)

    def set_markets(self, markets, currencies=None):
        """
        Market example
        {'ETC/BTH':
            {'percentage': True,
             'feeSide': 'get',
             'tierBased': False,
             'taker': 0.001,
             'maker': 0.001,
             'precision': {'base': 8, 'quote': 8, 'amount': 2, 'price': 6},
             'limits': {'amount': {'min': 0.01, 'max': 90000000.0},
              'price': {'min': 1e-06, 'max': 1000.0},
              'cost': {'min': 0.0001, 'max': None},
              'market': {'min': 0.0, 'max': 7150.68052119}},
             'id': 'ETCBTC',
             'lowercaseId': 'etcbtc',
             'symbol': 'ETC/BTC',
             'base': 'ETC',
             'quote': 'BTC',
             'baseId': 'ETC',
             'quoteId': 'BTC',
             'info': {'symbol': 'ETCBTC',
              'status': 'TRADING',
              'baseAsset': 'ETC',
              'baseAssetPrecision': '8',
              'quoteAsset': 'BTC',
              'quotePrecision': '8',
              'quoteAssetPrecision': '8',
              'baseCommissionPrecision': '8',
              'quoteCommissionPrecision': '8',
              'orderTypes': ['LIMIT',
               'LIMIT_MAKER',
               'MARKET',
               'STOP_LOSS_LIMIT',
               'TAKE_PROFIT_LIMIT'],
              'icebergAllowed': True,
              'ocoAllowed': True,
              'quoteOrderQtyMarketAllowed': True,
              'isSpotTradingAllowed': True,
              'isMarginTradingAllowed': True,
              'filters': [{'filterType': 'PRICE_FILTER',
                'minPrice': '0.00000100',
                'maxPrice': '1000.00000000',
                'tickSize': '0.00000100'},
               {'filterType': 'PERCENT_PRICE',
                'multiplierUp': '5',
                'multiplierDown': '0.2',
                'avgPriceMins': '5'},
               {'filterType': 'LOT_SIZE',
                'minQty': '0.01000000',
                'maxQty': '90000000.00000000',
                'stepSize': '0.01000000'},
               {'filterType': 'MIN_NOTIONAL',
                'minNotional': '0.00010000',
                'applyToMarket': True,
                'avgPriceMins': '5'},
               {'filterType': 'ICEBERG_PARTS', 'limit': '10'},
               {'filterType': 'MARKET_LOT_SIZE',
                'minQty': '0.00000000',
                'maxQty': '7150.68052119',
                'stepSize': '0.00000000'},
               {'filterType': 'MAX_NUM_ORDERS', 'maxNumOrders': '200'},
               {'filterType': 'MAX_NUM_ALGO_ORDERS', 'maxNumAlgoOrders': '5'}],
              'permissions': ['SPOT', 'MARGIN']},
             'spot': True,
             'type': 'spot',
             'margin': True,
             'future': False,
             'delivery': False,
             'linear': False,
             'inverse': False,
             'expiry': None,
             'expiryDatetime': None,
             'active': True,
             'contractSize': None}
        }
        """
        values = list(markets.values()) if type(markets) is dict else markets
        for i in range(0, len(values)):
            values[i] = self.extend(
                self.fees['trading'],
                {'precision': self.precision, 'limits': self.limits},
                values[i]
            )
        # Array of markets to a dict of markets indexed by symbols
        self.markets = self.index_by(values, 'symbol')
        self.markets_by_id = self.index_by(values, 'id')
        self.symbols = sorted(self.markets.keys())
        self.ids = sorted(self.markets_by_id.keys())

        return self.markets
    
    def calculate_fee(self, symbol, type, side, amount, price, takerOrMaker='taker', params={}):
        market = self.markets[symbol]
        feeSide = self.safe_string(market, 'feeSide', 'quote')
        key = 'quote'
        cost = None
        if feeSide == 'quote':
            # the fee is always in quote currency
            cost = amount * price
        elif feeSide == 'base':
            # the fee is always in base currency
            cost = amount
        elif feeSide == 'get':
            # the fee is always in the currency you get
            cost = amount
            if side == 'sell':
                cost *= price
            else:
                key = 'base'
        elif feeSide == 'give':
            # the fee is always in the currency you give
            cost = amount
            if side == 'buy':
                cost *= price
            else:
                key = 'base'
        rate = market[takerOrMaker]
        if cost is not None:
            cost *= rate
        return {
            'type': takerOrMaker,
            'currency': market[key],
            'rate': rate,
            'cost': cost,
        }
    
    def parse_number(self, value, default=None):
        if value is None:
            return default
        else:
            try:
                return self.number(value)
            except Exception:
                return default

    def build_ohlcvc(self, trades, timeframe='1m', since=None, limit=None):
        ms = self.parse_timeframe(timeframe) * 1000
        ohlcvs = []
        (timestamp, open, high, low, close, volume, count) = (0, 1, 2, 3, 4, 5, 6)
        num_trades = len(trades)
        oldest = (num_trades - 1) if limit is None else min(num_trades - 1, limit)
        for i in range(0, oldest):
            trade = trades[i]
            if (since is not None) and (trade['timestamp'] < since):
                continue
            opening_time = int(math.floor(trade['timestamp'] / ms) * ms)  # Shift the edge of the m/h/d (but not M)
            j = len(ohlcvs)
            candle = j - 1
            if (j == 0) or opening_time >= ohlcvs[candle][timestamp] + ms:
                # moved to a new timeframe -> create a new candle from opening trade
                ohlcvs.append([
                    opening_time,
                    trade['price'],
                    trade['price'],
                    trade['price'],
                    trade['price'],
                    trade['amount'],
                    1,  # count
                ])
            else:
                # still processing the same timeframe -> update opening trade
                ohlcvs[candle][high] = max(ohlcvs[candle][high], trade['price'])
                ohlcvs[candle][low] = min(ohlcvs[candle][low], trade['price'])
                ohlcvs[candle][close] = trade['price']
                ohlcvs[candle][volume] += trade['amount']
                ohlcvs[candle][count] += 1
        return ohlcvs

    def fetch_l2_order_book(self, symbol, limit=None, params={}):
        orderbook = self.fetch_order_book(symbol, limit, params)
        return self.extend(orderbook, {
            'bids': self.sort_by(self.aggregate(orderbook['bids']), 0, True),
            'asks': self.sort_by(self.aggregate(orderbook['asks']), 0),
        })

    def fetch_l2_order_book_dummy(self, symbol, last_price, limit=None, params={}):
        # Return l2 order book to align with the real fetching method
        if not self.dummy_l2_order_book or \
                (time.time() - self.dummy_l2_order_book['timestamp'] > 20):
            self.dummy_l2_order_book = {
                'symbol': symbol,
                'bids': [[last_price - i, np.random.randint(10000, 20000)] for i in range(1, 5)],
                'asks': [[last_price + i, np.random.randint(10000, 20000)] for i in range(1, 5)],
                'timestamp': time.time(),
                'datetime': None,
                'nonce': np.random.randint(1000000, 2000000)
            }

        return self.dummy_l2_order_book

    @staticmethod
    def parse_timeframe(timeframe):
        amount = int(timeframe[0:-1])
        unit = timeframe[-1]
        if 'y' == unit:
            scale = 60 * 60 * 24 * 365
        elif 'M' == unit:
            scale = 60 * 60 * 24 * 30
        elif 'w' == unit:
            scale = 60 * 60 * 24 * 7
        elif 'd' == unit:
            scale = 60 * 60 * 24
        elif 'h' == unit:
            scale = 60 * 60
        elif 'm' == unit:
            scale = 60
        elif 's' == unit:
            scale = 1
        else:
            raise NotSupported('timeframe unit {} is not supported'.format(unit))
        return amount * scale


    def cost_to_precision(self, symbol, cost):
        # return ccxt.decimal_to_precision(cost, TRUNCATE, self.markets[symbol]['precision']['price'], DECIMAL_PLACES)
        return None

    def fee_to_precision(self, symbol, fee):
        # return ccxt.decimal_to_precision(fee, TRUNCATE, self.markets[symbol]['precision']['price'], DECIMAL_PLACES)
        return None

    def fetch_markets(self, params={}):
        result = [
            {
                'symbol': pair,
                'base': 'JPY',
                'quote': 'JPY',
                'maker': 0.001,
                'taker': 0.001,
                'active': True,
                'min_unit': 100,
                'limits': {  # value limits when placing orders on this market
                    'amount': {
                        'min': 100,  # order amount should be > min
                        'max': 100000000,  # order amount should be < max
                    },
                    'price': {
                        'min': 100,  # order price should be > min
                        'max': 100000000,  # order price should be < max
                    },
                    'cost':  {  # order cost = price * amount
                        'min': 0,  # order cost should be > min
                        'max': 100000000,  # order cost should be < max
                    },
                },
            } for pair in ['8306@1/JPY', '4689@1/JPY', '6501@1/JPY',
                           '3826@1/JPY', '5020@1/JPY', '3632@1/JPY',
                           '5191@1/JPY', '6440@1/JPY', '167030018@24/JPY']
        ]

        return result

    def fetch_balance(self, params={}):
        self.load_markets()
        return {}  # self.parse_balance(result)

    def fetch_order_book(self, symbol, limit=None, params={}):
        self.load_markets()
        orderbook = fetch_order_book(self.kabuto_config['token'], symbol, limit=None, params={})
        return orderbook

    def fetch_currencies(self, params={}):
        result = {}
        return result

    def parse_ticker(self, ticker, market=None):
        return {}

    def fetch_tickers(self, symbols=None, params={}):
        self.load_markets()
        return []

    def fetch_ticker(self, symbol, params={}):
        self.load_markets()
        return {}

    def parse_trade(self, trade, market=None):

        return {
            'info': None,  # trade,
            'timestamp': None,  # timestamp,
            'datetime': None,  # self.iso8601(timestamp),
            'symbol': None,  # market['symbol'],
            'id': None,  # id,
            'order': None,  # order,
            'takerOrMaker': None,  # takerOrMaker,
            'type': None,
            'side': None,  # side,
            'price': None,  # price,
            'amount': None,  # amount,
            'cost': None,  # cost,
            'fee': None,  # fee,
        }

    def fetch_time(self, params={}):
        # response = self.publicGetPing(params)
        return None  # self.safe_integer(response, 'serverTime')

    def fetch_trades(self, symbol, since=None, limit=None, params={}):
        self.load_markets()
        return None,  # self.parse_trades(response, market, since, limit)

    def parse_ohlcv(self, ohlcv, market=None):

        return [
            # self.parse8601(self.safe_string(ohlcv, 'startsAt')),
            # self.safe_number(ohlcv, 'open'),
            # self.safe_number(ohlcv, 'high'),
            # self.safe_number(ohlcv, 'low'),
            # self.safe_number(ohlcv, 'close'),
            # self.safe_number(ohlcv, 'volume'),
        ]

    def fetch_ohlcv(self, symbol, timeframe='1m', since=None, limit=None, params={}):
        self.load_markets()
        return []  # self.parse_ohlcvs(response, market, timeframe, since, limit)

    def fetch_open_orders(self, symbol=None, since=None, limit=None, params={}):
        self.load_markets()
        return None  # self.parse_orders(response, market, since, limit)

    def fetch_order_trades(self, id, symbol=None, since=None, limit=None, params={}):
        self.load_markets()
        return None  # self.parse_trades(response, market, since, limit)

    def create_order(self, symbol, type, side, amount, price=None, params={}):
        # A ceiling order is a market or limit order that allows you to specify
        # the amount of quote currency you want to spend(or receive, if selling)
        # instead of the quantity of the market currency(e.g. buy $100 USD of BTC
        # at the current market BTC price)
        self.load_markets()

        return {}

    def cancel_order(self, id, symbol=None, params={}):
        self.load_markets()
        return []

    def cancel_all_orders(self, symbol=None, params={}):
        self.load_markets()
        return []

    def fetch_deposits(self, code=None, since=None, limit=None, params={}):
        self.load_markets()
        return []

    def fetch_withdrawals(self, code=None, since=None, limit=None, params={}):
        self.load_markets()
        return {}

    def parse_transaction(self, transaction, currency=None):
        return {}

    def parse_time_in_force(self, timeInForce):
        return {}

    def parse_order(self, order, market=None):
        return {}

    def parse_orders(self, orders, market=None, since=None, limit=None, params={}):
        return {}

    def parse_order_status(self, status):
        statuses = {
            'CLOSED': 'closed',
            'OPEN': 'open',
            'CANCELLED': 'canceled',
            'CANCELED': 'canceled',
        }
        return statuses

    def fetch_order(self, id, symbol=None, params={}):
        return self.parse_order({})

    def order_to_trade(self, order):
        return {
            'id': None,  # self.safe_string(order, 'id'),
            'side': None,  # self.safe_string(order, 'side'),
            'order': None,  # self.safe_string(order, 'id'),
            'type': None,  # self.safe_string(order, 'type'),
            'price': None,  # self.safe_number(order, 'average'),
            'amount': None,  # self.safe_number(order, 'filled'),
            'cost': None,  # self.safe_number(order, 'cost'),
            'symbol': None,  # self.safe_string(order, 'symbol'),
            'timestamp': None,  # timestamp,
            'datetime': None,  # self.iso8601(timestamp),
            'fee': None,  # self.safe_value(order, 'fee'),
            'info': None,  # order,
            'takerOrMaker': None,
        }

    def orders_to_trades(self, orders):
        # self entire method should be moved to the base class
        result = []
        for i in range(0, len(orders)):
            result.append(self.order_to_trade(orders[i]))
        return result

    def fetch_my_trades(self, symbol=None, since=None, limit=None, params={}):
        self.load_markets()
        return {}

    def fetch_closed_orders(self, symbol=None, since=None, limit=None, params={}):
        self.load_markets()
        return {}

    def create_deposit_address(self, code, params={}):
        self.load_markets()
        return {
            'currency': None,  # code,
            'address': None,  # address,
            'tag': None,  # tag,
            'info': None,  # response,
        }

    def fetch_deposit_address(self, code, params={}):
        self.load_markets()
        return {
            'currency': None,  # code,
            'address': None,  # address,
            'tag': None,  # tag,
            'info': None,  # response,
        }

    def withdraw(self, code, amount, address, tag=None, params={}):
        return {
            'info': None,  # response,
            'id': None,  # id,
        }

    def sign(self, path, api='v3', method='GET', params={}, headers=None, body=None):
        return {
            'url': None,  # url,
            'method': None,  # method,
            'body': None,  # body,
            'headers': None,  # headers
        }

    def handle_errors(self, code, reason, url, method, headers, body, response, requestHeaders, requestBody):
        pass

    @staticmethod
    def key_exists(dictionary, key):
        if dictionary is None or key is None:
            return False
        if isinstance(dictionary, list):
            if isinstance(key, int) and 0 <= key and key < len(dictionary):
                return dictionary[key] is not None
            else:
                return False
        if key in dictionary:
            return dictionary[key] is not None
        return False

    @staticmethod
    def safe_float(dictionary, key, default_value=None):
        value = default_value
        try:
            if API.key_exists(dictionary, key):
                value = float(dictionary[key])
        except ValueError as e:
            value = default_value
        return value

    @staticmethod
    def safe_string(dictionary, key, default_value=None):
        return str(dictionary[key]) if API.key_exists(dictionary, key) else default_value

    @staticmethod
    def safe_string_lower(dictionary, key, default_value=None):
        return str(dictionary[key]).lower() if API.key_exists(dictionary, key) else default_value

    @staticmethod
    def safe_string_upper(dictionary, key, default_value=None):
        return str(dictionary[key]).upper() if API.key_exists(dictionary, key) else default_value

    @staticmethod
    def safe_integer(dictionary, key, default_value=None):
        if not API.key_exists(dictionary, key):
            return default_value
        value = dictionary[key]
        try:
            # needed to avoid breaking on "100.0"
            # https://stackoverflow.com/questions/1094717/convert-a-string-to-integer-with-decimal-in-python#1094721
            return int(float(value))
        except ValueError:
            return default_value
        except TypeError:
            return default_value

    @staticmethod
    def safe_integer_product(dictionary, key, factor, default_value=None):
        if not API.key_exists(dictionary, key):
            return default_value
        value = dictionary[key]
        if isinstance(value, Number):
            return int(value * factor)
        elif isinstance(value, basestring):
            try:
                return int(float(value) * factor)
            except ValueError:
                pass
        return default_value

    @staticmethod
    def safe_timestamp(dictionary, key, default_value=None):
        return API.safe_integer_product(dictionary, key, 1000, default_value)

    @staticmethod
    def safe_value(dictionary, key, default_value=None):
        return dictionary[key] if API.key_exists(dictionary, key) else default_value

    # we're not using safe_floats with a list argument as we're trying to save some cycles here
    # we're not using safe_float_3 either because those cases are too rare to deserve their own optimization

    @staticmethod
    def safe_float_2(dictionary, key1, key2, default_value=None):
        return API.safe_either(API.safe_float, dictionary, key1, key2, default_value)

    @staticmethod
    def safe_string_2(dictionary, key1, key2, default_value=None):
        return API.safe_either(API.safe_string, dictionary, key1, key2, default_value)

    @staticmethod
    def safe_string_lower_2(dictionary, key1, key2, default_value=None):
        return API.safe_either(API.safe_string_lower, dictionary, key1, key2, default_value)

    @staticmethod
    def safe_string_upper_2(dictionary, key1, key2, default_value=None):
        return API.safe_either(API.safe_string_upper, dictionary, key1, key2, default_value)

    @staticmethod
    def safe_integer_2(dictionary, key1, key2, default_value=None):
        return API.safe_either(API.safe_integer, dictionary, key1, key2, default_value)

    @staticmethod
    def safe_integer_product_2(dictionary, key1, key2, factor, default_value=None):
        value = API.safe_integer_product(dictionary, key1, factor)
        return value if value is not None else API.safe_integer_product(dictionary, key2, factor, default_value)

    @staticmethod
    def safe_timestamp_2(dictionary, key1, key2, default_value=None):
        return API.safe_integer_product_2(dictionary, key1, key2, 1000, default_value)

    @staticmethod
    def safe_value_2(dictionary, key1, key2, default_value=None):
        return API.safe_either(API.safe_value, dictionary, key1, key2, default_value)

    @staticmethod
    def safe_either(method, dictionary, key1, key2, default_value=None):
        """A helper-wrapper for the safe_value_2() family."""
        value = method(dictionary, key1)
        return value if value is not None else method(dictionary, key2, default_value)

    @staticmethod
    def truncate(num, precision=0):
        """Deprecated, use decimal_to_precision instead"""
        if precision > 0:
            decimal_precision = math.pow(10, precision)
            return math.trunc(num * decimal_precision) / decimal_precision
        return int(API.truncate_to_string(num, precision))

    @staticmethod
    def truncate_to_string(num, precision=0):
        """Deprecated, todo: remove references from subclasses"""
        if precision > 0:
            parts = ('{0:.%df}' % precision).format(Decimal(num)).split('.')
            decimal_digits = parts[1][:precision].rstrip('0')
            decimal_digits = decimal_digits if len(decimal_digits) else '0'
            return parts[0] + '.' + decimal_digits
        return ('%d' % num)

    @staticmethod
    def uuid22(length=22):
        return format(random.getrandbits(length * 4), 'x')

    @staticmethod
    def uuid16(length=16):
        return format(random.getrandbits(length * 4), 'x')

    @staticmethod
    def uuid():
        return str(uuid.uuid4())

    @staticmethod
    def uuidv1():
        return str(uuid.uuid1()).replace('-', '')

    @staticmethod
    def capitalize(string):  # first character only, rest characters unchanged
        # the native pythonic .capitalize() method lowercases all other characters
        # which is an unwanted behaviour, therefore we use this custom implementation
        # check it yourself: print('foobar'.capitalize(), 'fooBar'.capitalize())
        if len(string) > 1:
            return "%s%s" % (string[0].upper(), string[1:])
        return string.upper()

    @staticmethod
    def strip(string):
        return string.strip()

    @staticmethod
    def keysort(dictionary):
        return collections.OrderedDict(sorted(dictionary.items(), key=lambda t: t[0]))

    @staticmethod
    def extend(*args):
        if args is not None:
            result = None
            if type(args[0]) is collections.OrderedDict:
                result = collections.OrderedDict()
            else:
                result = {}
            for arg in args:
                result.update(arg)
            return result
        return {}

    @staticmethod
    def deep_extend(*args):
        result = None
        for arg in args:
            if isinstance(arg, dict):
                if not isinstance(result, dict):
                    result = {}
                for key in arg:
                    result[key] = API.deep_extend(result[key] if key in result else None, arg[key])
            else:
                result = arg
        return result

    @staticmethod
    def filter_by(array, key, value=None):
        array = API.to_array(array)
        return list(filter(lambda x: x[key] == value, array))

    @staticmethod
    def filterBy(array, key, value=None):
        return API.filter_by(array, key, value)

    @staticmethod
    def group_by(array, key):
        result = {}
        array = API.to_array(array)
        array = [entry for entry in array if (key in entry) and (entry[key] is not None)]
        for entry in array:
            if entry[key] not in result:
                result[entry[key]] = []
            result[entry[key]].append(entry)
        return result

    @staticmethod
    def groupBy(array, key):
        return API.group_by(array, key)

    @staticmethod
    def index_by(array, key):
        result = {}
        if type(array) is dict:
            array = API.keysort(array).values()
        is_int_key = isinstance(key, int)
        for element in array:
            if ((is_int_key and (key < len(element))) or (key in element)) and (element[key] is not None):
                k = element[key]
                result[k] = element
        return result

    @staticmethod
    def sort_by(array, key, descending=False):
        return sorted(array, key=lambda k: k[key] if k[key] is not None else "", reverse=descending)

    @staticmethod
    def array_concat(a, b):
        return a + b

    @staticmethod
    def in_array(needle, haystack):
        return needle in haystack

    @staticmethod
    def is_empty(object):
        return not object

    @staticmethod
    def extract_params(string):
        return re.findall(r'{([\w-]+)}', string)

    def implode_hostname(self, url):
        return API.implode_params(url, {'hostname': self.hostname})

    @staticmethod
    def implode_params(string, params):
        if isinstance(params, dict):
            for key in params:
                if not isinstance(params[key], list):
                    string = string.replace('{' + key + '}', str(params[key]))
        return string

    @staticmethod
    def urlencode(params={}, doseq=False):
        for key, value in params.items():
            if isinstance(value, bool):
                params[key] = 'true' if value else 'false'
        return _urlencode.urlencode(params, doseq)

    @staticmethod
    def urlencode_with_array_repeat(params={}):
        return re.sub(r'%5B\d*%5D', '', API.urlencode(params, True))

    @staticmethod
    def rawencode(params={}):
        return _urlencode.unquote(API.urlencode(params))

    @staticmethod
    def encode_uri_component(uri, safe="~()*!.'"):
        return _urlencode.quote(uri, safe=safe)

    @staticmethod
    def omit(d, *args):
        if isinstance(d, dict):
            result = d.copy()
            for arg in args:
                if type(arg) is list:
                    for key in arg:
                        if key in result:
                            del result[key]
                else:
                    if arg in result:
                        del result[arg]
            return result
        return d

    @staticmethod
    def unique(array):
        return list(set(array))

    @staticmethod
    def pluck(array, key):
        return [
            element[key]
            for element in array
            if (key in element) and (element[key] is not None)
        ]

    @staticmethod
    def sum(*args):
        return sum([arg for arg in args if isinstance(arg, (float, int))])

    @staticmethod
    def ordered(array):
        return collections.OrderedDict(array)

    @staticmethod
    def aggregate(bidasks):
        ordered = API.ordered({})
        for [price, volume, *_] in bidasks:
            if volume > 0:
                ordered[price] = (ordered[price] if price in ordered else 0) + volume
        result = []
        items = list(ordered.items())
        for price, volume in items:
            result.append([price, volume])
        return result

    @staticmethod
    def sec():
        return API.seconds()

    @staticmethod
    def msec():
        return API.milliseconds()

    @staticmethod
    def usec():
        return API.microseconds()

    @staticmethod
    def seconds():
        return int(time.time())

    @staticmethod
    def milliseconds():
        return int(time.time() * 1000)

    @staticmethod
    def microseconds():
        return int(time.time() * 1000000)

    @staticmethod
    def iso8601(timestamp=None):
        if timestamp is None:
            return timestamp
        if not isinstance(timestamp, (int, long)):
            return None
        if int(timestamp) < 0:
            return None

        try:
            utc = datetime.datetime.utcfromtimestamp(timestamp // 1000)
            return utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-6] + "{:03d}".format(int(timestamp) % 1000) + 'Z'
        except (TypeError, OverflowError, OSError):
            return None

    @staticmethod
    def rfc2616(self, timestamp=None):
        if timestamp is None:
            ts = datetime.datetime.now()
        else:
            ts = timestamp
        stamp = mktime(ts.timetuple())
        return format_date_time(stamp)

    @staticmethod
    def dmy(timestamp, infix='-'):
        utc_datetime = datetime.datetime.utcfromtimestamp(int(round(timestamp / 1000)))
        return utc_datetime.strftime('%m' + infix + '%d' + infix + '%Y')

    @staticmethod
    def ymd(timestamp, infix='-'):
        utc_datetime = datetime.datetime.utcfromtimestamp(int(round(timestamp / 1000)))
        return utc_datetime.strftime('%Y' + infix + '%m' + infix + '%d')

    @staticmethod
    def ymdhms(timestamp, infix=' '):
        utc_datetime = datetime.datetime.utcfromtimestamp(int(round(timestamp / 1000)))
        return utc_datetime.strftime('%Y-%m-%d' + infix + '%H:%M:%S')

    @staticmethod
    def parse_date(timestamp=None):
        if timestamp is None:
            return timestamp
        if not isinstance(timestamp, str):
            return None
        if 'GMT' in timestamp:
            try:
                string = ''.join([str(value) for value in parsedate(timestamp)[:6]]) + '.000Z'
                dt = datetime.datetime.strptime(string, "%Y%m%d%H%M%S.%fZ")
                return calendar.timegm(dt.utctimetuple()) * 1000
            except (TypeError, OverflowError, OSError):
                return None
        else:
            return API.parse8601(timestamp)

    @staticmethod
    def parse8601(timestamp=None):
        if timestamp is None:
            return timestamp
        yyyy = '([0-9]{4})-?'
        mm = '([0-9]{2})-?'
        dd = '([0-9]{2})(?:T|[\\s])?'
        h = '([0-9]{2}):?'
        m = '([0-9]{2}):?'
        s = '([0-9]{2})'
        ms = '(\\.[0-9]{1,3})?'
        tz = '(?:(\\+|\\-)([0-9]{2})\\:?([0-9]{2})|Z)?'
        regex = r'' + yyyy + mm + dd + h + m + s + ms + tz
        try:
            match = re.search(regex, timestamp, re.IGNORECASE)
            if match is None:
                return None
            yyyy, mm, dd, h, m, s, ms, sign, hours, minutes = match.groups()
            ms = ms or '.000'
            ms = (ms + '00')[0:4]
            msint = int(ms[1:])
            sign = sign or ''
            sign = int(sign + '1') * -1
            hours = int(hours or 0) * sign
            minutes = int(minutes or 0) * sign
            offset = datetime.timedelta(hours=hours, minutes=minutes)
            string = yyyy + mm + dd + h + m + s + ms + 'Z'
            dt = datetime.datetime.strptime(string, "%Y%m%d%H%M%S.%fZ")
            dt = dt + offset
            return calendar.timegm(dt.utctimetuple()) * 1000 + msint
        except (TypeError, OverflowError, OSError, ValueError):
            return None

    @staticmethod
    def hash(request, algorithm='md5', digest='hex'):
        if algorithm == 'keccak':
            binary = bytes(keccak.SHA3(request))
        else:
            h = hashlib.new(algorithm, request)
            binary = h.digest()
        if digest == 'base64':
            return API.binary_to_base64(binary)
        elif digest == 'hex':
            return API.binary_to_base16(binary)
        return binary

    @staticmethod
    def hmac(request, secret, algorithm=hashlib.sha256, digest='hex'):
        h = hmac.new(secret, request, algorithm)
        binary = h.digest()
        if digest == 'hex':
            return API.binary_to_base16(binary)
        elif digest == 'base64':
            return API.binary_to_base64(binary)
        return binary

    @staticmethod
    def binary_concat(*args):
        result = bytes()
        for arg in args:
            result = result + arg
        return result

    @staticmethod
    def binary_concat_array(array):
        result = bytes()
        for element in array:
            result = result + element
        return result

    @staticmethod
    def base64urlencode(s):
        return API.decode(base64.urlsafe_b64encode(s)).replace('=', '')

    @staticmethod
    def binary_to_base64(s):
        return API.decode(base64.standard_b64encode(s))

    @staticmethod
    def base64_to_binary(s):
        return base64.standard_b64decode(s)

    @staticmethod
    def string_to_base64(s):
        # will return string in the future
        binary = API.encode(s) if isinstance(s, str) else s
        return API.encode(API.binary_to_base64(binary))

    @staticmethod
    def base64_to_string(s):
        return base64.b64decode(s).decode('utf-8')

    @staticmethod
    def jwt(request, secret, alg='HS256'):
        algos = {
            'HS256': hashlib.sha256,
            'HS384': hashlib.sha384,
            'HS512': hashlib.sha512,
        }
        header = API.encode(API.json({
            'alg': alg,
            'typ': 'JWT',
        }))
        encoded_header = API.base64urlencode(header)
        encoded_data = API.base64urlencode(API.encode(API.json(request)))
        token = encoded_header + '.' + encoded_data
        if alg[:2] == 'RS':
            signature = API.rsa(token, secret, alg)
        else:
            algorithm = algos[alg]
            signature = API.hmac(API.encode(token), secret, algorithm, 'binary')
        return token + '.' + API.base64urlencode(signature)

    @staticmethod
    def rsa(request, secret, alg='RS256'):
        algorithms = {
            "RS256": hashes.SHA256(),
            "RS384": hashes.SHA384(),
            "RS512": hashes.SHA512(),
        }
        algorithm = algorithms[alg]
        priv_key = load_pem_private_key(secret, None, backends.default_backend())
        return priv_key.sign(API.encode(request), padding.PKCS1v15(), algorithm)

    @staticmethod
    def ecdsa(request, secret, algorithm='p256', hash=None, fixed_length=False):
        # your welcome - frosty00
        algorithms = {
            'p192': [ecdsa.NIST192p, 'sha256'],
            'p224': [ecdsa.NIST224p, 'sha256'],
            'p256': [ecdsa.NIST256p, 'sha256'],
            'p384': [ecdsa.NIST384p, 'sha384'],
            'p521': [ecdsa.NIST521p, 'sha512'],
            'secp256k1': [ecdsa.SECP256k1, 'sha256'],
        }
        if algorithm not in algorithms:
            raise ArgumentsRequired(algorithm + ' is not a supported algorithm')
        curve_info = algorithms[algorithm]
        hash_function = getattr(hashlib, curve_info[1])
        encoded_request = API.encode(request)
        if hash is not None:
            digest = API.hash(encoded_request, hash, 'binary')
        else:
            digest = base64.b16decode(encoded_request, casefold=True)
        key = ecdsa.SigningKey.from_string(base64.b16decode(API.encode(secret),
                                                            casefold=True), curve=curve_info[0])
        r_binary, s_binary, v = key.sign_digest_deterministic(digest, hashfunc=hash_function,
                                                              sigencode=ecdsa.util.sigencode_strings_canonize)
        r_int, s_int = ecdsa.util.sigdecode_strings((r_binary, s_binary), key.privkey.order)
        counter = 0
        minimum_size = (1 << (8 * 31)) - 1
        half_order = key.privkey.order / 2
        while fixed_length and (r_int > half_order or r_int <= minimum_size or s_int <= minimum_size):
            r_binary, s_binary, v = key.sign_digest_deterministic(digest, hashfunc=hash_function,
                                                                  sigencode=ecdsa.util.sigencode_strings_canonize,
                                                                  extra_entropy=API.number_to_le(counter, 32))
            r_int, s_int = ecdsa.util.sigdecode_strings((r_binary, s_binary), key.privkey.order)
            counter += 1
        r, s = API.decode(base64.b16encode(r_binary)).lower(), API.decode(base64.b16encode(s_binary)).lower()
        return {
            'r': r,
            's': s,
            'v': v,
        }

    @staticmethod
    def eddsa(request, secret, curve='ed25519'):
        random = b'\x00' * 64
        request = base64.b16decode(request, casefold=True)
        secret = base64.b16decode(secret, casefold=True)
        signature = eddsa.calculateSignature(random, secret, request)
        return API.binary_to_base58(signature)

    @staticmethod
    def json(data, params=None):
        return json.dumps(data, separators=(',', ':'))

    @staticmethod
    def is_json_encoded_object(input):
        return (isinstance(input, basestring) and
                (len(input) >= 2) and
                ((input[0] == '{') or (input[0] == '[')))

    @staticmethod
    def encode(string):
        return string.encode('latin-1')

    @staticmethod
    def decode(string):
        return string.decode('latin-1')

    @staticmethod
    def to_array(value):
        return list(value.values()) if type(value) is dict else value

    def nonce(self):
        return API.seconds()

    @staticmethod
    def check_required_version(required_version, error=True):
        result = True
        [major1, minor1, patch1] = required_version.split('.')
        [major2, minor2, patch2] = __version__.split('.')
        int_major1 = int(major1)
        int_minor1 = int(minor1)
        int_patch1 = int(patch1)
        int_major2 = int(major2)
        int_minor2 = int(minor2)
        int_patch2 = int(patch2)
        if int_major1 > int_major2:
            result = False
        if int_major1 == int_major2:
            if int_minor1 > int_minor2:
                result = False
            elif int_minor1 == int_minor2 and int_patch1 > int_patch2:
                result = False
        if not result:
            if error:
                raise NotSupported('Your current version of CCXT is ' + __version__ + ', a newer version ' + required_version + ' is required, please, upgrade your version of CCXT')
            else:
                return error
        return result
