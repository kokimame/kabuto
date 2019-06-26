import logging
from argparse import Namespace
from typing import Any, Dict

from filelock import FileLock, Timeout

from freqtrade import DependencyException, constants
from freqtrade.state import RunMode
from freqtrade.utils import setup_utils_configuration


logger = logging.getLogger(__name__)


def setup_configuration(args: Namespace, method: RunMode) -> Dict[str, Any]:
    """
    Prepare the configuration for the Hyperopt module
    :param args: Cli args from Arguments()
    :return: Configuration
    """
    config = setup_utils_configuration(args, method)

    if method == RunMode.BACKTEST:
        if config['stake_amount'] == constants.UNLIMITED_STAKE_AMOUNT:
            raise DependencyException('stake amount could not be "%s" for backtesting' %
                                      constants.UNLIMITED_STAKE_AMOUNT)

    if method == RunMode.HYPEROPT:
        # Special cases for Hyperopt
        if config.get('strategy') and config.get('strategy') != 'DefaultStrategy':
            logger.error("Please don't use --strategy for hyperopt.")
            logger.error(
                "Read the documentation at "
                "https://github.com/freqtrade/freqtrade/blob/develop/docs/hyperopt.md "
                "to understand how to configure hyperopt.")
            raise DependencyException("--strategy configured but not supported for hyperopt")

    return config


def start_backtesting(args: Namespace) -> None:
    """
    Start Backtesting script
    :param args: Cli args from Arguments()
    :return: None
    """
    # Import here to avoid loading backtesting module when it's not used
    from freqtrade.optimize.backtesting import Backtesting

    # Initialize configuration
    config = setup_configuration(args, RunMode.BACKTEST)

    logger.info('Starting freqtrade in Backtesting mode')

    # Initialize backtesting object
    backtesting = Backtesting(config)
    backtesting.start()


def start_hyperopt(args: Namespace) -> None:
    """
    Start hyperopt script
    :param args: Cli args from Arguments()
    :return: None
    """
    # Import here to avoid loading hyperopt module when it's not used
    from freqtrade.optimize.hyperopt import Hyperopt, HYPEROPT_LOCKFILE

    # Initialize configuration
    config = setup_configuration(args, RunMode.HYPEROPT)

    logger.info('Starting freqtrade in Hyperopt mode')

    lock = FileLock(HYPEROPT_LOCKFILE)

    try:
        with lock.acquire(timeout=1):

            # Remove noisy log messages
            logging.getLogger('hyperopt.tpe').setLevel(logging.WARNING)
            logging.getLogger('filelock').setLevel(logging.WARNING)

            # Initialize backtesting object
            hyperopt = Hyperopt(config)
            hyperopt.start()

    except Timeout:
        logger.info("Another running instance of freqtrade Hyperopt detected.")
        logger.info("Simultaneous execution of multiple Hyperopt commands is not supported. "
                    "Hyperopt module is resource hungry. Please run your Hyperopts sequentially "
                    "or on separate machines.")
        logger.info("Quitting now.")
        # TODO: return False here in order to help freqtrade to exit
        # with non-zero exit code...
        # Same in Edge and Backtesting start() functions.


def start_edge(args: Namespace) -> None:
    """
    Start Edge script
    :param args: Cli args from Arguments()
    :return: None
    """
    from freqtrade.optimize.edge_cli import EdgeCli
    # Initialize configuration
    config = setup_configuration(args, RunMode.EDGE)
    logger.info('Starting freqtrade in Edge mode')

    # Initialize Edge object
    edge_cli = EdgeCli(config)
    edge_cli.start()
