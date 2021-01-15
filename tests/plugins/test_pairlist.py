# pragma pylint: disable=missing-docstring,C0103,protected-access

from unittest.mock import MagicMock, PropertyMock

import pytest

from freqtrade.constants import AVAILABLE_PAIRLISTS
from freqtrade.exceptions import OperationalException
from freqtrade.plugins.pairlist.pairlist_helpers import expand_pairlist
from freqtrade.plugins.pairlistmanager import PairListManager
from freqtrade.resolvers import PairListResolver
from tests.conftest import get_patched_freqtradebot, log_has, log_has_re


@pytest.fixture(scope="function")
def whitelist_conf(default_conf):
    default_conf['stake_currency'] = 'BTC'
    default_conf['exchange']['pair_whitelist'] = [
        'ETH/BTC',
        'TKN/BTC',
        'TRST/BTC',
        'SWT/BTC',
        'BCC/BTC',
        'HOT/BTC',
    ]
    default_conf['exchange']['pair_blacklist'] = [
        'BLK/BTC'
    ]
    default_conf['pairlists'] = [
        {
            "method": "VolumePairList",
            "number_assets": 5,
            "sort_key": "quoteVolume",
        },
    ]
    return default_conf


@pytest.fixture(scope="function")
def whitelist_conf_2(default_conf):
    default_conf['stake_currency'] = 'BTC'
    default_conf['exchange']['pair_whitelist'] = [
        'ETH/BTC', 'TKN/BTC', 'BLK/BTC', 'LTC/BTC',
        'BTT/BTC', 'HOT/BTC', 'FUEL/BTC', 'XRP/BTC'
    ]
    default_conf['exchange']['pair_blacklist'] = [
        'BLK/BTC'
    ]
    default_conf['pairlists'] = [
        # {   "method": "StaticPairList"},
        {
            "method": "VolumePairList",
            "number_assets": 5,
            "sort_key": "quoteVolume",
            "refresh_period": 0,
        },
    ]
    return default_conf


@pytest.fixture(scope="function")
def whitelist_conf_agefilter(default_conf):
    default_conf['stake_currency'] = 'BTC'
    default_conf['exchange']['pair_whitelist'] = [
        'ETH/BTC', 'TKN/BTC', 'BLK/BTC', 'LTC/BTC',
        'BTT/BTC', 'HOT/BTC', 'FUEL/BTC', 'XRP/BTC'
    ]
    default_conf['exchange']['pair_blacklist'] = [
        'BLK/BTC'
    ]
    default_conf['pairlists'] = [
        {
            "method": "VolumePairList",
            "number_assets": 5,
            "sort_key": "quoteVolume",
            "refresh_period": 0,
        },
        {
            "method": "AgeFilter",
            "min_days_listed": 2
        }
    ]
    return default_conf


@pytest.fixture(scope="function")
def static_pl_conf(whitelist_conf):
    whitelist_conf['pairlists'] = [
        {
            "method": "StaticPairList",
        },
    ]
    return whitelist_conf


def test_log_cached(mocker, static_pl_conf, markets, tickers):
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )
    freqtrade = get_patched_freqtradebot(mocker, static_pl_conf)
    logmock = MagicMock()
    # Assign starting whitelist
    pl = freqtrade.pairlists._pairlist_handlers[0]
    pl.log_once('Hello world', logmock)
    assert logmock.call_count == 1
    pl.log_once('Hello world', logmock)
    assert logmock.call_count == 1
    assert pl._log_cache.currsize == 1
    assert ('Hello world',) in pl._log_cache._Cache__data

    pl.log_once('Hello world2', logmock)
    assert logmock.call_count == 2
    assert pl._log_cache.currsize == 2


def test_load_pairlist_noexist(mocker, markets, default_conf):
    freqtrade = get_patched_freqtradebot(mocker, default_conf)
    mocker.patch('freqtrade.exchange.Exchange.markets', PropertyMock(return_value=markets))
    plm = PairListManager(freqtrade.exchange, default_conf)
    with pytest.raises(OperationalException,
                       match=r"Impossible to load Pairlist 'NonexistingPairList'. "
                             r"This class does not exist or contains Python code errors."):
        PairListResolver.load_pairlist('NonexistingPairList', freqtrade.exchange, plm,
                                       default_conf, {}, 1)


def test_refresh_market_pair_not_in_whitelist(mocker, markets, static_pl_conf):

    freqtrade = get_patched_freqtradebot(mocker, static_pl_conf)

    mocker.patch('freqtrade.exchange.Exchange.markets', PropertyMock(return_value=markets))
    freqtrade.pairlists.refresh_pairlist()
    # List ordered by BaseVolume
    whitelist = ['ETH/BTC', 'TKN/BTC']
    # Ensure all except those in whitelist are removed
    assert set(whitelist) == set(freqtrade.pairlists.whitelist)
    # Ensure config dict hasn't been changed
    assert (static_pl_conf['exchange']['pair_whitelist'] ==
            freqtrade.config['exchange']['pair_whitelist'])


