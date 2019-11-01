"""
This module contains the argument manager class
"""
import argparse
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional

from freqtrade import constants
from freqtrade.configuration.cli_options import AVAILABLE_CLI_OPTIONS

ARGS_COMMON = ["verbosity", "logfile", "version", "config", "datadir", "user_data_dir"]

ARGS_STRATEGY = ["strategy", "strategy_path"]

ARGS_MAIN = ARGS_COMMON + ARGS_STRATEGY + ["db_url", "sd_notify"]

ARGS_COMMON_OPTIMIZE = ["ticker_interval", "timerange",
                        "max_open_trades", "stake_amount", "fee"]

ARGS_BACKTEST = ARGS_COMMON_OPTIMIZE + ["position_stacking", "use_max_market_positions",
                                        "strategy_list", "export", "exportfilename"]

ARGS_HYPEROPT = ARGS_COMMON_OPTIMIZE + ["hyperopt", "hyperopt_path",
                                        "position_stacking", "epochs", "spaces",
                                        "use_max_market_positions", "print_all",
                                        "print_colorized", "print_json", "hyperopt_jobs",
                                        "hyperopt_random_state", "hyperopt_min_trades",
                                        "hyperopt_continue", "hyperopt_loss"]

ARGS_EDGE = ARGS_COMMON_OPTIMIZE + ["stoploss_range"]

ARGS_LIST_EXCHANGES = ["print_one_column", "list_exchanges_all"]

ARGS_LIST_TIMEFRAMES = ["exchange", "print_one_column"]

ARGS_LIST_PAIRS = ["exchange", "print_list", "list_pairs_print_json", "print_one_column",
                   "print_csv", "base_currencies", "quote_currencies", "list_pairs_all"]

ARGS_CREATE_USERDIR = ["user_data_dir"]

ARGS_DOWNLOAD_DATA = ["pairs", "pairs_file", "days", "download_trades", "exchange",
                      "timeframes", "erase"]

ARGS_PLOT_DATAFRAME = ["pairs", "indicators1", "indicators2", "plot_limit", "db_url",
                       "trade_source", "export", "exportfilename", "timerange", "ticker_interval"]

ARGS_PLOT_PROFIT = ["pairs", "timerange", "export", "exportfilename", "db_url",
                    "trade_source", "ticker_interval"]

NO_CONF_REQURIED = ["download-data", "list-timeframes", "list-markets", "list-pairs",
                    "plot-dataframe", "plot-profit"]

NO_CONF_ALLOWED = ["create-userdir", "list-exchanges"]


