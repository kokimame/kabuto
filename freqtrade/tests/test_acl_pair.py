# pragma pylint: disable=missing-docstring,C0103,protected-access

import freqtrade.tests.conftest as tt  # test tools

# whitelist, blacklist, filtering, all of that will
# eventually become some rules to run on a generic ACL engine
# perhaps try to anticipate that by using some python package


def whitelist_conf():
    config = tt.default_conf()

    config['stake_currency'] = 'BTC'
    config['exchange']['pair_whitelist'] = [
        'ETH/BTC',
        'TKN/BTC',
        'TRST/BTC',
        'SWT/BTC',
        'BCC/BTC'
    ]

    config['exchange']['pair_blacklist'] = [
        'BLK/BTC'
    ]

    return config


def get_market_summaries():
    return {
        'TKN/BTC': {
            'symbol': 'TKN/BTC',
            'info': {
                'High': 0.00000919,
                'Low': 0.00000820,
                'Volume': 74339.61396015,
                'Last': 0.00000820,
                'BaseVolume': 1664,
                'TimeStamp': '2014-07-09T07:19:30.15',
                'Bid': 0.00000820,
                'Ask': 0.00000831,
                'OpenBuyOrders': 15,
                'OpenSellOrders': 15,
                'PrevDay': 0.00000821,
                'Created': '2014-03-20T06:00:00',
                'DisplayMarketName': ''
            }
        },
        'ETH/BTC': {
            'symbol': 'ETH/BTC',
            'info': {
                'High': 0.00000072,
                'Low': 0.00000001,
                'Volume': 166340678.42280999,
                'Last': 0.00000005,
                'BaseVolume': 42,
                'TimeStamp': '2014-07-09T07:21:40.51',
                'Bid': 0.00000004,
                'Ask': 0.00000005,
                'OpenBuyOrders': 18,
                'OpenSellOrders': 18,
                'PrevDay': 0.00000002,
                'Created': '2014-05-30T07:57:49.637',
                'DisplayMarketName': ''
            }
        },
        'BLK/BTC': {
            'symbol': 'BLK/BTC',
            'info': {
                'High': 0.00000072,
                'Low': 0.00000001,
                'Volume': 166340678.42280999,
                'Last': 0.00000005,
                'BaseVolume': 3,
                'TimeStamp': '2014-07-09T07:21:40.51',
                'Bid': 0.00000004,
                'Ask': 0.00000005,
                'OpenBuyOrders': 18,
                'OpenSellOrders': 18,
                'PrevDay': 0.00000002,
                'Created': '2014-05-30T07:57:49.637',
                'DisplayMarketName': ''
            }}
    }


def get_health():
    return {
        'ETH/BTC': {'base': 'ETH', 'active': True},
        'TKN/BTC': {'base': 'TKN', 'active': True},
        'BLK/BTC': {'base': 'BLK', 'active': True}}


def get_health_empty():
    return {}


def test_refresh_market_pair_not_in_whitelist(mocker):
    conf = whitelist_conf()

    freqtradebot = tt.get_patched_freqtradebot(mocker, conf)

    mocker.patch('freqtrade.freqtradebot.exchange.get_wallet_health', get_health)
    refreshedwhitelist = freqtradebot._refresh_whitelist(
        conf['exchange']['pair_whitelist'] + ['XXX/BTC']
    )
    # List ordered by BaseVolume
    whitelist = ['ETH/BTC', 'TKN/BTC']
    # Ensure all except those in whitelist are removed
    assert whitelist == refreshedwhitelist


def test_refresh_whitelist(mocker):
    conf = whitelist_conf()
    freqtradebot = tt.get_patched_freqtradebot(mocker, conf)

    mocker.patch('freqtrade.freqtradebot.exchange.get_wallet_health', get_health)
    refreshedwhitelist = freqtradebot._refresh_whitelist(conf['exchange']['pair_whitelist'])

    # List ordered by BaseVolume
    whitelist = ['ETH/BTC', 'TKN/BTC']
    # Ensure all except those in whitelist are removed
    assert whitelist == refreshedwhitelist


def test_refresh_whitelist_dynamic(mocker):
    conf = whitelist_conf()
    freqtradebot = tt.get_patched_freqtradebot(mocker, conf)
    mocker.patch.multiple(
        'freqtrade.freqtradebot.exchange',
        get_wallet_health=get_health,
        get_market_summaries=get_market_summaries
    )

    # argument: use the whitelist dynamically by exchange-volume
    whitelist = ['TKN/BTC', 'ETH/BTC']

    refreshedwhitelist = freqtradebot._refresh_whitelist(
        freqtradebot._gen_pair_whitelist(conf['stake_currency'])
    )

    assert whitelist == refreshedwhitelist


def test_refresh_whitelist_dynamic_empty(mocker):
    conf = whitelist_conf()
    freqtradebot = tt.get_patched_freqtradebot(mocker, conf)
    mocker.patch('freqtrade.freqtradebot.exchange.get_wallet_health', get_health_empty)

    # argument: use the whitelist dynamically by exchange-volume
    whitelist = []
    conf['exchange']['pair_whitelist'] = []
    freqtradebot._refresh_whitelist(whitelist)
    pairslist = conf['exchange']['pair_whitelist']

    assert set(whitelist) == set(pairslist)