def test_refresh_static_pairlist(mocker, markets, static_pl_conf):
    freqtrade = get_patched_freqtradebot(mocker, static_pl_conf)
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        exchange_has=MagicMock(return_value=True),
        markets=PropertyMock(return_value=markets),
    )
    freqtrade.pairlists.refresh_pairlist()
    # List ordered by BaseVolume
    whitelist = ['ETH/BTC', 'TKN/BTC']
    # Ensure all except those in whitelist are removed
    assert set(whitelist) == set(freqtrade.pairlists.whitelist)
    assert static_pl_conf['exchange']['pair_blacklist'] == freqtrade.pairlists.blacklist


@pytest.mark.parametrize('pairs,expected', [
    (['NOEXIST/BTC', r'\+WHAT/BTC'],
     ['ETH/BTC', 'TKN/BTC', 'TRST/BTC', 'NOEXIST/BTC', 'SWT/BTC', 'BCC/BTC', 'HOT/BTC']),
    (['NOEXIST/BTC', r'*/BTC'],  # This is an invalid regex
     []),
])
def test_refresh_static_pairlist_noexist(mocker, markets, static_pl_conf, pairs, expected, caplog):

    static_pl_conf['pairlists'][0]['allow_inactive'] = True
    static_pl_conf['exchange']['pair_whitelist'] += pairs
    freqtrade = get_patched_freqtradebot(mocker, static_pl_conf)
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        exchange_has=MagicMock(return_value=True),
        markets=PropertyMock(return_value=markets),
    )
    freqtrade.pairlists.refresh_pairlist()

    # Ensure all except those in whitelist are removed
    assert set(expected) == set(freqtrade.pairlists.whitelist)
    assert static_pl_conf['exchange']['pair_blacklist'] == freqtrade.pairlists.blacklist
    if not expected:
        assert log_has_re(r'Pair whitelist contains an invalid Wildcard: Wildcard error.*', caplog)


def test_invalid_blacklist(mocker, markets, static_pl_conf, caplog):
    static_pl_conf['exchange']['pair_blacklist'] = ['*/BTC']
    freqtrade = get_patched_freqtradebot(mocker, static_pl_conf)
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        exchange_has=MagicMock(return_value=True),
        markets=PropertyMock(return_value=markets),
    )
    freqtrade.pairlists.refresh_pairlist()
    whitelist = []
    # Ensure all except those in whitelist are removed
    assert set(whitelist) == set(freqtrade.pairlists.whitelist)
    assert static_pl_conf['exchange']['pair_blacklist'] == freqtrade.pairlists.blacklist
    log_has_re(r"Pair blacklist contains an invalid Wildcard.*", caplog)


def test_refresh_pairlist_dynamic(mocker, shitcoinmarkets, tickers, whitelist_conf):

    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        get_tickers=tickers,
        exchange_has=MagicMock(return_value=True),
    )
    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
    # Remock markets with shitcoinmarkets since get_patched_freqtradebot uses the markets fixture
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        markets=PropertyMock(return_value=shitcoinmarkets),
    )
    # argument: use the whitelist dynamically by exchange-volume
    whitelist = ['ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC', 'HOT/BTC']
    freqtrade.pairlists.refresh_pairlist()
    assert whitelist == freqtrade.pairlists.whitelist

    whitelist_conf['pairlists'] = [{'method': 'VolumePairList'}]
    with pytest.raises(OperationalException,
                       match=r'`number_assets` not specified. Please check your configuration '
                             r'for "pairlist.config.number_assets"'):
        PairListManager(freqtrade.exchange, whitelist_conf)


def test_refresh_pairlist_dynamic_2(mocker, shitcoinmarkets, tickers, whitelist_conf_2):

    tickers_dict = tickers()

    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        exchange_has=MagicMock(return_value=True),
    )
    # Remove caching of ticker data to emulate changing volume by the time of second call
    mocker.patch.multiple(
        'freqtrade.plugins.pairlistmanager.PairListManager',
        _get_cached_tickers=MagicMock(return_value=tickers_dict),
    )
    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf_2)
    # Remock markets with shitcoinmarkets since get_patched_freqtradebot uses the markets fixture
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        markets=PropertyMock(return_value=shitcoinmarkets),
    )

    whitelist = ['ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC', 'HOT/BTC']
    freqtrade.pairlists.refresh_pairlist()
    assert whitelist == freqtrade.pairlists.whitelist

    whitelist = ['FUEL/BTC', 'ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC']
    tickers_dict['FUEL/BTC']['quoteVolume'] = 10000.0
    freqtrade.pairlists.refresh_pairlist()
    assert whitelist == freqtrade.pairlists.whitelist


def test_VolumePairList_refresh_empty(mocker, markets_empty, whitelist_conf):
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        exchange_has=MagicMock(return_value=True),
    )
    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
    mocker.patch('freqtrade.exchange.Exchange.markets', PropertyMock(return_value=markets_empty))

    # argument: use the whitelist dynamically by exchange-volume
    whitelist = []
    whitelist_conf['exchange']['pair_whitelist'] = []
    freqtrade.pairlists.refresh_pairlist()
    pairslist = whitelist_conf['exchange']['pair_whitelist']

    assert set(whitelist) == set(pairslist)


