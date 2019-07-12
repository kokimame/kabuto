# pragma pylint: disable=attribute-defined-outside-init

"""
This module load custom strategies
"""
import logging
import tempfile
from base64 import urlsafe_b64decode
from collections import OrderedDict
from inspect import getfullargspec
from pathlib import Path
from typing import Dict, Optional

from freqtrade import constants, OperationalException
from freqtrade.resolvers import IResolver
from freqtrade.strategy import import_strategy
from freqtrade.strategy.interface import IStrategy

logger = logging.getLogger(__name__)


class StrategyResolver(IResolver):
    """
    This class contains all the logic to load custom strategy class
    """

    __slots__ = ['strategy']

    def __init__(self, config: Optional[Dict] = None) -> None:
        """
        Load the custom class from config parameter
        :param config: configuration dictionary or None
        """
        config = config or {}

        # Verify the strategy is in the configuration, otherwise fallback to the default strategy
        strategy_name = config.get('strategy') or constants.DEFAULT_STRATEGY
        self.strategy: IStrategy = self._load_strategy(strategy_name,
                                                       config=config,
                                                       extra_dir=config.get('strategy_path'))

        # make sure experimental dict is available
        if 'experimental' not in config:
            config['experimental'] = {}

        # Set attributes
        # Check if we need to override configuration
        # (Attribute name,                              default, experimental)
        attributes = [("minimal_roi",                     {"0": 10.0}, False),
                      ("ticker_interval",                 None,        False),
                      ("stoploss",                        None,        False),
                      ("trailing_stop",                   None,        False),
                      ("trailing_stop_positive",          None,        False),
                      ("trailing_stop_positive_offset",   0.0,         False),
                      ("trailing_only_offset_is_reached", None,        False),
                      ("process_only_new_candles",        None,        False),
                      ("order_types",                     None,        False),
                      ("order_time_in_force",             None,        False),
                      ("stake_currency",                  None,        False),
                      ("stake_amount",                    None,        False),
                      ("use_sell_signal",                 False,       True),
                      ("sell_profit_only",                False,       True),
                      ("ignore_roi_if_buy_signal",        False,       True),
                      ]
        for attribute, default, experimental in attributes:
            if experimental:
                self._override_attribute_helper(config['experimental'], attribute, default)
            else:
                self._override_attribute_helper(config, attribute, default)

        # Loop this list again to have output combined
        for attribute, _, exp in attributes:
            if exp and attribute in config['experimental']:
                logger.info("Strategy using %s: %s", attribute, config['experimental'][attribute])
            elif attribute in config:
                logger.info("Strategy using %s: %s", attribute, config[attribute])

        # Sort and apply type conversions
        self.strategy.minimal_roi = OrderedDict(sorted(
            {int(key): value for (key, value) in self.strategy.minimal_roi.items()}.items(),
            key=lambda t: t[0]))
        self.strategy.stoploss = float(self.strategy.stoploss)

        self._strategy_sanity_validations()

    def _override_attribute_helper(self, config, attribute: str, default):
        """
        Override attributes in the strategy.
        Prevalence:
        - Configuration
        - Strategy
        - default (if not None)
        """
        if attribute in config:
            setattr(self.strategy, attribute, config[attribute])
            logger.info("Override strategy '%s' with value in config file: %s.",
                        attribute, config[attribute])
        elif hasattr(self.strategy, attribute):
            config[attribute] = getattr(self.strategy, attribute)
        # Explicitly check for None here as other "falsy" values are possible
        elif default is not None:
            setattr(self.strategy, attribute, default)
            config[attribute] = default

    def _strategy_sanity_validations(self):
        if not all(k in self.strategy.order_types for k in constants.REQUIRED_ORDERTYPES):
            raise ImportError(f"Impossible to load Strategy '{self.strategy.__class__.__name__}'. "
                              f"Order-types mapping is incomplete.")

        if not all(k in self.strategy.order_time_in_force for k in constants.REQUIRED_ORDERTIF):
            raise ImportError(f"Impossible to load Strategy '{self.strategy.__class__.__name__}'. "
                              f"Order-time-in-force mapping is incomplete.")

    def _load_strategy(
            self, strategy_name: str, config: dict, extra_dir: Optional[str] = None) -> IStrategy:
        """
        Search and loads the specified strategy.
        :param strategy_name: name of the module to import
        :param config: configuration for the strategy
        :param extra_dir: additional directory to search for the given strategy
        :return: Strategy instance or None
        """
        current_path = Path(__file__).parent.parent.joinpath('strategy').resolve()

        abs_paths = [
            Path.cwd().joinpath('user_data/strategies'),
            current_path,
        ]

        if extra_dir:
            # Add extra strategy directory on top of search paths
            abs_paths.insert(0, Path(extra_dir).resolve())

        if ":" in strategy_name:
            logger.info("loading base64 encoded strategy")
            strat = strategy_name.split(":")

            if len(strat) == 2:
                temp = Path(tempfile.mkdtemp("freq", "strategy"))
                name = strat[0] + ".py"

                temp.joinpath(name).write_text(urlsafe_b64decode(strat[1]).decode('utf-8'))
                temp.joinpath("__init__.py").touch()

                strategy_name = strat[0]

                # register temp path with the bot
                abs_paths.insert(0, temp.resolve())

        for _path in abs_paths:
            try:
                (strategy, module_path) = self._search_object(directory=_path,
                                                              object_type=IStrategy,
                                                              object_name=strategy_name,
                                                              kwargs={'config': config})
                if strategy:
                    logger.info(f"Using resolved strategy {strategy_name} from '{module_path}'...")
                    strategy._populate_fun_len = len(
                        getfullargspec(strategy.populate_indicators).args)
                    strategy._buy_fun_len = len(getfullargspec(strategy.populate_buy_trend).args)
                    strategy._sell_fun_len = len(getfullargspec(strategy.populate_sell_trend).args)
                    try:
                        return import_strategy(strategy, config=config)
                    except TypeError as e:
                        logger.warning(
                            f"Impossible to load strategy '{strategy_name}' from {module_path}. "
                            f"Error: {e}")
            except FileNotFoundError:
                logger.warning('Path "%s" does not exist.', _path.relative_to(Path.cwd()))

        raise OperationalException(
            f"Impossible to load Strategy '{strategy_name}'. This class does not exist "
            "or contains Python code errors."
        )
