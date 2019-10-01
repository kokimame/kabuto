# pragma pylint: disable=missing-docstring, too-many-arguments, too-many-ancestors,
# pragma pylint: disable=protected-access, C0103

import time
from unittest.mock import MagicMock

import pytest
from requests.exceptions import RequestException

from freqtrade.rpc.fiat_convert import CryptoFiat, CryptoToFiatConverter
from tests.conftest import log_has


def test_pair_convertion_object():
    pair_convertion = CryptoFiat(
        crypto_symbol='btc',
        fiat_symbol='usd',
        price=12345.0
    )

    # Check the cache duration is 6 hours
    assert pair_convertion.CACHE_DURATION == 6 * 60 * 60

    # Check a regular usage
    assert pair_convertion.crypto_symbol == 'BTC'
    assert pair_convertion.fiat_symbol == 'USD'
    assert pair_convertion.price == 12345.0
    assert pair_convertion.is_expired() is False

    # Update the expiration time (- 2 hours) and check the behavior
    pair_convertion._expiration = time.time() - 2 * 60 * 60
    assert pair_convertion.is_expired() is True

    # Check set price behaviour
    time_reference = time.time() + pair_convertion.CACHE_DURATION
    pair_convertion.set_price(price=30000.123)
    assert pair_convertion.is_expired() is False
    assert pair_convertion._expiration >= time_reference
    assert pair_convertion.price == 30000.123


def test_fiat_convert_is_supported(mocker):
    fiat_convert = CryptoToFiatConverter()
    assert fiat_convert._is_supported_fiat(fiat='USD') is True
    assert fiat_convert._is_supported_fiat(fiat='usd') is True
    assert fiat_convert._is_supported_fiat(fiat='abc') is False
    assert fiat_convert._is_supported_fiat(fiat='ABC') is False


def test_fiat_convert_add_pair(mocker):

    fiat_convert = CryptoToFiatConverter()

    pair_len = len(fiat_convert._pairs)
    assert pair_len == 0

    fiat_convert._add_pair(crypto_symbol='btc', fiat_symbol='usd', price=12345.0)
    pair_len = len(fiat_convert._pairs)
    assert pair_len == 1
    assert fiat_convert._pairs[0].crypto_symbol == 'BTC'
    assert fiat_convert._pairs[0].fiat_symbol == 'USD'
    assert fiat_convert._pairs[0].price == 12345.0

    fiat_convert._add_pair(crypto_symbol='btc', fiat_symbol='Eur', price=13000.2)
    pair_len = len(fiat_convert._pairs)
    assert pair_len == 2
    assert fiat_convert._pairs[1].crypto_symbol == 'BTC'
    assert fiat_convert._pairs[1].fiat_symbol == 'EUR'
    assert fiat_convert._pairs[1].price == 13000.2


def test_fiat_convert_find_price(mocker):
    fiat_convert = CryptoToFiatConverter()

    with pytest.raises(ValueError, match=r'The fiat ABC is not supported.'):
        fiat_convert._find_price(crypto_symbol='BTC', fiat_symbol='ABC')

    assert fiat_convert.get_price(crypto_symbol='XRP', fiat_symbol='USD') == 0.0

    mocker.patch('freqtrade.rpc.fiat_convert.CryptoToFiatConverter._find_price',
                 return_value=12345.0)
    assert fiat_convert.get_price(crypto_symbol='BTC', fiat_symbol='USD') == 12345.0
    assert fiat_convert.get_price(crypto_symbol='btc', fiat_symbol='usd') == 12345.0

    mocker.patch('freqtrade.rpc.fiat_convert.CryptoToFiatConverter._find_price',
                 return_value=13000.2)
    assert fiat_convert.get_price(crypto_symbol='BTC', fiat_symbol='EUR') == 13000.2


def test_fiat_convert_unsupported_crypto(mocker, caplog):
    mocker.patch('freqtrade.rpc.fiat_convert.CryptoToFiatConverter._cryptomap', return_value=[])
    fiat_convert = CryptoToFiatConverter()
    assert fiat_convert._find_price(crypto_symbol='CRYPTO_123', fiat_symbol='EUR') == 0.0
    assert log_has('unsupported crypto-symbol CRYPTO_123 - returning 0.0', caplog)