@pytest.mark.parametrize("pairlists,base_currency,whitelist_result", [
    # VolumePairList only
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC', 'HOT/BTC']),
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"}],
     "USDT", ['ETH/USDT', 'NANO/USDT', 'ADAHALF/USDT', 'ADADOUBLE/USDT']),
    # No pair for ETH, VolumePairList
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"}],
     "ETH", []),
    # No pair for ETH, StaticPairList
    ([{"method": "StaticPairList"}],
     "ETH", []),
    # No pair for ETH, all handlers
    ([{"method": "StaticPairList"},
      {"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "AgeFilter", "min_days_listed": 2},
      {"method": "PrecisionFilter"},
      {"method": "PriceFilter", "low_price_ratio": 0.03},
      {"method": "SpreadFilter", "max_spread_ratio": 0.005},
      {"method": "ShuffleFilter"}, {"method": "PerformanceFilter"}],
     "ETH", []),
    # AgeFilter and VolumePairList (require 2 days only, all should pass age test)
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "AgeFilter", "min_days_listed": 2}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC', 'HOT/BTC']),
    # AgeFilter and VolumePairList (require 10 days, all should fail age test)
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "AgeFilter", "min_days_listed": 10}],
     "BTC", []),
    # Precisionfilter and quote volume
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "PrecisionFilter"}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC']),
    # PriceFilter and VolumePairList
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "PriceFilter", "low_price_ratio": 0.03}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'LTC/BTC', 'XRP/BTC']),
    # PriceFilter and VolumePairList
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "PriceFilter", "low_price_ratio": 0.03}],
     "USDT", ['ETH/USDT', 'NANO/USDT']),
    # Hot is removed by precision_filter, Fuel by low_price_ratio, Ripple by min_price.
    ([{"method": "VolumePairList", "number_assets": 6, "sort_key": "quoteVolume"},
      {"method": "PrecisionFilter"},
      {"method": "PriceFilter", "low_price_ratio": 0.02, "min_price": 0.01}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'LTC/BTC']),
    # Hot is removed by precision_filter, Fuel by low_price_ratio, Ethereum by max_price.
    ([{"method": "VolumePairList", "number_assets": 6, "sort_key": "quoteVolume"},
      {"method": "PrecisionFilter"},
      {"method": "PriceFilter", "low_price_ratio": 0.02, "max_price": 0.05}],
     "BTC", ['TKN/BTC', 'LTC/BTC', 'XRP/BTC']),
    # HOT and XRP are removed because below 1250 quoteVolume
    ([{"method": "VolumePairList", "number_assets": 5,
       "sort_key": "quoteVolume", "min_value": 1250}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'LTC/BTC']),
    # StaticPairlist only
    ([{"method": "StaticPairList"}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'HOT/BTC']),
    # Static Pairlist before VolumePairList - sorting changes
    # SpreadFilter
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "SpreadFilter", "max_spread_ratio": 0.005}],
     "USDT", ['ETH/USDT']),
    # ShuffleFilter
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "ShuffleFilter", "seed": 77}],
     "USDT", ['ADADOUBLE/USDT', 'ETH/USDT', 'NANO/USDT', 'ADAHALF/USDT']),
    # ShuffleFilter, other seed
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "ShuffleFilter", "seed": 42}],
     "USDT", ['ADAHALF/USDT', 'NANO/USDT', 'ADADOUBLE/USDT', 'ETH/USDT']),
    # ShuffleFilter, no seed
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "ShuffleFilter"}],
     "USDT", 3),  # whitelist_result is integer -- check only length of randomized pairlist
    # AgeFilter only
    ([{"method": "AgeFilter", "min_days_listed": 2}],
     "BTC", 'filter_at_the_beginning'),  # OperationalException expected
    # PrecisionFilter after StaticPairList
    ([{"method": "StaticPairList"},
      {"method": "PrecisionFilter"}],
     "BTC", ['ETH/BTC', 'TKN/BTC']),
    # PrecisionFilter only
    ([{"method": "PrecisionFilter"}],
     "BTC", 'filter_at_the_beginning'),  # OperationalException expected
    # PriceFilter after StaticPairList
    ([{"method": "StaticPairList"},
      {"method": "PriceFilter", "low_price_ratio": 0.02, "min_price": 0.000001, "max_price": 0.1}],
     "BTC", ['ETH/BTC', 'TKN/BTC']),
    # PriceFilter only
    ([{"method": "PriceFilter", "low_price_ratio": 0.02}],
     "BTC", 'filter_at_the_beginning'),  # OperationalException expected
    # ShuffleFilter after StaticPairList
    ([{"method": "StaticPairList"},
      {"method": "ShuffleFilter", "seed": 42}],
     "BTC", ['TKN/BTC', 'ETH/BTC', 'HOT/BTC']),
    # ShuffleFilter only
    ([{"method": "ShuffleFilter", "seed": 42}],
     "BTC", 'filter_at_the_beginning'),  # OperationalException expected
    # PerformanceFilter after StaticPairList
    ([{"method": "StaticPairList"},
      {"method": "PerformanceFilter"}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'HOT/BTC']),
    # PerformanceFilter only
    ([{"method": "PerformanceFilter"}],
     "BTC", 'filter_at_the_beginning'),  # OperationalException expected
    # SpreadFilter after StaticPairList
    ([{"method": "StaticPairList"},
      {"method": "SpreadFilter", "max_spread_ratio": 0.005}],
     "BTC", ['ETH/BTC', 'TKN/BTC']),
    # SpreadFilter only
    ([{"method": "SpreadFilter", "max_spread_ratio": 0.005}],
     "BTC", 'filter_at_the_beginning'),  # OperationalException expected
    # Static Pairlist after VolumePairList, on a non-first position
    ([{"method": "VolumePairList", "number_assets": 5, "sort_key": "quoteVolume"},
      {"method": "StaticPairList"}],
        "BTC", 'static_in_the_middle'),
    ([{"method": "VolumePairList", "number_assets": 20, "sort_key": "quoteVolume"},
      {"method": "PriceFilter", "low_price_ratio": 0.02}],
        "USDT", ['ETH/USDT', 'NANO/USDT']),
    ([{"method": "StaticPairList"},
      {"method": "RangeStabilityFilter", "lookback_days": 10,
       "min_rate_of_change": 0.01, "refresh_period": 1440}],
     "BTC", ['ETH/BTC', 'TKN/BTC', 'HOT/BTC']),
])
def test_VolumePairList_whitelist_gen(mocker, whitelist_conf, shitcoinmarkets, tickers,
                                      ohlcv_history, pairlists, base_currency,
                                      whitelist_result, caplog) -> None:
    whitelist_conf['pairlists'] = pairlists
    whitelist_conf['stake_currency'] = base_currency

    ohlcv_data = {
        ('ETH/BTC', '1d'): ohlcv_history,
        ('TKN/BTC', '1d'): ohlcv_history,
        ('LTC/BTC', '1d'): ohlcv_history,
        ('XRP/BTC', '1d'): ohlcv_history,
        ('HOT/BTC', '1d'): ohlcv_history,
    }

    mocker.patch('freqtrade.exchange.Exchange.exchange_has', MagicMock(return_value=True))

    if whitelist_result == 'static_in_the_middle':
        with pytest.raises(OperationalException,
                           match=r"StaticPairList can only be used in the first position "
                                 r"in the list of Pairlist Handlers."):
            freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
        return

    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          get_tickers=tickers,
                          markets=PropertyMock(return_value=shitcoinmarkets)
                          )
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        refresh_latest_ohlcv=MagicMock(return_value=ohlcv_data),
    )

    # Provide for PerformanceFilter's dependency
    mocker.patch.multiple('freqtrade.persistence.Trade',
                          get_overall_performance=MagicMock(return_value=[])
                          )

    # Set whitelist_result to None if pairlist is invalid and should produce exception
    if whitelist_result == 'filter_at_the_beginning':
        with pytest.raises(OperationalException,
                           match=r"This Pairlist Handler should not be used at the first position "
                                 r"in the list of Pairlist Handlers."):
            freqtrade.pairlists.refresh_pairlist()
    else:
        freqtrade.pairlists.refresh_pairlist()
        whitelist = freqtrade.pairlists.whitelist

        assert isinstance(whitelist, list)

        # Verify length of pairlist matches (used for ShuffleFilter without seed)
        if type(whitelist_result) is list:
            assert whitelist == whitelist_result
        else:
            len(whitelist) == whitelist_result

        for pairlist in pairlists:
            if pairlist['method'] == 'AgeFilter' and pairlist['min_days_listed'] and \
                    len(ohlcv_history) <= pairlist['min_days_listed']:
                assert log_has_re(r'^Removed .* from whitelist, because age .* is less than '
                                  r'.* day.*', caplog)
            if pairlist['method'] == 'PrecisionFilter' and whitelist_result:
                assert log_has_re(r'^Removed .* from whitelist, because stop price .* '
                                  r'would be <= stop limit.*', caplog)
            if pairlist['method'] == 'PriceFilter' and whitelist_result:
                assert (log_has_re(r'^Removed .* from whitelist, because 1 unit is .*%$', caplog) or
                        log_has_re(r'^Removed .* from whitelist, '
                                   r'because last price < .*%$', caplog) or
                        log_has_re(r'^Removed .* from whitelist, '
                                   r'because last price > .*%$', caplog) or
                        log_has_re(r"^Removed .* from whitelist, because ticker\['last'\] "
                                   r"is empty.*", caplog))
            if pairlist['method'] == 'VolumePairList':
                logmsg = ("DEPRECATED: using any key other than quoteVolume for "
                          "VolumePairList is deprecated.")
                if pairlist['sort_key'] != 'quoteVolume':
                    assert log_has(logmsg, caplog)
                else:
                    assert not log_has(logmsg, caplog)


