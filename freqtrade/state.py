# pragma pylint: disable=too-few-public-methods

"""
Bot state constant
"""
from enum import Enum


class State(Enum):
    """
    Bot application states
    """
    RUNNING = 1
    STOPPED = 2
    RELOAD_CONF = 3


class RunMode(Enum):
    """
    Bot running mode (backtest, hyperopt, ...)
    can be "live", "dry-run", "backtest", "edge", "hyperopt".
    """
    LIVE = "live"
    DRY_RUN = "dry_run"
    BACKTEST = "backtest"
    EDGE = "edge"
    HYPEROPT = "hyperopt"
    PLOT = "plot"
    OTHER = "other"  # Used for plotting scripts and test