def test_fiat_convert_get_price(mocker):
    mocker.patch('freqtrade.rpc.fiat_convert.CryptoToFiatConverter._find_price',
                 return_value=28000.0)

    fiat_convert = CryptoToFiatConverter()

    with pytest.raises(ValueError, match=r'The fiat US DOLLAR is not supported.'):
        fiat_convert.get_price(crypto_symbol='BTC', fiat_symbol='US Dollar')

    # Check the value return by the method
    pair_len = len(fiat_convert._pairs)
    assert pair_len == 0
    assert fiat_convert.get_price(crypto_symbol='BTC', fiat_symbol='USD') == 28000.0
    assert fiat_convert._pairs[0].crypto_symbol == 'BTC'
    assert fiat_convert._pairs[0].fiat_symbol == 'USD'
    assert fiat_convert._pairs[0].price == 28000.0
    assert fiat_convert._pairs[0]._expiration != 0
    assert len(fiat_convert._pairs) == 1

    # Verify the cached is used
    fiat_convert._pairs[0].price = 9867.543
    expiration = fiat_convert._pairs[0]._expiration
    assert fiat_convert.get_price(crypto_symbol='BTC', fiat_symbol='USD') == 9867.543
    assert fiat_convert._pairs[0]._expiration == expiration

    # Verify the cache expiration
    expiration = time.time() - 2 * 60 * 60
    fiat_convert._pairs[0]._expiration = expiration
    assert fiat_convert.get_price(crypto_symbol='BTC', fiat_symbol='USD') == 28000.0
    assert fiat_convert._pairs[0]._expiration is not expiration


def test_fiat_convert_same_currencies(mocker):
    fiat_convert = CryptoToFiatConverter()

    assert fiat_convert.get_price(crypto_symbol='USD', fiat_symbol='USD') == 1.0


def test_fiat_convert_two_FIAT(mocker):
    fiat_convert = CryptoToFiatConverter()

    assert fiat_convert.get_price(crypto_symbol='USD', fiat_symbol='EUR') == 0.0


def test_loadcryptomap(mocker):

    fiat_convert = CryptoToFiatConverter()
    assert len(fiat_convert._cryptomap) == 2

    assert fiat_convert._cryptomap["BTC"] == "1"


def test_fiat_init_network_exception(mocker):
    # Because CryptoToFiatConverter is a Singleton we reset the listings
    listmock = MagicMock(side_effect=RequestException)
    mocker.patch.multiple(
        'freqtrade.rpc.fiat_convert.Market',
        listings=listmock,
    )
    # with pytest.raises(RequestEsxception):
    fiat_convert = CryptoToFiatConverter()
    fiat_convert._cryptomap = {}
    fiat_convert._load_cryptomap()

    length_cryptomap = len(fiat_convert._cryptomap)
    assert length_cryptomap == 0


def test_fiat_convert_without_network(mocker):
    # Because CryptoToFiatConverter is a Singleton we reset the value of _coinmarketcap

    fiat_convert = CryptoToFiatConverter()

    cmc_temp = CryptoToFiatConverter._coinmarketcap
    CryptoToFiatConverter._coinmarketcap = None

    assert fiat_convert._coinmarketcap is None
    assert fiat_convert._find_price(crypto_symbol='BTC', fiat_symbol='USD') == 0.0
    CryptoToFiatConverter._coinmarketcap = cmc_temp


def test_fiat_invalid_response(mocker, caplog):
    # Because CryptoToFiatConverter is a Singleton we reset the listings
    listmock = MagicMock(return_value="{'novalidjson':DEADBEEFf}")
    mocker.patch.multiple(
        'freqtrade.rpc.fiat_convert.Market',
        listings=listmock,
    )
    # with pytest.raises(RequestEsxception):
    fiat_convert = CryptoToFiatConverter()
    fiat_convert._cryptomap = {}
    fiat_convert._load_cryptomap()

    length_cryptomap = len(fiat_convert._cryptomap)
    assert length_cryptomap == 0
    assert log_has('Could not load FIAT Cryptocurrency map for the following problem: TypeError',
                   caplog)


def test_convert_amount(mocker):
    mocker.patch('freqtrade.rpc.fiat_convert.CryptoToFiatConverter.get_price', return_value=12345.0)

    fiat_convert = CryptoToFiatConverter()
    result = fiat_convert.convert_amount(
        crypto_amount=1.23,
        crypto_symbol="BTC",
        fiat_symbol="USD"
    )
    assert result == 15184.35

    result = fiat_convert.convert_amount(
        crypto_amount=1.23,
        crypto_symbol="BTC",
        fiat_symbol="BTC"
    )
    assert result == 1.23

    result = fiat_convert.convert_amount(
        crypto_amount="1.23",
        crypto_symbol="BTC",
        fiat_symbol="BTC"
    )
    assert result == 1.23