def test_PrecisionFilter_error(mocker, whitelist_conf) -> None:
    whitelist_conf['pairlists'] = [{"method": "StaticPairList"}, {"method": "PrecisionFilter"}]
    del whitelist_conf['stoploss']

    mocker.patch('freqtrade.exchange.Exchange.exchange_has', MagicMock(return_value=True))

    with pytest.raises(OperationalException,
                       match=r"PrecisionFilter can only work with stoploss defined\..*"):
        PairListManager(MagicMock, whitelist_conf)


def test_gen_pair_whitelist_not_supported(mocker, default_conf, tickers) -> None:
    default_conf['pairlists'] = [{'method': 'VolumePairList', 'number_assets': 10}]

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          get_tickers=tickers,
                          exchange_has=MagicMock(return_value=False),
                          )

    with pytest.raises(OperationalException,
                       match=r'Exchange does not support dynamic whitelist.*'):
        get_patched_freqtradebot(mocker, default_conf)


@pytest.mark.parametrize("pairlist", AVAILABLE_PAIRLISTS)
def test_pairlist_class(mocker, whitelist_conf, markets, pairlist):
    whitelist_conf['pairlists'][0]['method'] = pairlist
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True)
                          )
    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)

    assert freqtrade.pairlists.name_list == [pairlist]
    assert pairlist in str(freqtrade.pairlists.short_desc())
    assert isinstance(freqtrade.pairlists.whitelist, list)
    assert isinstance(freqtrade.pairlists.blacklist, list)


