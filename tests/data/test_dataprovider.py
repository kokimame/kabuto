from unittest.mock import MagicMock

from pandas import DataFrame
import pytest

from freqtrade.data.dataprovider import DataProvider
from freqtrade.pairlist.pairlistmanager import PairListManager
from freqtrade.exceptions import DependencyException, OperationalException
from freqtrade.state import RunMode
from tests.conftest import get_patched_exchange


def test_ohlcv(mocker, default_conf, ohlcv_history):
    default_conf["runmode"] = RunMode.DRY_RUN
    timeframe = default_conf["timeframe"]
    exchange = get_patched_exchange(mocker, default_conf)
    exchange._klines[("XRP/BTC", timeframe)] = ohlcv_history
    exchange._klines[("UNITTEST/BTC", timeframe)] = ohlcv_history

    dp = DataProvider(default_conf, exchange)
    assert dp.runmode == RunMode.DRY_RUN
    assert ohlcv_history.equals(dp.ohlcv("UNITTEST/BTC", timeframe))
    assert isinstance(dp.ohlcv("UNITTEST/BTC", timeframe), DataFrame)
    assert dp.ohlcv("UNITTEST/BTC", timeframe) is not ohlcv_history
    assert dp.ohlcv("UNITTEST/BTC", timeframe, copy=False) is ohlcv_history
    assert not dp.ohlcv("UNITTEST/BTC", timeframe).empty
    assert dp.ohlcv("NONESENSE/AAA", timeframe).empty

    # Test with and without parameter
    assert dp.ohlcv("UNITTEST/BTC", timeframe).equals(dp.ohlcv("UNITTEST/BTC"))

    default_conf["runmode"] = RunMode.LIVE
    dp = DataProvider(default_conf, exchange)
    assert dp.runmode == RunMode.LIVE
    assert isinstance(dp.ohlcv("UNITTEST/BTC", timeframe), DataFrame)

    default_conf["runmode"] = RunMode.BACKTEST
    dp = DataProvider(default_conf, exchange)
    assert dp.runmode == RunMode.BACKTEST
    assert dp.ohlcv("UNITTEST/BTC", timeframe).empty


def test_historic_ohlcv(mocker, default_conf, ohlcv_history):
    historymock = MagicMock(return_value=ohlcv_history)
    mocker.patch("freqtrade.data.dataprovider.load_pair_history", historymock)

    dp = DataProvider(default_conf, None)
    data = dp.historic_ohlcv("UNITTEST/BTC", "5m")
    assert isinstance(data, DataFrame)
    assert historymock.call_count == 1
    assert historymock.call_args_list[0][1]["timeframe"] == "5m"


def test_get_pair_dataframe(mocker, default_conf, ohlcv_history):
    default_conf["runmode"] = RunMode.DRY_RUN
    timeframe = default_conf["timeframe"]
    exchange = get_patched_exchange(mocker, default_conf)
    exchange._klines[("XRP/BTC", timeframe)] = ohlcv_history
    exchange._klines[("UNITTEST/BTC", timeframe)] = ohlcv_history

    dp = DataProvider(default_conf, exchange)
    assert dp.runmode == RunMode.DRY_RUN
    assert ohlcv_history.equals(dp.get_pair_dataframe("UNITTEST/BTC", timeframe))
    assert isinstance(dp.get_pair_dataframe("UNITTEST/BTC", timeframe), DataFrame)
    assert dp.get_pair_dataframe("UNITTEST/BTC", timeframe) is not ohlcv_history
    assert not dp.get_pair_dataframe("UNITTEST/BTC", timeframe).empty
    assert dp.get_pair_dataframe("NONESENSE/AAA", timeframe).empty

    # Test with and without parameter
    assert dp.get_pair_dataframe("UNITTEST/BTC", timeframe)\
        .equals(dp.get_pair_dataframe("UNITTEST/BTC"))

    default_conf["runmode"] = RunMode.LIVE
    dp = DataProvider(default_conf, exchange)
    assert dp.runmode == RunMode.LIVE
    assert isinstance(dp.get_pair_dataframe("UNITTEST/BTC", timeframe), DataFrame)
    assert dp.get_pair_dataframe("NONESENSE/AAA", timeframe).empty

    historymock = MagicMock(return_value=ohlcv_history)
    mocker.patch("freqtrade.data.dataprovider.load_pair_history", historymock)
    default_conf["runmode"] = RunMode.BACKTEST
    dp = DataProvider(default_conf, exchange)
    assert dp.runmode == RunMode.BACKTEST
    assert isinstance(dp.get_pair_dataframe("UNITTEST/BTC", timeframe), DataFrame)
    # assert dp.get_pair_dataframe("NONESENSE/AAA", timeframe).empty


