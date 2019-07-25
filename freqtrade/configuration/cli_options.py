"""
Definition of cli arguments used in arguments.py
"""
import argparse
import os

from freqtrade import __version__, constants


def check_int_positive(value: str) -> int:
    try:
        uint = int(value)
        if uint <= 0:
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{value} is invalid for this parameter, should be a positive integer value"
        )
    return uint


class Arg:
    # Optional CLI arguments
    def __init__(self, *args, **kwargs):
        self.cli = args
        self.kwargs = kwargs


# List of available command line options
AVAILABLE_CLI_OPTIONS = {
    # Common options
    "verbosity": Arg(
        '-v', '--verbose',
        help='Verbose mode (-vv for more, -vvv to get all messages).',
        action='count',
        default=0,
    ),
    "logfile": Arg(
        '--logfile',
        help='Log to the file specified.',
        metavar='FILE',
    ),
    "version": Arg(
        '-V', '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    ),
    "config": Arg(
        '-c', '--config',
        help=f'Specify configuration file (default: `{constants.DEFAULT_CONFIG}`). '
        f'Multiple --config options may be used. '
        f'Can be set to `-` to read config from stdin.',
        action='append',
        metavar='PATH',
    ),
    "datadir": Arg(
        '-d', '--datadir',
        help='Path to backtest data.',
        metavar='PATH',
    ),
    # Main options
    "strategy": Arg(
        '-s', '--strategy',
        help='Specify strategy class name (default: `%(default)s`).',
        metavar='NAME',
        default='DefaultStrategy',
    ),
    "strategy_path": Arg(
        '--strategy-path',
        help='Specify additional strategy lookup path.',
        metavar='PATH',
    ),
    "db_url": Arg(
        '--db-url',
        help=f'Override trades database URL, this is useful in custom deployments '
        f'(default: `{constants.DEFAULT_DB_PROD_URL}` for Live Run mode, '
        f'`{constants.DEFAULT_DB_DRYRUN_URL}` for Dry Run).',
        metavar='PATH',
    ),
    "sd_notify": Arg(
        '--sd-notify',
        help='Notify systemd service manager.',
        action='store_true',
    ),
    # Optimize common
    "ticker_interval": Arg(
        '-i', '--ticker-interval',
        help='Specify ticker interval (`1m`, `5m`, `30m`, `1h`, `1d`).',
    ),
    "timerange": Arg(
        '--timerange',
        help='Specify what timerange of data to use.',
    ),
    "max_open_trades": Arg(
        '--max_open_trades',
        help='Specify max_open_trades to use.',
        type=int,
        metavar='INT',
    ),
    "stake_amount": Arg(
        '--stake_amount',
        help='Specify stake_amount.',
        type=float,
    ),
    "refresh_pairs": Arg(
        '-r', '--refresh-pairs-cached',
        help='Refresh the pairs files in tests/testdata with the latest data from the '
        'exchange. Use it if you want to run your optimization commands with '
        'up-to-date data.',
        action='store_true',
    ),
    # Backtesting
    "position_stacking": Arg(
        '--eps', '--enable-position-stacking',
        help='Allow buying the same pair multiple times (position stacking).',
        action='store_true',
        default=False,
    ),
    "use_max_market_positions": Arg(
        '--dmmp', '--disable-max-market-positions',
        help='Disable applying `max_open_trades` during backtest '
        '(same as setting `max_open_trades` to a very high number).',
        action='store_false',
        default=True,
    ),
    "live": Arg(
        '-l', '--live',
        help='Use live data.',
        action='store_true',
    ),
    "strategy_list": Arg(
        '--strategy-list',
        help='Provide a comma-separated list of strategies to backtest. '
        'Please note that ticker-interval needs to be set either in config '
        'or via command line. When using this together with `--export trades`, '
        'the strategy-name is injected into the filename '
        '(so `backtest-data.json` becomes `backtest-data-DefaultStrategy.json`',
        nargs='+',
    ),
    "export": Arg(
        '--export',
        help='Export backtest results, argument are: trades. '
        'Example: `--export=trades`',
    ),
    "exportfilename": Arg(
        '--export-filename',
        help='Save backtest results to the file with this filename (default: `%(default)s`). '
        'Requires `--export` to be set as well. '
        'Example: `--export-filename=user_data/backtest_data/backtest_today.json`',
        metavar='PATH',
        default=os.path.join('user_data', 'backtest_data',
                             'backtest-result.json'),
    ),
    # Edge
    "stoploss_range": Arg(
        '--stoplosses',
        help='Defines a range of stoploss values against which edge will assess the strategy. '
        'The format is "min,max,step" (without any space). '
        'Example: `--stoplosses=-0.01,-0.1,-0.001`',
    ),
    # Hyperopt
    "hyperopt": Arg(
        '--customhyperopt',
        help='Specify hyperopt class name (default: `%(default)s`).',
        metavar='NAME',
        default=constants.DEFAULT_HYPEROPT,
    ),
    "hyperopt_path": Arg(
        '--hyperopt-path',
        help='Specify additional lookup path for Hyperopts and Hyperopt Loss functions.',
        metavar='PATH',
    ),
    "epochs": Arg(
        '-e', '--epochs',
        help='Specify number of epochs (default: %(default)d).',
        type=check_int_positive,
        metavar='INT',
        default=constants.HYPEROPT_EPOCH,
    ),
    "spaces": Arg(
        '-s', '--spaces',
        help='Specify which parameters to hyperopt. Space-separated list. '
        'Default: `%(default)s`.',
        choices=['all', 'buy', 'sell', 'roi', 'stoploss'],
        nargs='+',
        default='all',
    ),
    "print_all": Arg(
        '--print-all',
        help='Print all results, not only the best ones.',
        action='store_true',
        default=False,
    ),
    "hyperopt_jobs": Arg(
        '-j', '--job-workers',
        help='The number of concurrently running jobs for hyperoptimization '
        '(hyperopt worker processes). '
        'If -1 (default), all CPUs are used, for -2, all CPUs but one are used, etc. '
        'If 1 is given, no parallel computing code is used at all.',
        type=int,
        metavar='JOBS',
        default=-1,
    ),
    "hyperopt_random_state": Arg(
        '--random-state',
        help='Set random state to some positive integer for reproducible hyperopt results.',
        type=check_int_positive,
        metavar='INT',
    ),
    "hyperopt_min_trades": Arg(
        '--min-trades',
        help="Set minimal desired number of trades for evaluations in the hyperopt "
        "optimization path (default: 1).",
        type=check_int_positive,
        metavar='INT',
        default=1,
    ),
    "hyperopt_continue": Arg(
        "--continue",
        help="Continue hyperopt from previous runs. "
        "By default, temporary files will be removed and hyperopt will start from scratch.",
        default=False,
        action='store_true',
    ),
    "hyperopt_loss": Arg(
        '--hyperopt-loss',
        help='Specify the class name of the hyperopt loss function class (IHyperOptLoss). '
        'Different functions can generate completely different results, '
        'since the target for optimization is different. (default: `%(default)s`).',
        metavar='NAME',
        default=constants.DEFAULT_HYPEROPT_LOSS,
    ),
    # List exchanges
    "print_one_column": Arg(
        '-1', '--one-column',
        help='Print exchanges in one column.',
        action='store_true',
    ),
    # Script options
    "pairs": Arg(
        '-p', '--pairs',
        help='Show profits for only these pairs. Pairs are comma-separated.',
    ),
    # Download data
    "pairs_file": Arg(
        '--pairs-file',
        help='File containing a list of pairs to download.',
        metavar='FILE',
    ),
    "days": Arg(
        '--days',
        help='Download data for given number of days.',
        type=check_int_positive,
        metavar='INT',
    ),
    "exchange": Arg(
        '--exchange',
        help=f'Exchange name (default: `{constants.DEFAULT_EXCHANGE}`). '
        f'Only valid if no config is provided.',
    ),
    "timeframes": Arg(
        '-t', '--timeframes',
        help=f'Specify which tickers to download. Space-separated list. '
        f'Default: `{constants.DEFAULT_DOWNLOAD_TICKER_INTERVALS}`.',
        choices=['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h',
                 '6h', '8h', '12h', '1d', '3d', '1w'],
        nargs='+',
    ),
    "erase": Arg(
        '--erase',
        help='Clean all existing data for the selected exchange/pairs/timeframes.',
        action='store_true',
    ),
    # Plot dataframe
    "indicators1": Arg(
        '--indicators1',
        help='Set indicators from your strategy you want in the first row of the graph. '
        'Comma-separated list. Example: `ema3,ema5`. Default: `%(default)s`.',
        default='sma,ema3,ema5',
    ),
    "indicators2": Arg(
        '--indicators2',
        help='Set indicators from your strategy you want in the third row of the graph. '
        'Comma-separated list. Example: `fastd,fastk`. Default: `%(default)s`.',
        default='macd,macdsignal',
    ),
    "plot_limit": Arg(
        '--plot-limit',
        help='Specify tick limit for plotting. Notice: too high values cause huge files. '
        'Default: %(default)s.',
        type=check_int_positive,
        metavar='INT',
        default=750,
    ),
    "trade_source": Arg(
        '--trade-source',
        help='Specify the source for trades (Can be DB or file (backtest file)) '
        'Default: %(default)s',
        choices=["DB", "file"],
        default="file",
    ),
}