@pytest.mark.parametrize("pairlist", AVAILABLE_PAIRLISTS)
@pytest.mark.parametrize("whitelist,log_message", [
    (['ETH/BTC', 'TKN/BTC'], ""),
    # TRX/ETH not in markets
    (['ETH/BTC', 'TKN/BTC', 'TRX/ETH'], "is not compatible with exchange"),
    # wrong stake
    (['ETH/BTC', 'TKN/BTC', 'ETH/USDT'], "is not compatible with your stake currency"),
    # BCH/BTC not available
    (['ETH/BTC', 'TKN/BTC', 'BCH/BTC'], "is not compatible with exchange"),
    # BTT/BTC is inactive
    (['ETH/BTC', 'TKN/BTC', 'BTT/BTC'], "Market is not active"),
    # XLTCUSDT is not a valid pair
    (['ETH/BTC', 'TKN/BTC', 'XLTCUSDT'], "is not tradable with Freqtrade"),
])
def test__whitelist_for_active_markets(mocker, whitelist_conf, markets, pairlist, whitelist, caplog,
                                       log_message, tickers):
    whitelist_conf['pairlists'][0]['method'] = pairlist
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )
    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
    caplog.clear()

    # Assign starting whitelist
    pairlist_handler = freqtrade.pairlists._pairlist_handlers[0]
    new_whitelist = pairlist_handler._whitelist_for_active_markets(whitelist)

    assert set(new_whitelist) == set(['ETH/BTC', 'TKN/BTC'])
    assert log_message in caplog.text


@pytest.mark.parametrize("pairlist", AVAILABLE_PAIRLISTS)
def test__whitelist_for_active_markets_empty(mocker, whitelist_conf, pairlist, tickers):
    whitelist_conf['pairlists'][0]['method'] = pairlist

    mocker.patch('freqtrade.exchange.Exchange.exchange_has', return_value=True)

    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=None),
                          get_tickers=tickers
                          )
    # Assign starting whitelist
    pairlist_handler = freqtrade.pairlists._pairlist_handlers[0]
    with pytest.raises(OperationalException, match=r'Markets not loaded.*'):
        pairlist_handler._whitelist_for_active_markets(['ETH/BTC'])


def test_volumepairlist_invalid_sortvalue(mocker, whitelist_conf):
    whitelist_conf['pairlists'][0].update({"sort_key": "asdf"})

    mocker.patch('freqtrade.exchange.Exchange.exchange_has', MagicMock(return_value=True))
    with pytest.raises(OperationalException,
                       match=r"key asdf not in .*"):
        get_patched_freqtradebot(mocker, whitelist_conf)


def test_volumepairlist_caching(mocker, markets, whitelist_conf, tickers):

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )
    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
    assert freqtrade.pairlists._pairlist_handlers[0]._last_refresh == 0
    assert tickers.call_count == 0
    freqtrade.pairlists.refresh_pairlist()
    assert tickers.call_count == 1

    assert freqtrade.pairlists._pairlist_handlers[0]._last_refresh != 0
    lrf = freqtrade.pairlists._pairlist_handlers[0]._last_refresh
    freqtrade.pairlists.refresh_pairlist()
    assert tickers.call_count == 1
    # Time should not be updated.
    assert freqtrade.pairlists._pairlist_handlers[0]._last_refresh == lrf


