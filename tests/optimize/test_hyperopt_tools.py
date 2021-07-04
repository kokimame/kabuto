import logging
import re
from pathlib import Path
from typing import Dict, List

import numpy as np
import pytest
import rapidjson

from freqtrade.constants import FTHYPT_FILEVERSION
from freqtrade.exceptions import OperationalException
from freqtrade.optimize.hyperopt_tools import HyperoptTools, hyperopt_serializer
from tests.conftest import log_has, log_has_re


# Functions for recurrent object patching
def create_results() -> List[Dict]:

    return [{'loss': 1, 'result': 'foo', 'params': {}, 'is_best': True}]


def test_save_results_saves_epochs(hyperopt, tmpdir, caplog) -> None:
    # Test writing to temp dir and reading again
    epochs = create_results()
    hyperopt.results_file = Path(tmpdir / 'ut_results.fthypt')

    caplog.set_level(logging.DEBUG)

    for epoch in epochs:
        hyperopt._save_result(epoch)
    assert log_has(f"1 epoch saved to '{hyperopt.results_file}'.", caplog)

    hyperopt._save_result(epochs[0])
    assert log_has(f"2 epochs saved to '{hyperopt.results_file}'.", caplog)

    hyperopt_epochs = HyperoptTools.load_previous_results(hyperopt.results_file)
    assert len(hyperopt_epochs) == 2


def test_load_previous_results(testdatadir, caplog) -> None:

    results_file = testdatadir / 'hyperopt_results_SampleStrategy.pickle'

    hyperopt_epochs = HyperoptTools.load_previous_results(results_file)

    assert len(hyperopt_epochs) == 5
    assert log_has_re(r"Reading pickled epochs from .*", caplog)

    caplog.clear()

    # Modern version
    results_file = testdatadir / 'strategy_SampleStrategy.fthypt'

    hyperopt_epochs = HyperoptTools.load_previous_results(results_file)

    assert len(hyperopt_epochs) == 5
    assert log_has_re(r"Reading epochs from .*", caplog)


def test_load_previous_results2(mocker, testdatadir, caplog) -> None:
    mocker.patch('freqtrade.optimize.hyperopt_tools.HyperoptTools._read_results_pickle',
                 return_value=[{'asdf': '222'}])
    results_file = testdatadir / 'hyperopt_results_SampleStrategy.pickle'
    with pytest.raises(OperationalException, match=r"The file .* incompatible.*"):
        HyperoptTools.load_previous_results(results_file)


