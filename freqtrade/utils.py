import csv
import logging
import sys
from collections import OrderedDict
from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, List

import arrow
import rapidjson
from colorama import init as colorama_init
from tabulate import tabulate

from freqtrade.configuration import (Configuration, TimeRange,
                                     remove_credentials)
from freqtrade.configuration.directory_operations import (copy_sample_files,
                                                          create_userdata_dir)
from freqtrade.constants import USERPATH_HYPEROPTS, USERPATH_STRATEGY
from freqtrade.data.history import (convert_trades_to_ohlcv,
                                    refresh_backtest_ohlcv_data,
                                    refresh_backtest_trades_data)
from freqtrade.exceptions import OperationalException
from freqtrade.exchange import (available_exchanges, ccxt_exchanges,
                                market_is_active, symbol_is_pair)
from freqtrade.misc import plural, render_template
from freqtrade.resolvers import ExchangeResolver, StrategyResolver
from freqtrade.state import RunMode

logger = logging.getLogger(__name__)


def setup_utils_configuration(args: Dict[str, Any], method: RunMode) -> Dict[str, Any]:
    """
    Prepare the configuration for utils subcommands
    :param args: Cli args from Arguments()
    :return: Configuration
    """
    configuration = Configuration(args, method)
    config = configuration.get_config()

    # Ensure we do not use Exchange credentials
    remove_credentials(config)

    return config


def start_trading(args: Dict[str, Any]) -> int:
    """
    Main entry point for trading mode
    """
    from freqtrade.worker import Worker
    # Load and run worker
    worker = None
    try:
        worker = Worker(args)
        worker.run()
    except KeyboardInterrupt:
        logger.info('SIGINT received, aborting ...')
    finally:
        if worker:
            logger.info("worker found ... calling exit")
            worker.exit()
    return 0


def start_list_exchanges(args: Dict[str, Any]) -> None:
    """
    Print available exchanges
    :param args: Cli args from Arguments()
    :return: None
    """
    exchanges = ccxt_exchanges() if args['list_exchanges_all'] else available_exchanges()
    if args['print_one_column']:
        print('\n'.join(exchanges))
    else:
        if args['list_exchanges_all']:
            print(f"All exchanges supported by the ccxt library: {', '.join(exchanges)}")
        else:
            print(f"Exchanges available for Freqtrade: {', '.join(exchanges)}")


def start_create_userdir(args: Dict[str, Any]) -> None:
    """
    Create "user_data" directory to contain user data strategies, hyperopt, ...)
    :param args: Cli args from Arguments()
    :return: None
    """
    if "user_data_dir" in args and args["user_data_dir"]:
        userdir = create_userdata_dir(args["user_data_dir"], create_dir=True)
        copy_sample_files(userdir, overwrite=args["reset"])
    else:
        logger.warning("`create-userdir` requires --userdir to be set.")
        sys.exit(1)


def deploy_new_strategy(strategy_name, strategy_path: Path, subtemplate: str):
    """
    Deploy new strategy from template to strategy_path
    """
    indicators = render_template(templatefile=f"subtemplates/indicators_{subtemplate}.j2",)
    buy_trend = render_template(templatefile=f"subtemplates/buy_trend_{subtemplate}.j2",)
    sell_trend = render_template(templatefile=f"subtemplates/sell_trend_{subtemplate}.j2",)

    strategy_text = render_template(templatefile='base_strategy.py.j2',
                                    arguments={"strategy": strategy_name,
                                               "indicators": indicators,
                                               "buy_trend": buy_trend,
                                               "sell_trend": sell_trend,
                                               })

    logger.info(f"Writing strategy to `{strategy_path}`.")
    strategy_path.write_text(strategy_text)


def start_new_strategy(args: Dict[str, Any]) -> None:

    config = setup_utils_configuration(args, RunMode.UTIL_NO_EXCHANGE)

    if "strategy" in args and args["strategy"]:
        if args["strategy"] == "DefaultStrategy":
            raise OperationalException("DefaultStrategy is not allowed as name.")

        new_path = config['user_data_dir'] / USERPATH_STRATEGY / (args["strategy"] + ".py")

        if new_path.exists():
            raise OperationalException(f"`{new_path}` already exists. "
                                       "Please choose another Strategy Name.")

        deploy_new_strategy(args['strategy'], new_path, args['template'])

    else:
        raise OperationalException("`new-strategy` requires --strategy to be set.")