def test_agefilter_min_days_listed_too_small(mocker, default_conf, markets, tickers):
    default_conf['pairlists'] = [{'method': 'VolumePairList', 'number_assets': 10},
                                 {'method': 'AgeFilter', 'min_days_listed': -1}]

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )

    with pytest.raises(OperationalException,
                       match=r'AgeFilter requires min_days_listed to be >= 1'):
        get_patched_freqtradebot(mocker, default_conf)


def test_agefilter_min_days_listed_too_large(mocker, default_conf, markets, tickers):
    default_conf['pairlists'] = [{'method': 'VolumePairList', 'number_assets': 10},
                                 {'method': 'AgeFilter', 'min_days_listed': 99999}]

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )

    with pytest.raises(OperationalException,
                       match=r'AgeFilter requires min_days_listed to not exceed '
                             r'exchange max request size \([0-9]+\)'):
        get_patched_freqtradebot(mocker, default_conf)


def test_agefilter_caching(mocker, markets, whitelist_conf_agefilter, tickers, ohlcv_history):
    ohlcv_data = {
        ('ETH/BTC', '1d'): ohlcv_history,
        ('TKN/BTC', '1d'): ohlcv_history,
        ('LTC/BTC', '1d'): ohlcv_history,
    }
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        refresh_latest_ohlcv=MagicMock(return_value=ohlcv_data),
    )

    freqtrade = get_patched_freqtradebot(mocker, whitelist_conf_agefilter)
    assert freqtrade.exchange.refresh_latest_ohlcv.call_count == 0
    freqtrade.pairlists.refresh_pairlist()
    assert len(freqtrade.pairlists.whitelist) == 3
    assert freqtrade.exchange.refresh_latest_ohlcv.call_count > 0
    # freqtrade.config['exchange']['pair_whitelist'].append('HOT/BTC')

    previous_call_count = freqtrade.exchange.refresh_latest_ohlcv.call_count
    freqtrade.pairlists.refresh_pairlist()
    assert len(freqtrade.pairlists.whitelist) == 3
    # Called once for XRP/BTC
    assert freqtrade.exchange.refresh_latest_ohlcv.call_count == previous_call_count + 1


def test_rangestabilityfilter_checks(mocker, default_conf, markets, tickers):
    default_conf['pairlists'] = [{'method': 'VolumePairList', 'number_assets': 10},
                                 {'method': 'RangeStabilityFilter', 'lookback_days': 99999}]

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )

    with pytest.raises(OperationalException,
                       match=r'RangeStabilityFilter requires lookback_days to not exceed '
                             r'exchange max request size \([0-9]+\)'):
        get_patched_freqtradebot(mocker, default_conf)

    default_conf['pairlists'] = [{'method': 'VolumePairList', 'number_assets': 10},
                                 {'method': 'RangeStabilityFilter', 'lookback_days': 0}]

    with pytest.raises(OperationalException,
                       match='RangeStabilityFilter requires lookback_days to be >= 1'):
        get_patched_freqtradebot(mocker, default_conf)


@pytest.mark.parametrize('min_rate_of_change,expected_length', [
    (0.01, 5),
    (0.05, 0),  # Setting rate_of_change to 5% removes all pairs from the whitelist.
])
def test_rangestabilityfilter_caching(mocker, markets, default_conf, tickers, ohlcv_history,
                                      min_rate_of_change, expected_length):
    default_conf['pairlists'] = [{'method': 'VolumePairList', 'number_assets': 10},
                                 {'method': 'RangeStabilityFilter', 'lookback_days': 2,
                                  'min_rate_of_change': min_rate_of_change}]

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers
                          )
    ohlcv_data = {
        ('ETH/BTC', '1d'): ohlcv_history,
        ('TKN/BTC', '1d'): ohlcv_history,
        ('LTC/BTC', '1d'): ohlcv_history,
        ('XRP/BTC', '1d'): ohlcv_history,
        ('HOT/BTC', '1d'): ohlcv_history,
        ('BLK/BTC', '1d'): ohlcv_history,
    }
    mocker.patch.multiple(
        'freqtrade.exchange.Exchange',
        refresh_latest_ohlcv=MagicMock(return_value=ohlcv_data),
    )

    freqtrade = get_patched_freqtradebot(mocker, default_conf)
    assert freqtrade.exchange.refresh_latest_ohlcv.call_count == 0
    freqtrade.pairlists.refresh_pairlist()
    assert len(freqtrade.pairlists.whitelist) == expected_length
    assert freqtrade.exchange.refresh_latest_ohlcv.call_count > 0

    previous_call_count = freqtrade.exchange.refresh_latest_ohlcv.call_count
    freqtrade.pairlists.refresh_pairlist()
    assert len(freqtrade.pairlists.whitelist) == expected_length
    # Should not have increased since first call.
    assert freqtrade.exchange.refresh_latest_ohlcv.call_count == previous_call_count