class Arguments:
    """
    Arguments Class. Manage the arguments received by the cli
    """
    def __init__(self, args: Optional[List[str]]) -> None:
        self.args = args
        self._parsed_arg: Optional[argparse.Namespace] = None
        self.parser = argparse.ArgumentParser(description='Free, open source crypto trading bot')

    def _load_args(self) -> None:
        self._build_args(optionlist=ARGS_MAIN)
        self._build_subcommands()

    def get_parsed_arg(self) -> Dict[str, Any]:
        """
        Return the list of arguments
        :return: List[str] List of arguments
        """
        if self._parsed_arg is None:
            self._load_args()
            self._parsed_arg = self._parse_args()

        return vars(self._parsed_arg)

    def _parse_args(self) -> argparse.Namespace:
        """
        Parses given arguments and returns an argparse Namespace instance.
        """
        parsed_arg = self.parser.parse_args(self.args)

        # When no config is provided, but a config exists, use that configuration!
        subparser = parsed_arg.subparser if 'subparser' in parsed_arg else None

        # Workaround issue in argparse with action='append' and default value
        # (see https://bugs.python.org/issue16399)
        # Allow no-config for certain commands (like downloading / plotting)
        if (parsed_arg.config is None
                and subparser not in NO_CONF_ALLOWED
                and ((Path.cwd() / constants.DEFAULT_CONFIG).is_file()
                     or (subparser not in NO_CONF_REQURIED))):
            parsed_arg.config = [constants.DEFAULT_CONFIG]

        return parsed_arg

    def _build_args(self, optionlist, parser=None):
        parser = parser or self.parser

        for val in optionlist:
            opt = AVAILABLE_CLI_OPTIONS[val]
            parser.add_argument(*opt.cli, dest=val, **opt.kwargs)

    def _build_subcommands(self) -> None:
        """
        Builds and attaches all subcommands.
        :return: None
        """
        from freqtrade.optimize import start_backtesting, start_hyperopt, start_edge
        from freqtrade.utils import (start_create_userdir, start_download_data,
                                     start_list_exchanges, start_list_timeframes,
                                     start_list_markets)

        subparsers = self.parser.add_subparsers(dest='subparser')

        # Add backtesting subcommand
        backtesting_cmd = subparsers.add_parser('backtesting', help='Backtesting module.')
        backtesting_cmd.set_defaults(func=start_backtesting)
        self._build_args(optionlist=ARGS_BACKTEST, parser=backtesting_cmd)

        # Add edge subcommand
        edge_cmd = subparsers.add_parser('edge', help='Edge module.')
        edge_cmd.set_defaults(func=start_edge)
        self._build_args(optionlist=ARGS_EDGE, parser=edge_cmd)

        # Add hyperopt subcommand
        hyperopt_cmd = subparsers.add_parser('hyperopt', help='Hyperopt module.')
        hyperopt_cmd.set_defaults(func=start_hyperopt)
        self._build_args(optionlist=ARGS_HYPEROPT, parser=hyperopt_cmd)

        # add create-userdir subcommand
        create_userdir_cmd = subparsers.add_parser('create-userdir',
                                                   help="Create user-data directory.")
        create_userdir_cmd.set_defaults(func=start_create_userdir)
        self._build_args(optionlist=ARGS_CREATE_USERDIR, parser=create_userdir_cmd)

        # Add list-exchanges subcommand
        list_exchanges_cmd = subparsers.add_parser(
            'list-exchanges',
            help='Print available exchanges.'
        )
        list_exchanges_cmd.set_defaults(func=start_list_exchanges)
        self._build_args(optionlist=ARGS_LIST_EXCHANGES, parser=list_exchanges_cmd)

        # Add list-timeframes subcommand
        list_timeframes_cmd = subparsers.add_parser(
            'list-timeframes',
            help='Print available ticker intervals (timeframes) for the exchange.'
        )
        list_timeframes_cmd.set_defaults(func=start_list_timeframes)
        self._build_args(optionlist=ARGS_LIST_TIMEFRAMES, parser=list_timeframes_cmd)

        # Add list-markets subcommand
        list_markets_cmd = subparsers.add_parser(
            'list-markets',
            help='Print markets on exchange.'
        )
        list_markets_cmd.set_defaults(func=partial(start_list_markets, pairs_only=False))
        self._build_args(optionlist=ARGS_LIST_PAIRS, parser=list_markets_cmd)

        # Add list-pairs subcommand
        list_pairs_cmd = subparsers.add_parser(
            'list-pairs',
            help='Print pairs on exchange.'
        )
        list_pairs_cmd.set_defaults(func=partial(start_list_markets, pairs_only=True))
        self._build_args(optionlist=ARGS_LIST_PAIRS, parser=list_pairs_cmd)

        # Add download-data subcommand
        download_data_cmd = subparsers.add_parser(
            'download-data',
            help='Download backtesting data.'
        )
        download_data_cmd.set_defaults(func=start_download_data)
        self._build_args(optionlist=ARGS_DOWNLOAD_DATA, parser=download_data_cmd)

        # Add Plotting subcommand
        from freqtrade.plot.plot_utils import start_plot_dataframe, start_plot_profit
        plot_dataframe_cmd = subparsers.add_parser(
            'plot-dataframe',
            help='Plot candles with indicators.'
        )
        plot_dataframe_cmd.set_defaults(func=start_plot_dataframe)
        self._build_args(optionlist=ARGS_PLOT_DATAFRAME, parser=plot_dataframe_cmd)

        # Plot profit
        plot_profit_cmd = subparsers.add_parser(
            'plot-profit',
            help='Generate plot showing profits.'
        )
        plot_profit_cmd.set_defaults(func=start_plot_profit)
        self._build_args(optionlist=ARGS_PLOT_PROFIT, parser=plot_profit_cmd)
