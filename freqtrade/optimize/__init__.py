# pragma pylint: disable=missing-docstring

import gzip
import json
import logging
import os
from typing import Optional, List, Dict, Tuple

from freqtrade import misc
from freqtrade.exchange import get_ticker_history
from user_data.hyperopt_conf import hyperopt_optimize_conf

logger = logging.getLogger(__name__)


def trim_tickerlist(tickerlist: List[Dict], timerange: Tuple[Tuple, int, int]) -> List[Dict]:
    stype, start, stop = timerange
    if stype == (None, 'line'):
        return tickerlist[stop:]
    elif stype == ('line', None):
        return tickerlist[0:start]
    elif stype == ('index', 'index'):
        return tickerlist[start:stop]

    return tickerlist


def load_tickerdata_file(
        datadir: str, pair: str,
        ticker_interval: int,
        timerange: Optional[Tuple[Tuple, int, int]] = None) -> Optional[List[Dict]]:
    """
    Load a pair from file,
    :return dict OR empty if unsuccesful
    """
    path = make_testdata_path(datadir)
    file = os.path.join(path, '{pair}-{ticker_interval}.json'.format(
        pair=pair,
        ticker_interval=ticker_interval,
    ))
    gzipfile = file + '.gz'

    # If the file does not exist we download it when None is returned.
    # If file exists, read the file, load the json
    if os.path.isfile(gzipfile):
        logger.debug('Loading ticker data from file %s', gzipfile)
        with gzip.open(gzipfile) as tickerdata:
            pairdata = json.load(tickerdata)
    elif os.path.isfile(file):
        logger.debug('Loading ticker data from file %s', file)
        with open(file) as tickerdata:
            pairdata = json.load(tickerdata)
    else:
        return None

    if timerange:
        pairdata = trim_tickerlist(pairdata, timerange)
    return pairdata


def load_data(datadir: str, ticker_interval: int,
              pairs: Optional[List[str]] = None,
              refresh_pairs: Optional[bool] = False,
              timerange: Optional[Tuple[Tuple, int, int]] = None) -> Dict[str, List]:
    """
    Loads ticker history data for the given parameters
    :return: dict
    """
    result = {}

    _pairs = pairs or hyperopt_optimize_conf()['exchange']['pair_whitelist']

    # If the user force the refresh of pairs
    if refresh_pairs:
        logger.info('Download data for all pairs and store them in %s', datadir)
        download_pairs(datadir, _pairs, ticker_interval)

    for pair in _pairs:
        pairdata = load_tickerdata_file(datadir, pair, ticker_interval, timerange=timerange)
        if not pairdata:
            # download the tickerdata from exchange
            download_backtesting_testdata(datadir, pair=pair, interval=ticker_interval)
            # and retry reading the pair
            pairdata = load_tickerdata_file(datadir, pair, ticker_interval, timerange=timerange)
        result[pair] = pairdata
    return result


def make_testdata_path(datadir: str) -> str:
    """Return the path where testdata files are stored"""
    return datadir or os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', 'tests', 'testdata'
        )
    )


def download_pairs(datadir, pairs: List[str], ticker_interval: int) -> bool:
    """For each pairs passed in parameters, download the ticker intervals"""
    for pair in pairs:
        try:
            download_backtesting_testdata(datadir, pair=pair, interval=ticker_interval)
        except BaseException:
            logger.info(
                'Failed to download the pair: "%s", Interval: %s min',
                pair,
                ticker_interval
            )
            return False
    return True


# FIX: 20180110, suggest rename interval to tick_interval
def download_backtesting_testdata(datadir: str, pair: str, interval: int = 5) -> None:
    """
    Download the latest 1 and 5 ticker intervals from Bittrex for the pairs passed in parameters
    Based on @Rybolov work: https://github.com/rybolov/freqtrade-data
    """

    path = make_testdata_path(datadir)
    logger.info(
        'Download the pair: "%s", Interval: %s min', pair, interval
    )

    filename = os.path.join(path, '{pair}-{interval}.json'.format(
        pair=pair.replace("-", "_"),
        interval=interval,
    ))

    if os.path.isfile(filename):
        with open(filename, "rt") as file:
            data = json.load(file)
    else:
        data = []

    logger.debug('Current Start: %s', data[1]['T'] if data else None)
    logger.debug('Current End: %s', data[-1:][0]['T'] if data else None)

    # Extend data with new ticker history
    data.extend([
        row for row in get_ticker_history(pair=pair, tick_interval=int(interval))
        if row not in data
    ])

    data = sorted(data, key=lambda _data: _data['T'])
    logger.debug('New Start: %s', data[1]['T'])
    logger.debug('New End: %s', data[-1:][0]['T'])
    misc.file_dump_json(filename, data)