@pytest.mark.parametrize("pairlistconfig,desc_expected,exception_expected", [
    ({"method": "PriceFilter", "low_price_ratio": 0.001, "min_price": 0.00000010,
      "max_price": 1.0},
     "[{'PriceFilter': 'PriceFilter - Filtering pairs priced below "
     "0.1% or below 0.00000010 or above 1.00000000.'}]",
     None
     ),
    ({"method": "PriceFilter", "low_price_ratio": 0.001, "min_price": 0.00000010},
     "[{'PriceFilter': 'PriceFilter - Filtering pairs priced below 0.1% or below 0.00000010.'}]",
     None
     ),
    ({"method": "PriceFilter", "low_price_ratio": 0.001, "max_price": 1.00010000},
     "[{'PriceFilter': 'PriceFilter - Filtering pairs priced below 0.1% or above 1.00010000.'}]",
     None
     ),
    ({"method": "PriceFilter", "min_price": 0.00002000},
     "[{'PriceFilter': 'PriceFilter - Filtering pairs priced below 0.00002000.'}]",
     None
     ),
    ({"method": "PriceFilter"},
     "[{'PriceFilter': 'PriceFilter - No price filters configured.'}]",
     None
     ),
    ({"method": "PriceFilter", "low_price_ratio": -0.001},
     None,
     "PriceFilter requires low_price_ratio to be >= 0"
     ),  # OperationalException expected
    ({"method": "PriceFilter", "min_price": -0.00000010},
     None,
     "PriceFilter requires min_price to be >= 0"
     ),  # OperationalException expected
    ({"method": "PriceFilter", "max_price": -1.00010000},
     None,
     "PriceFilter requires max_price to be >= 0"
     ),  # OperationalException expected
    ({"method": "RangeStabilityFilter", "lookback_days": 10, "min_rate_of_change": 0.01},
     "[{'RangeStabilityFilter': 'RangeStabilityFilter - Filtering pairs with rate of change below "
     "0.01 over the last days.'}]",
        None
     ),
])
def test_pricefilter_desc(mocker, whitelist_conf, markets, pairlistconfig,
                          desc_expected, exception_expected):
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          markets=PropertyMock(return_value=markets),
                          exchange_has=MagicMock(return_value=True)
                          )
    whitelist_conf['pairlists'] = [pairlistconfig]

    if desc_expected is not None:
        freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)
        short_desc = str(freqtrade.pairlists.short_desc())
        assert short_desc == desc_expected
    else:  # OperationalException expected
        with pytest.raises(OperationalException,
                           match=exception_expected):
            freqtrade = get_patched_freqtradebot(mocker, whitelist_conf)


def test_pairlistmanager_no_pairlist(mocker, whitelist_conf):
    mocker.patch('freqtrade.exchange.Exchange.exchange_has', MagicMock(return_value=True))

    whitelist_conf['pairlists'] = []

    with pytest.raises(OperationalException,
                       match=r"No Pairlist Handlers defined"):
        get_patched_freqtradebot(mocker, whitelist_conf)


@pytest.mark.parametrize("pairlists,pair_allowlist,overall_performance,allowlist_result", [
    # No trades yet
    ([{"method": "StaticPairList"}, {"method": "PerformanceFilter"}],
     ['ETH/BTC', 'TKN/BTC', 'LTC/BTC'], [], ['ETH/BTC', 'TKN/BTC', 'LTC/BTC']),
    # Happy path: Descending order, all values filled
    ([{"method": "StaticPairList"}, {"method": "PerformanceFilter"}],
     ['ETH/BTC', 'TKN/BTC'],
     [{'pair': 'TKN/BTC', 'profit': 5, 'count': 3}, {'pair': 'ETH/BTC', 'profit': 4, 'count': 2}],
     ['TKN/BTC', 'ETH/BTC']),
    # Performance data outside allow list ignored
    ([{"method": "StaticPairList"}, {"method": "PerformanceFilter"}],
     ['ETH/BTC', 'TKN/BTC'],
     [{'pair': 'OTHER/BTC', 'profit': 5, 'count': 3},
      {'pair': 'ETH/BTC', 'profit': 4, 'count': 2}],
     ['ETH/BTC', 'TKN/BTC']),
    # Partial performance data missing and sorted between positive and negative profit
    ([{"method": "StaticPairList"}, {"method": "PerformanceFilter"}],
     ['ETH/BTC', 'TKN/BTC', 'LTC/BTC'],
     [{'pair': 'ETH/BTC', 'profit': -5, 'count': 100},
      {'pair': 'TKN/BTC', 'profit': 4, 'count': 2}],
     ['TKN/BTC', 'LTC/BTC', 'ETH/BTC']),
    # Tie in performance data broken by count (ascending)
    ([{"method": "StaticPairList"}, {"method": "PerformanceFilter"}],
     ['ETH/BTC', 'TKN/BTC', 'LTC/BTC'],
     [{'pair': 'LTC/BTC', 'profit': -5.01, 'count': 101},
      {'pair': 'TKN/BTC', 'profit': -5.01, 'count': 2},
      {'pair': 'ETH/BTC', 'profit': -5.01, 'count': 100}],
     ['TKN/BTC', 'ETH/BTC', 'LTC/BTC']),
    # Tie in performance and count, broken by alphabetical sort
    ([{"method": "StaticPairList"}, {"method": "PerformanceFilter"}],
     ['ETH/BTC', 'TKN/BTC', 'LTC/BTC'],
     [{'pair': 'LTC/BTC', 'profit': -5.01, 'count': 1},
      {'pair': 'TKN/BTC', 'profit': -5.01, 'count': 1},
      {'pair': 'ETH/BTC', 'profit': -5.01, 'count': 1}],
     ['ETH/BTC', 'LTC/BTC', 'TKN/BTC']),
])
def test_performance_filter(mocker, whitelist_conf, pairlists, pair_allowlist, overall_performance,
                            allowlist_result, tickers, markets, ohlcv_history_list):
    allowlist_conf = whitelist_conf
    allowlist_conf['pairlists'] = pairlists
    allowlist_conf['exchange']['pair_whitelist'] = pair_allowlist

    mocker.patch('freqtrade.exchange.Exchange.exchange_has', MagicMock(return_value=True))

    freqtrade = get_patched_freqtradebot(mocker, allowlist_conf)
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          get_tickers=tickers,
                          markets=PropertyMock(return_value=markets)
                          )
    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          get_historic_ohlcv=MagicMock(return_value=ohlcv_history_list),
                          )
    mocker.patch.multiple('freqtrade.persistence.Trade',
                          get_overall_performance=MagicMock(return_value=overall_performance),
                          )
    freqtrade.pairlists.refresh_pairlist()
    allowlist = freqtrade.pairlists.whitelist
    assert allowlist == allowlist_result