def deploy_new_hyperopt(hyperopt_name, hyperopt_path: Path, subtemplate: str):
    """
    Deploys a new hyperopt template to hyperopt_path
    """
    buy_guards = render_template(
        templatefile=f"subtemplates/hyperopt_buy_guards_{subtemplate}.j2",)
    sell_guards = render_template(
        templatefile=f"subtemplates/hyperopt_sell_guards_{subtemplate}.j2",)
    buy_space = render_template(
        templatefile=f"subtemplates/hyperopt_buy_space_{subtemplate}.j2",)
    sell_space = render_template(
        templatefile=f"subtemplates/hyperopt_sell_space_{subtemplate}.j2",)

    strategy_text = render_template(templatefile='base_hyperopt.py.j2',
                                    arguments={"hyperopt": hyperopt_name,
                                               "buy_guards": buy_guards,
                                               "sell_guards": sell_guards,
                                               "buy_space": buy_space,
                                               "sell_space": sell_space,
                                               })

    logger.info(f"Writing hyperopt to `{hyperopt_path}`.")
    hyperopt_path.write_text(strategy_text)


def start_new_hyperopt(args: Dict[str, Any]) -> None:

    config = setup_utils_configuration(args, RunMode.UTIL_NO_EXCHANGE)

    if "hyperopt" in args and args["hyperopt"]:
        if args["hyperopt"] == "DefaultHyperopt":
            raise OperationalException("DefaultHyperopt is not allowed as name.")

        new_path = config['user_data_dir'] / USERPATH_HYPEROPTS / (args["hyperopt"] + ".py")

        if new_path.exists():
            raise OperationalException(f"`{new_path}` already exists. "
                                       "Please choose another Strategy Name.")
        deploy_new_hyperopt(args['hyperopt'], new_path, args['template'])
    else:
        raise OperationalException("`new-hyperopt` requires --hyperopt to be set.")


def start_download_data(args: Dict[str, Any]) -> None:
    """
    Download data (former download_backtest_data.py script)
    """
    config = setup_utils_configuration(args, RunMode.UTIL_EXCHANGE)

    timerange = TimeRange()
    if 'days' in config:
        time_since = arrow.utcnow().shift(days=-config['days']).strftime("%Y%m%d")
        timerange = TimeRange.parse_timerange(f'{time_since}-')

    if 'pairs' not in config:
        raise OperationalException(
            "Downloading data requires a list of pairs. "
            "Please check the documentation on how to configure this.")

    logger.info(f'About to download pairs: {config["pairs"]}, '
                f'intervals: {config["timeframes"]} to {config["datadir"]}')

    pairs_not_available: List[str] = []

    # Init exchange
    exchange = ExchangeResolver.load_exchange(config['exchange']['name'], config)
    try:

        if config.get('download_trades'):
            pairs_not_available = refresh_backtest_trades_data(
                exchange, pairs=config["pairs"], datadir=config['datadir'],
                timerange=timerange, erase=config.get("erase"))

            # Convert downloaded trade data to different timeframes
            convert_trades_to_ohlcv(
                pairs=config["pairs"], timeframes=config["timeframes"],
                datadir=config['datadir'], timerange=timerange, erase=config.get("erase"))
        else:
            pairs_not_available = refresh_backtest_ohlcv_data(
                exchange, pairs=config["pairs"], timeframes=config["timeframes"],
                datadir=config['datadir'], timerange=timerange, erase=config.get("erase"))

    except KeyboardInterrupt:
        sys.exit("SIGINT received, aborting ...")

    finally:
        if pairs_not_available:
            logger.info(f"Pairs [{','.join(pairs_not_available)}] not available "
                        f"on exchange {exchange.name}.")


def start_list_strategies(args: Dict[str, Any]) -> None:
    """
    Print Strategies available in a directory
    """
    config = setup_utils_configuration(args, RunMode.UTIL_NO_EXCHANGE)

    directory = Path(config.get('strategy_path', config['user_data_dir'] / USERPATH_STRATEGY))
    strategies = StrategyResolver.search_all_objects(directory)
    # Sort alphabetically
    strategies = sorted(strategies, key=lambda x: x['name'])
    strats_to_print = [{'name': s['name'], 'location': s['location'].name} for s in strategies]

    if args['print_one_column']:
        print('\n'.join([s['name'] for s in strategies]))
    else:
        print(tabulate(strats_to_print, headers='keys', tablefmt='pipe'))