@pytest.mark.parametrize("spaces, expected_results", [
    (['buy'],
     {'buy': True, 'sell': False, 'roi': False, 'stoploss': False, 'trailing': False}),
    (['sell'],
     {'buy': False, 'sell': True, 'roi': False, 'stoploss': False, 'trailing': False}),
    (['roi'],
     {'buy': False, 'sell': False, 'roi': True, 'stoploss': False, 'trailing': False}),
    (['stoploss'],
     {'buy': False, 'sell': False, 'roi': False, 'stoploss': True, 'trailing': False}),
    (['trailing'],
     {'buy': False, 'sell': False, 'roi': False, 'stoploss': False, 'trailing': True}),
    (['buy', 'sell', 'roi', 'stoploss'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': False}),
    (['buy', 'sell', 'roi', 'stoploss', 'trailing'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': True}),
    (['buy', 'roi'],
     {'buy': True, 'sell': False, 'roi': True, 'stoploss': False, 'trailing': False}),
    (['all'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': True}),
    (['default'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': False}),
    (['default', 'trailing'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': True}),
    (['all', 'buy'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': True}),
    (['default', 'buy'],
     {'buy': True, 'sell': True, 'roi': True, 'stoploss': True, 'trailing': False}),
])
def test_has_space(hyperopt_conf, spaces, expected_results):
    for s in ['buy', 'sell', 'roi', 'stoploss', 'trailing']:
        hyperopt_conf.update({'spaces': spaces})
        assert HyperoptTools.has_space(hyperopt_conf, s) == expected_results[s]


def test_show_epoch_details(capsys):
    test_result = {
        'params_details': {
            'trailing': {
                'trailing_stop': True,
                'trailing_stop_positive': 0.02,
                'trailing_stop_positive_offset': 0.04,
                'trailing_only_offset_is_reached': True
            },
            'roi': {
                0: 0.18,
                90: 0.14,
                225: 0.05,
                430: 0},
        },
        'results_explanation': 'foo result',
        'is_initial_point': False,
        'total_profit': 0,
        'current_epoch': 2,  # This starts from 1 (in a human-friendly manner)
        'is_best': True
    }

    HyperoptTools.show_epoch_details(test_result, 5, False, no_header=True)
    captured = capsys.readouterr()
    assert '# Trailing stop:' in captured.out
    # re.match(r"Pairs for .*", captured.out)
    assert re.search(r'^\s+trailing_stop = True$', captured.out, re.MULTILINE)
    assert re.search(r'^\s+trailing_stop_positive = 0.02$', captured.out, re.MULTILINE)
    assert re.search(r'^\s+trailing_stop_positive_offset = 0.04$', captured.out, re.MULTILINE)
    assert re.search(r'^\s+trailing_only_offset_is_reached = True$', captured.out, re.MULTILINE)

    assert '# ROI table:' in captured.out
    assert re.search(r'^\s+minimal_roi = \{$', captured.out, re.MULTILINE)
    assert re.search(r'^\s+\"90\"\:\s0.14,\s*$', captured.out, re.MULTILINE)


def test__pprint_dict():
    params = {'buy_std': 1.2, 'buy_rsi': 31, 'buy_enable': True, 'buy_what': 'asdf'}
    non_params = {'buy_notoptimied': 55}

    x = HyperoptTools._pprint_dict(params, non_params)
    assert x == """{
    "buy_std": 1.2,
    "buy_rsi": 31,
    "buy_enable": True,
    "buy_what": "asdf",
    "buy_notoptimied": 55,  # value loaded from strategy
}"""


def test_get_strategy_filename(default_conf):

    x = HyperoptTools.get_strategy_filename(default_conf, 'DefaultStrategy')
    assert isinstance(x, Path)
    assert x == Path(__file__).parents[1] / 'strategy/strats/default_strategy.py'

    x = HyperoptTools.get_strategy_filename(default_conf, 'NonExistingStrategy')
    assert x is None


def test_export_params(tmpdir):

    filename = Path(tmpdir) / "DefaultStrategy.json"
    assert not filename.is_file()
    params = {
        "params_details": {
            "buy": {
                "buy_rsi": 30
            },
            "sell": {
                "sell_rsi": 70
            },
            "roi": {
                "0": 0.528,
                "346": 0.08499,
                "507": 0.049,
                "1595": 0
            }
        },
        "params_not_optimized": {
            "stoploss": -0.05,
            "trailing": {
                "trailing_stop": False,
                "trailing_stop_positive": 0.05,
                "trailing_stop_positive_offset": 0.1,
                "trailing_only_offset_is_reached": True
            },
        }

    }
    HyperoptTools.export_params(params, "DefaultStrategy", filename)

    assert filename.is_file()

    content = rapidjson.load(filename.open('r'))
    assert content['strategy_name'] == 'DefaultStrategy'
    assert 'params' in content
    assert "buy" in content["params"]
    assert "sell" in content["params"]
    assert "roi" in content["params"]
    assert "stoploss" in content["params"]
    assert "trailing" in content["params"]


def test_try_export_params(default_conf, tmpdir, caplog, mocker):
    default_conf['disableparamexport'] = False
    export_mock = mocker.patch("freqtrade.optimize.hyperopt_tools.HyperoptTools.export_params")

    filename = Path(tmpdir) / "DefaultStrategy.json"
    assert not filename.is_file()
    params = {
        "params_details": {
            "buy": {
                "buy_rsi": 30
            },
            "sell": {
                "sell_rsi": 70
            },
            "roi": {
                "0": 0.528,
                "346": 0.08499,
                "507": 0.049,
                "1595": 0
            }
        },
        "params_not_optimized": {
            "stoploss": -0.05,
            "trailing": {
                "trailing_stop": False,
                "trailing_stop_positive": 0.05,
                "trailing_stop_positive_offset": 0.1,
                "trailing_only_offset_is_reached": True
            },
        },
        FTHYPT_FILEVERSION: 2,

    }
    HyperoptTools.try_export_params(default_conf, "DefaultStrategy22", params)

    assert log_has("Strategy not found, not exporting parameter file.", caplog)
    assert export_mock.call_count == 0
    caplog.clear()

    HyperoptTools.try_export_params(default_conf, "DefaultStrategy", params)

    assert export_mock.call_count == 1
    assert export_mock.call_args_list[0][0][1] == 'DefaultStrategy'
    assert export_mock.call_args_list[0][0][2].name == 'default_strategy.json'


def test_params_print(capsys):

    params = {
        "buy": {
            "buy_rsi": 30
        },
        "sell": {
            "sell_rsi": 70
        },
    }
    non_optimized = {
        "buy": {
            "buy_adx": 44
        },
        "sell": {
            "sell_adx": 65
        },
        "stoploss": {
            "stoploss": -0.05,
        },
        "roi": {
            "0": 0.05,
            "20": 0.01,
        },
        "trailing": {
            "trailing_stop": False,
            "trailing_stop_positive": 0.05,
            "trailing_stop_positive_offset": 0.1,
            "trailing_only_offset_is_reached": True
        },

    }
    HyperoptTools._params_pretty_print(params, 'buy', 'No header', non_optimized)

    captured = capsys.readouterr()
    assert re.search("# No header", captured.out)
    assert re.search('"buy_rsi": 30,\n', captured.out)
    assert re.search('"buy_adx": 44,  # value loaded.*\n', captured.out)
    assert not re.search("sell", captured.out)

    HyperoptTools._params_pretty_print(params, 'sell', 'Sell Header', non_optimized)
    captured = capsys.readouterr()
    assert re.search("# Sell Header", captured.out)
    assert re.search('"sell_rsi": 70,\n', captured.out)
    assert re.search('"sell_adx": 65,  # value loaded.*\n', captured.out)

    HyperoptTools._params_pretty_print(params, 'roi', 'ROI Table:', non_optimized)
    captured = capsys.readouterr()
    assert re.search("# ROI Table:  # value loaded.*\n", captured.out)
    assert re.search('minimal_roi = {\n', captured.out)
    assert re.search('"20": 0.01\n', captured.out)

    HyperoptTools._params_pretty_print(params, 'trailing', 'Trailing stop:', non_optimized)
    captured = capsys.readouterr()
    assert re.search("# Trailing stop:", captured.out)
    assert re.search('trailing_stop = False  # value loaded.*\n', captured.out)
    assert re.search('trailing_stop_positive = 0.05  # value loaded.*\n', captured.out)
    assert re.search('trailing_stop_positive_offset = 0.1  # value loaded.*\n', captured.out)
    assert re.search('trailing_only_offset_is_reached = True  # value loaded.*\n', captured.out)


def test_hyperopt_serializer():

    assert isinstance(hyperopt_serializer(np.int_(5)), int)
    assert isinstance(hyperopt_serializer(np.bool_(True)), bool)
    assert isinstance(hyperopt_serializer(np.bool_(False)), bool)