@pytest.mark.parametrize('wildcardlist,pairs,expected', [
    (['BTC/USDT'],
     ['BTC/USDT'],
     ['BTC/USDT']),
    (['BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETH/USDT']),
    (['BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT'], ['BTC/USDT']),  # Test one too many
    (['.*/USDT'],
     ['BTC/USDT', 'ETH/USDT'], ['BTC/USDT', 'ETH/USDT']),  # Wildcard simple
    (['.*C/USDT'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT'], ['BTC/USDT', 'ETC/USDT']),  # Wildcard exclude one
    (['.*UP/USDT', 'BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT', 'BTCUP/USDT', 'XRPUP/USDT', 'XRPDOWN/USDT'],
     ['BTC/USDT', 'ETH/USDT', 'BTCUP/USDT', 'XRPUP/USDT']),  # Wildcard exclude one
    (['BTC/.*', 'ETH/.*'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT', 'BTC/USD', 'ETH/EUR', 'BTC/GBP'],
     ['BTC/USDT', 'ETH/USDT', 'BTC/USD', 'ETH/EUR', 'BTC/GBP']),  # Wildcard exclude one
    (['*UP/USDT', 'BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT', 'BTCUP/USDT', 'XRPUP/USDT', 'XRPDOWN/USDT'],
     None),
])
def test_expand_pairlist(wildcardlist, pairs, expected):
    if expected is None:
        with pytest.raises(ValueError, match=r'Wildcard error in \*UP/USDT,'):
            expand_pairlist(wildcardlist, pairs)
    else:
        assert sorted(expand_pairlist(wildcardlist, pairs)) == sorted(expected)


@pytest.mark.parametrize('wildcardlist,pairs,expected', [
    (['BTC/USDT'],
     ['BTC/USDT'],
     ['BTC/USDT']),
    (['BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETH/USDT']),
    (['BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT'], ['BTC/USDT', 'ETH/USDT']),  # Test one too many
    (['.*/USDT'],
     ['BTC/USDT', 'ETH/USDT'], ['BTC/USDT', 'ETH/USDT']),  # Wildcard simple
    (['.*C/USDT'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT'], ['BTC/USDT', 'ETC/USDT']),  # Wildcard exclude one
    (['.*UP/USDT', 'BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT', 'BTCUP/USDT', 'XRPUP/USDT', 'XRPDOWN/USDT'],
     ['BTC/USDT', 'ETH/USDT', 'BTCUP/USDT', 'XRPUP/USDT']),  # Wildcard exclude one
    (['BTC/.*', 'ETH/.*'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT', 'BTC/USD', 'ETH/EUR', 'BTC/GBP'],
     ['BTC/USDT', 'ETH/USDT', 'BTC/USD', 'ETH/EUR', 'BTC/GBP']),  # Wildcard exclude one
    (['*UP/USDT', 'BTC/USDT', 'ETH/USDT'],
     ['BTC/USDT', 'ETC/USDT', 'ETH/USDT', 'BTCUP/USDT', 'XRPUP/USDT', 'XRPDOWN/USDT'],
     None),
    (['HELLO/WORLD'], [], ['HELLO/WORLD'])  # Invalid pair kept
])
def test_expand_pairlist_keep_invalid(wildcardlist, pairs, expected):
    if expected is None:
        with pytest.raises(ValueError, match=r'Wildcard error in \*UP/USDT,'):
            expand_pairlist(wildcardlist, pairs, keep_invalid=True)
    else:
        assert sorted(expand_pairlist(wildcardlist, pairs, keep_invalid=True)) == sorted(expected)