def start_list_timeframes(args: Dict[str, Any]) -> None:
    """
    Print ticker intervals (timeframes) available on Exchange
    """
    config = setup_utils_configuration(args, RunMode.UTIL_EXCHANGE)
    # Do not use ticker_interval set in the config
    config['ticker_interval'] = None

    # Init exchange
    exchange = ExchangeResolver.load_exchange(config['exchange']['name'], config, validate=False)

    if args['print_one_column']:
        print('\n'.join(exchange.timeframes))
    else:
        print(f"Timeframes available for the exchange `{exchange.name}`: "
              f"{', '.join(exchange.timeframes)}")


def start_list_markets(args: Dict[str, Any], pairs_only: bool = False) -> None:
    """
    Print pairs/markets on the exchange
    :param args: Cli args from Arguments()
    :param pairs_only: if True print only pairs, otherwise print all instruments (markets)
    :return: None
    """
    config = setup_utils_configuration(args, RunMode.UTIL_EXCHANGE)

    # Init exchange
    exchange = ExchangeResolver.load_exchange(config['exchange']['name'], config, validate=False)

    # By default only active pairs/markets are to be shown
    active_only = not args.get('list_pairs_all', False)

    base_currencies = args.get('base_currencies', [])
    quote_currencies = args.get('quote_currencies', [])

    try:
        pairs = exchange.get_markets(base_currencies=base_currencies,
                                     quote_currencies=quote_currencies,
                                     pairs_only=pairs_only,
                                     active_only=active_only)
        # Sort the pairs/markets by symbol
        pairs = OrderedDict(sorted(pairs.items()))
    except Exception as e:
        raise OperationalException(f"Cannot get markets. Reason: {e}") from e

    else:
        summary_str = ((f"Exchange {exchange.name} has {len(pairs)} ") +
                       ("active " if active_only else "") +
                       (plural(len(pairs), "pair" if pairs_only else "market")) +
                       (f" with {', '.join(base_currencies)} as base "
                        f"{plural(len(base_currencies), 'currency', 'currencies')}"
                        if base_currencies else "") +
                       (" and" if base_currencies and quote_currencies else "") +
                       (f" with {', '.join(quote_currencies)} as quote "
                        f"{plural(len(quote_currencies), 'currency', 'currencies')}"
                        if quote_currencies else ""))

        headers = ["Id", "Symbol", "Base", "Quote", "Active",
                   *(['Is pair'] if not pairs_only else [])]

        tabular_data = []
        for _, v in pairs.items():
            tabular_data.append({'Id': v['id'], 'Symbol': v['symbol'],
                                 'Base': v['base'], 'Quote': v['quote'],
                                 'Active': market_is_active(v),
                                 **({'Is pair': symbol_is_pair(v['symbol'])}
                                    if not pairs_only else {})})

        if (args.get('print_one_column', False) or
                args.get('list_pairs_print_json', False) or
                args.get('print_csv', False)):
            # Print summary string in the log in case of machine-readable
            # regular formats.
            logger.info(f"{summary_str}.")
        else:
            # Print empty string separating leading logs and output in case of
            # human-readable formats.
            print()

        if len(pairs):
            if args.get('print_list', False):
                # print data as a list, with human-readable summary
                print(f"{summary_str}: {', '.join(pairs.keys())}.")
            elif args.get('print_one_column', False):
                print('\n'.join(pairs.keys()))
            elif args.get('list_pairs_print_json', False):
                print(rapidjson.dumps(list(pairs.keys()), default=str))
            elif args.get('print_csv', False):
                writer = csv.DictWriter(sys.stdout, fieldnames=headers)
                writer.writeheader()
                writer.writerows(tabular_data)
            else:
                # print data as a table, with the human-readable summary
                print(f"{summary_str}:")
                print(tabulate(tabular_data, headers='keys', tablefmt='pipe'))
        elif not (args.get('print_one_column', False) or
                  args.get('list_pairs_print_json', False) or
                  args.get('print_csv', False)):
            print(f"{summary_str}.")


