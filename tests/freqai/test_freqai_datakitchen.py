import datetime
import shutil
from pathlib import Path

import pytest

from freqtrade.exceptions import OperationalException
from tests.conftest import log_has_re
from tests.freqai.conftest import get_patched_data_kitchen, make_data_dictionary


@pytest.mark.parametrize(
    "timerange, train_period_days, expected_result",
    [
        ("20220101-20220201", 30, "20211202-20220201"),
        ("20220301-20220401", 15, "20220214-20220401"),
    ],
)
def test_create_fulltimerange(
    timerange, train_period_days, expected_result, freqai_conf, mocker, caplog
):
    dk = get_patched_data_kitchen(mocker, freqai_conf)
    assert dk.create_fulltimerange(timerange, train_period_days) == expected_result
    shutil.rmtree(Path(dk.full_path))


def test_create_fulltimerange_incorrect_backtest_period(mocker, freqai_conf):
    dk = get_patched_data_kitchen(mocker, freqai_conf)
    with pytest.raises(OperationalException, match=r"backtest_period_days must be an integer"):
        dk.create_fulltimerange("20220101-20220201", 0.5)
    with pytest.raises(OperationalException, match=r"backtest_period_days must be positive"):
        dk.create_fulltimerange("20220101-20220201", -1)
    shutil.rmtree(Path(dk.full_path))


@pytest.mark.parametrize(
    "timerange, train_period_days, backtest_period_days, expected_result",
    [
        ("20220101-20220201", 30, 7, 9),
        ("20220101-20220201", 30, 0.5, 120),
        ("20220101-20220201", 10, 1, 80),
    ],
)
def test_split_timerange(
    mocker, freqai_conf, timerange, train_period_days, backtest_period_days, expected_result
):
    freqai_conf.update({"timerange": "20220101-20220401"})
    dk = get_patched_data_kitchen(mocker, freqai_conf)
    tr_list, bt_list = dk.split_timerange(timerange, train_period_days, backtest_period_days)
    assert len(tr_list) == len(bt_list) == expected_result

    with pytest.raises(
        OperationalException, match=r"train_period_days must be an integer greater than 0."
    ):
        dk.split_timerange("20220101-20220201", -1, 0.5)
    shutil.rmtree(Path(dk.full_path))


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        (datetime.datetime.now(tz=datetime.timezone.utc).timestamp() - 7200, True),
        (datetime.datetime.now(tz=datetime.timezone.utc).timestamp(), False),
    ],
)
def test_check_if_model_expired(mocker, freqai_conf, timestamp, expected):
    dk = get_patched_data_kitchen(mocker, freqai_conf)
    assert dk.check_if_model_expired(timestamp) == expected
    shutil.rmtree(Path(dk.full_path))


def test_use_DBSCAN_to_remove_outliers(mocker, freqai_conf, caplog):
    freqai = make_data_dictionary(mocker, freqai_conf)
    # freqai_conf['freqai']['feature_parameters'].update({"outlier_protection_percentage": 1})
    freqai.dk.use_DBSCAN_to_remove_outliers(predict=False)
    assert log_has_re(
        "DBSCAN found eps of 2.42.",
        caplog,
    )


def test_compute_distances(mocker, freqai_conf):
    freqai = make_data_dictionary(mocker, freqai_conf)
    freqai_conf['freqai']['feature_parameters'].update({"DI_threshold": 1})
    avg_mean_dist = freqai.dk.compute_distances()
    assert round(avg_mean_dist, 2) == 2.56


def test_use_SVM_to_remove_outliers_and_outlier_protection(mocker, freqai_conf, caplog):
    freqai = make_data_dictionary(mocker, freqai_conf)
    freqai_conf['freqai']['feature_parameters'].update({"outlier_protection_percentage": 0.1})
    freqai.dk.use_SVM_to_remove_outliers(predict=False)
    assert log_has_re(
        "SVM detected 8.46%",
        caplog,
    )
