# pragma pylint: disable=too-few-public-methods

"""
bot constants
"""
DYNAMIC_WHITELIST = 20  # pairs
PROCESS_THROTTLE_SECS = 5  # sec
TICKER_INTERVAL = 5  # min
HYPEROPT_EPOCH = 100  # epochs
RETRY_TIMEOUT = 30  # sec
DEFAULT_STRATEGY = 'DefaultStrategy'
DEFAULT_DB_PROD_URL = 'sqlite:///tradesv3.sqlite'
DEFAULT_DB_DRYRUN_URL = 'sqlite://'
UNLIMITED_STAKE_AMOUNT = 'unlimited'


TICKER_INTERVAL_MINUTES = {
    '1m': 1,
    '3m': 3,
    '5m': 5,
    '15m': 15,
    '30m': 30,
    '1h': 60,
    '2h': 120,
    '4h': 240,
    '6h': 360,
    '8h': 480,
    '12h': 720,
    '1d': 1440,
    '3d': 4320,
    '1w': 10080,
}

SUPPORTED_FIAT = [
    "AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK", "DKK",
    "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY",
    "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PKR", "PLN",
    "RUB", "SEK", "SGD", "THB", "TRY", "TWD", "ZAR", "USD",
    "BTC", "ETH", "XRP", "LTC", "BCH", "USDT"
    ]

# Required json-schema for user specified config
CONF_SCHEMA = {
    'type': 'object',
    'properties': {
        'max_open_trades': {'type': 'integer', 'minimum': 0},
        'ticker_interval': {'type': 'string', 'enum': list(TICKER_INTERVAL_MINUTES.keys())},
        'stake_currency': {'type': 'string', 'enum': ['BTC', 'ETH', 'USDT', 'EUR', 'USD']},
        'stake_amount': {
            "type": ["number", "string"],
            "minimum": 0.0005,
            "pattern": UNLIMITED_STAKE_AMOUNT
        },
        'fiat_display_currency': {'type': 'string', 'enum': SUPPORTED_FIAT},
        'dry_run': {'type': 'boolean'},
        'minimal_roi': {
            'type': 'object',
            'patternProperties': {
                '^[0-9.]+$': {'type': 'number'}
            },
            'minProperties': 1
        },
        'stoploss': {'type': 'number', 'maximum': 0, 'exclusiveMaximum': True},
        'trailing_stop': {'type': 'boolean'},
        'trailing_stop_positive': {'type': 'number', 'minimum': 0, 'maximum': 1},
        'unfilledtimeout': {
            'type': 'object',
            'properties': {
                'buy': {'type': 'number', 'minimum': 3},
                'sell': {'type': 'number', 'minimum': 10}
            }
        },
        'bid_strategy': {
            'type': 'object',
            'properties': {
                'ask_last_balance': {
                    'type': 'number',
                    'minimum': 0,
                    'maximum': 1,
                    'exclusiveMaximum': False
                },
            },
            'required': ['ask_last_balance']
        },
        'exchange': {'$ref': '#/definitions/exchange'},
        'experimental': {
            'type': 'object',
            'properties': {
                'use_sell_signal': {'type': 'boolean'},
                'sell_profit_only': {'type': 'boolean'},
                "ignore_roi_if_buy_signal_true": {'type': 'boolean'}
            }
        },
        'telegram': {
            'type': 'object',
            'properties': {
                'enabled': {'type': 'boolean'},
                'token': {'type': 'string'},
                'chat_id': {'type': 'string'},
            },
            'required': ['enabled', 'token', 'chat_id']
        },
        'webhook': {
            'type': 'object',
            'properties': {
                'enabled': {'type': 'boolean'},
                'webhookbuy': {'type': 'object'},
                'webhooksell': {'type': 'object'},
                'webhookstatus': {'type': 'object'},
            },
        },
        'db_url': {'type': 'string'},
        'initial_state': {'type': 'string', 'enum': ['running', 'stopped']},
        'internals': {
            'type': 'object',
            'properties': {
                'process_throttle_secs': {'type': 'number'},
                'interval': {'type': 'integer'}
            }
        }
    },
    'definitions': {
        'exchange': {
            'type': 'object',
            'properties': {
                'name': {'type': 'string'},
                'key': {'type': 'string'},
                'secret': {'type': 'string'},
                'pair_whitelist': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'pattern': '^[0-9A-Z]+/[0-9A-Z]+$'
                    },
                    'uniqueItems': True
                },
                'pair_blacklist': {
                    'type': 'array',
                    'items': {
                        'type': 'string',
                        'pattern': '^[0-9A-Z]+/[0-9A-Z]+$'
                    },
                    'uniqueItems': True
                }
            },
            'required': ['name', 'key', 'secret', 'pair_whitelist']
        }
    },
    'anyOf': [
        {'required': ['exchange']}
    ],
    'required': [
        'max_open_trades',
        'stake_currency',
        'stake_amount',
        'fiat_display_currency',
        'dry_run',
        'bid_strategy',
        'telegram'
    ]
}