def start_test_pairlist(args: Dict[str, Any]) -> None:
    """
    Test Pairlist configuration
    """
    from freqtrade.pairlist.pairlistmanager import PairListManager
    config = setup_utils_configuration(args, RunMode.UTIL_EXCHANGE)

    exchange = ExchangeResolver.load_exchange(config['exchange']['name'], config, validate=False)

    quote_currencies = args.get('quote_currencies')
    if not quote_currencies:
        quote_currencies = [config.get('stake_currency')]
    results = {}
    for curr in quote_currencies:
        config['stake_currency'] = curr
        # Do not use ticker_interval set in the config
        pairlists = PairListManager(exchange, config)
        pairlists.refresh_pairlist()
        results[curr] = pairlists.whitelist

    for curr, pairlist in results.items():
        if not args.get('print_one_column', False):
            print(f"Pairs for {curr}: ")

        if args.get('print_one_column', False):
            print('\n'.join(pairlist))
        elif args.get('list_pairs_print_json', False):
            print(rapidjson.dumps(list(pairlist), default=str))
        else:
            print(pairlist)


def start_hyperopt_list(args: Dict[str, Any]) -> None:
    """
    List hyperopt epochs previously evaluated
    """
    from freqtrade.optimize.hyperopt import Hyperopt

    config = setup_utils_configuration(args, RunMode.UTIL_NO_EXCHANGE)

    only_best = config.get('hyperopt_list_best', False)
    only_profitable = config.get('hyperopt_list_profitable', False)
    print_colorized = config.get('print_colorized', False)
    print_json = config.get('print_json', False)
    no_details = config.get('hyperopt_list_no_details', False)
    no_header = False

    trials_file = (config['user_data_dir'] /
                   'hyperopt_results' / 'hyperopt_results.pickle')

    # Previous evaluations
    trials = Hyperopt.load_previous_results(trials_file)
    total_epochs = len(trials)

    trials = _hyperopt_filter_trials(trials, only_best, only_profitable)

    # TODO: fetch the interval for epochs to print from the cli option
    epoch_start, epoch_stop = 0, None

    if print_colorized:
        colorama_init(autoreset=True)

    try:
        # Human-friendly indexes used here (starting from 1)
        for val in trials[epoch_start:epoch_stop]:
            Hyperopt.print_results_explanation(val, total_epochs, not only_best, print_colorized)

    except KeyboardInterrupt:
        print('User interrupted..')

    if trials and not no_details:
        sorted_trials = sorted(trials, key=itemgetter('loss'))
        results = sorted_trials[0]
        Hyperopt.print_epoch_details(results, total_epochs, print_json, no_header)


def start_hyperopt_show(args: Dict[str, Any]) -> None:
    """
    Show details of a hyperopt epoch previously evaluated
    """
    from freqtrade.optimize.hyperopt import Hyperopt

    config = setup_utils_configuration(args, RunMode.UTIL_NO_EXCHANGE)

    only_best = config.get('hyperopt_list_best', False)
    only_profitable = config.get('hyperopt_list_profitable', False)
    no_header = config.get('hyperopt_show_no_header', False)

    trials_file = (config['user_data_dir'] /
                   'hyperopt_results' / 'hyperopt_results.pickle')

    # Previous evaluations
    trials = Hyperopt.load_previous_results(trials_file)
    total_epochs = len(trials)

    trials = _hyperopt_filter_trials(trials, only_best, only_profitable)
    trials_epochs = len(trials)

    n = config.get('hyperopt_show_index', -1)
    if n > trials_epochs:
        raise OperationalException(
                f"The index of the epoch to show should be less than {trials_epochs + 1}.")
    if n < -trials_epochs:
        raise OperationalException(
                f"The index of the epoch to show should be greater than {-trials_epochs - 1}.")

    # Translate epoch index from human-readable format to pythonic
    if n > 0:
        n -= 1

    print_json = config.get('print_json', False)

    if trials:
        val = trials[n]
        Hyperopt.print_epoch_details(val, total_epochs, print_json, no_header,
                                     header_str="Epoch details")


def _hyperopt_filter_trials(trials: List, only_best: bool, only_profitable: bool) -> List:
    """
    Filter our items from the list of hyperopt results
    """
    if only_best:
        trials = [x for x in trials if x['is_best']]
    if only_profitable:
        trials = [x for x in trials if x['results_metrics']['profit'] > 0]

    logger.info(f"{len(trials)} " +
                ("best " if only_best else "") +
                ("profitable " if only_profitable else "") +
                "epochs found.")

    return trials