def test_available_pairs(mocker, default_conf, ohlcv_history):
    exchange = get_patched_exchange(mocker, default_conf)
    timeframe = default_conf["timeframe"]
    exchange._klines[("XRP/BTC", timeframe)] = ohlcv_history
    exchange._klines[("UNITTEST/BTC", timeframe)] = ohlcv_history

    dp = DataProvider(default_conf, exchange)
    assert len(dp.available_pairs) == 2
    assert dp.available_pairs == [("XRP/BTC", timeframe), ("UNITTEST/BTC", timeframe), ]


def test_refresh(mocker, default_conf, ohlcv_history):
    refresh_mock = MagicMock()
    mocker.patch("freqtrade.exchange.Exchange.refresh_latest_ohlcv", refresh_mock)

    exchange = get_patched_exchange(mocker, default_conf, id="binance")
    timeframe = default_conf["timeframe"]
    pairs = [("XRP/BTC", timeframe), ("UNITTEST/BTC", timeframe)]

    pairs_non_trad = [("ETH/USDT", timeframe), ("BTC/TUSD", "1h")]

    dp = DataProvider(default_conf, exchange)
    dp.refresh(pairs)

    assert refresh_mock.call_count == 1
    assert len(refresh_mock.call_args[0]) == 1
    assert len(refresh_mock.call_args[0][0]) == len(pairs)
    assert refresh_mock.call_args[0][0] == pairs

    refresh_mock.reset_mock()
    dp.refresh(pairs, pairs_non_trad)
    assert refresh_mock.call_count == 1
    assert len(refresh_mock.call_args[0]) == 1
    assert len(refresh_mock.call_args[0][0]) == len(pairs) + len(pairs_non_trad)
    assert refresh_mock.call_args[0][0] == pairs + pairs_non_trad


def test_orderbook(mocker, default_conf, order_book_l2):
    api_mock = MagicMock()
    api_mock.fetch_l2_order_book = order_book_l2
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock)

    dp = DataProvider(default_conf, exchange)
    res = dp.orderbook('ETH/BTC', 5)
    assert order_book_l2.call_count == 1
    assert order_book_l2.call_args_list[0][0][0] == 'ETH/BTC'
    assert order_book_l2.call_args_list[0][0][1] == 5

    assert type(res) is dict
    assert 'bids' in res
    assert 'asks' in res


def test_market(mocker, default_conf, markets):
    api_mock = MagicMock()
    api_mock.markets = markets
    exchange = get_patched_exchange(mocker, default_conf, api_mock=api_mock)

    dp = DataProvider(default_conf, exchange)
    res = dp.market('ETH/BTC')

    assert type(res) is dict
    assert 'symbol' in res
    assert res['symbol'] == 'ETH/BTC'

    res = dp.market('UNITTEST/BTC')
    assert res is None


def test_ticker(mocker, default_conf, tickers):
    ticker_mock = MagicMock(return_value=tickers()['ETH/BTC'])
    mocker.patch("freqtrade.exchange.Exchange.fetch_ticker", ticker_mock)
    exchange = get_patched_exchange(mocker, default_conf)
    dp = DataProvider(default_conf, exchange)
    res = dp.ticker('ETH/BTC')
    assert type(res) is dict
    assert 'symbol' in res
    assert res['symbol'] == 'ETH/BTC'

    ticker_mock = MagicMock(side_effect=DependencyException('Pair not found'))
    mocker.patch("freqtrade.exchange.Exchange.fetch_ticker", ticker_mock)
    exchange = get_patched_exchange(mocker, default_conf)
    dp = DataProvider(default_conf, exchange)
    res = dp.ticker('UNITTEST/BTC')
    assert res == {}


def test_current_whitelist(mocker, default_conf, tickers):
    # patch default conf to volumepairlist
    default_conf['pairlists'][0] = {'method': 'VolumePairList', "number_assets": 5}

    mocker.patch.multiple('freqtrade.exchange.Exchange',
                          exchange_has=MagicMock(return_value=True),
                          get_tickers=tickers)
    exchange = get_patched_exchange(mocker, default_conf)

    pairlist = PairListManager(exchange, default_conf)
    dp = DataProvider(default_conf, exchange, pairlist)

    # Simulate volumepairs from exchange.
    pairlist.refresh_pairlist()

    assert dp.current_whitelist() == pairlist._whitelist
    # The identity of the 2 lists should be identical
    assert dp.current_whitelist() is pairlist._whitelist

    with pytest.raises(OperationalException):
        dp = DataProvider(default_conf, exchange)
        dp.current_whitelist()
