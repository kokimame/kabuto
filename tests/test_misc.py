# pragma pylint: disable=missing-docstring,C0103

import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from freqtrade.data.converter import ohlcv_to_dataframe
from freqtrade.misc import (datesarray_to_datetimearray, file_dump_json,
                            file_load_json, format_ms_time, pair_to_filename,
                            plural, safe_value_fallback, shorten_date)


def test_shorten_date() -> None:
    str_data = '1 day, 2 hours, 3 minutes, 4 seconds ago'
    str_shorten_data = '1 d, 2 h, 3 min, 4 sec ago'
    assert shorten_date(str_data) == str_shorten_data


def test_datesarray_to_datetimearray(ohlcv_history_list):
    dataframes = ohlcv_to_dataframe(ohlcv_history_list, "5m", pair="UNITTEST/BTC",
                                    fill_missing=True)
    dates = datesarray_to_datetimearray(dataframes['date'])

    assert isinstance(dates[0], datetime.datetime)
    assert dates[0].year == 2017
    assert dates[0].month == 11
    assert dates[0].day == 26
    assert dates[0].hour == 8
    assert dates[0].minute == 50

    date_len = len(dates)
    assert date_len == 2


def test_file_dump_json(mocker) -> None:
    file_open = mocker.patch('freqtrade.misc.open', MagicMock())
    json_dump = mocker.patch('rapidjson.dump', MagicMock())
    file_dump_json(Path('somefile'), [1, 2, 3])
    assert file_open.call_count == 1
    assert json_dump.call_count == 1
    file_open = mocker.patch('freqtrade.misc.gzip.open', MagicMock())
    json_dump = mocker.patch('rapidjson.dump', MagicMock())
    file_dump_json(Path('somefile'), [1, 2, 3], True)
    assert file_open.call_count == 1
    assert json_dump.call_count == 1


def test_file_load_json(mocker, testdatadir) -> None:

    # 7m .json does not exist
    ret = file_load_json(testdatadir / 'UNITTEST_BTC-7m.json')
    assert not ret
    # 1m json exists (but no .gz exists)
    ret = file_load_json(testdatadir / 'UNITTEST_BTC-1m.json')
    assert ret
    # 8 .json is empty and will fail if it's loaded. .json.gz is a copy of 1.json
    ret = file_load_json(testdatadir / 'UNITTEST_BTC-8m.json')
    assert ret


@pytest.mark.parametrize("pair,expected_result", [
    ("ETH/BTC", 'ETH_BTC'),
    ("Fabric Token/ETH", 'Fabric_Token_ETH'),
    ("ETHH20", 'ETHH20'),
    (".XBTBON2H", '_XBTBON2H'),
    ("ETHUSD.d", 'ETHUSD_d'),
    ("ADA-0327", 'ADA_0327'),
    ("BTC-USD-200110", 'BTC_USD_200110'),
    ("F-AKRO/USDT", 'F_AKRO_USDT'),
    ("LC+/ETH", 'LC__ETH'),
    ("CMT@18/ETH", 'CMT_18_ETH'),
    ("LBTC:1022/SAI", 'LBTC_1022_SAI'),
    ("$PAC/BTC", '_PAC_BTC'),
    ("ACC_OLD/BTC", 'ACC_OLD_BTC'),
])
def test_pair_to_filename(pair, expected_result):
    pair_s = pair_to_filename(pair)
    assert pair_s == expected_result


def test_format_ms_time() -> None:
    # Date 2018-04-10 18:02:01
    date_in_epoch_ms = 1523383321000
    date = format_ms_time(date_in_epoch_ms)
    assert type(date) is str
    res = datetime.datetime(2018, 4, 10, 18, 2, 1, tzinfo=datetime.timezone.utc)
    assert date == res.astimezone(None).strftime('%Y-%m-%dT%H:%M:%S')
    res = datetime.datetime(2017, 12, 13, 8, 2, 1, tzinfo=datetime.timezone.utc)
    # Date 2017-12-13 08:02:01
    date_in_epoch_ms = 1513152121000
    assert format_ms_time(date_in_epoch_ms) == res.astimezone(None).strftime('%Y-%m-%dT%H:%M:%S')


def test_safe_value_fallback():
    dict1 = {'keya': None, 'keyb': 2, 'keyc': 5, 'keyd': None}
    dict2 = {'keya': 20, 'keyb': None, 'keyc': 6, 'keyd': None}
    assert safe_value_fallback(dict1, dict2, 'keya', 'keya') == 20
    assert safe_value_fallback(dict2, dict1, 'keya', 'keya') == 20

    assert safe_value_fallback(dict1, dict2, 'keyb', 'keyb') == 2
    assert safe_value_fallback(dict2, dict1, 'keyb', 'keyb') == 2

    assert safe_value_fallback(dict1, dict2, 'keyc', 'keyc') == 5
    assert safe_value_fallback(dict2, dict1, 'keyc', 'keyc') == 6

    assert safe_value_fallback(dict1, dict2, 'keyd', 'keyd') is None
    assert safe_value_fallback(dict2, dict1, 'keyd', 'keyd') is None
    assert safe_value_fallback(dict2, dict1, 'keyd', 'keyd', 1234) == 1234

    assert safe_value_fallback(dict1, dict2, 'keyNo', 'keyNo') is None
    assert safe_value_fallback(dict2, dict1, 'keyNo', 'keyNo') is None
    assert safe_value_fallback(dict2, dict1, 'keyNo', 'keyNo', 1234) == 1234


def test_plural() -> None:
    assert plural(0, "page") == "pages"
    assert plural(0.0, "page") == "pages"
    assert plural(1, "page") == "page"
    assert plural(1.0, "page") == "page"
    assert plural(2, "page") == "pages"
    assert plural(2.0, "page") == "pages"
    assert plural(-1, "page") == "page"
    assert plural(-1.0, "page") == "page"
    assert plural(-2, "page") == "pages"
    assert plural(-2.0, "page") == "pages"
    assert plural(0.5, "page") == "pages"
    assert plural(1.5, "page") == "pages"
    assert plural(-0.5, "page") == "pages"
    assert plural(-1.5, "page") == "pages"

    assert plural(0, "ox", "oxen") == "oxen"
    assert plural(0.0, "ox", "oxen") == "oxen"
    assert plural(1, "ox", "oxen") == "ox"
    assert plural(1.0, "ox", "oxen") == "ox"
    assert plural(2, "ox", "oxen") == "oxen"
    assert plural(2.0, "ox", "oxen") == "oxen"
    assert plural(-1, "ox", "oxen") == "ox"
    assert plural(-1.0, "ox", "oxen") == "ox"
    assert plural(-2, "ox", "oxen") == "oxen"
    assert plural(-2.0, "ox", "oxen") == "oxen"
    assert plural(0.5, "ox", "oxen") == "oxen"
    assert plural(1.5, "ox", "oxen") == "oxen"
    assert plural(-0.5, "ox", "oxen") == "oxen"
    assert plural(-1.5, "ox", "oxen") == "oxen"
