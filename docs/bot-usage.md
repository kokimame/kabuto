# Start the bot

This page explains the different parameters of the bot and how to run it.


## Bot commands

```
usage: freqtrade [-h] [-v] [--logfile FILE] [--version] [-c PATH] [-d PATH]
                 [-s NAME] [--strategy-path PATH] [--db-url PATH]
                 [--sd-notify]
                 {backtesting,edge,hyperopt} ...

Free, open source crypto trading bot

positional arguments:
  {backtesting,edge,hyperopt}
    backtesting         Backtesting module.
    edge                Edge module.
    hyperopt            Hyperopt module.

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Verbose mode (-vv for more, -vvv to get all messages).
  --logfile FILE        Log to the file specified
  -V, --version         show program's version number and exit
  -c PATH, --config PATH
                        Specify configuration file (default: None). Multiple
                        --config options may be used. Can be set to '-' to
                        read config from stdin.
  -d PATH, --datadir PATH
                        Path to backtest data.
  -s NAME, --strategy NAME
                        Specify strategy class name (default:
                        DefaultStrategy).
  --strategy-path PATH  Specify additional strategy lookup path.
  --db-url PATH         Override trades database URL, this is useful if
                        dry_run is enabled or in custom deployments (default:
                        None).
  --sd-notify           Notify systemd service manager.
```

### How to use a different configuration file?

The bot allows you to select which configuration file you want to use. Per
default, the bot will load the file `./config.json`

```bash
freqtrade -c path/far/far/away/config.json
```

### How to use multiple configuration files?

The bot allows you to use multiple configuration files by specifying multiple
`-c/--config` configuration options in the command line. Configuration parameters
defined in the last configuration file override parameters with the same name
defined in the previous configuration file specified in the command line.

For example, you can make a separate configuration file with your key and secrete
for the Exchange you use for trading, specify default configuration file with
empty key and secrete values while running in the Dry Mode (which does not actually
require them):

```bash
freqtrade -c ./config.json
```

and specify both configuration files when running in the normal Live Trade Mode:

```bash
freqtrade -c ./config.json -c path/to/secrets/keys.config.json
```

This could help you hide your private Exchange key and Exchange secrete on you local machine
by setting appropriate file permissions for the file which contains actual secrets and, additionally,
prevent unintended disclosure of sensitive private data when you publish examples
of your configuration in the project issues or in the Internet.

See more details on this technique with examples in the documentation page on
[configuration](configuration.md).

### How to use **--strategy**?

This parameter will allow you to load your custom strategy class.
Per default without `--strategy` or `-s` the bot will load the
`DefaultStrategy` included with the bot (`freqtrade/strategy/default_strategy.py`).

The bot will search your strategy file within `user_data/strategies` and `freqtrade/strategy`.

To load a strategy, simply pass the class name (e.g.: `CustomStrategy`) in this parameter.

**Example:**
In `user_data/strategies` you have a file `my_awesome_strategy.py` which has
a strategy class called `AwesomeStrategy` to load it:

```bash
freqtrade --strategy AwesomeStrategy
```

If the bot does not find your strategy file, it will display in an error
message the reason (File not found, or errors in your code).

Learn more about strategy file in
[Strategy Customization](strategy-customization.md).

### How to use **--strategy-path**?

This parameter allows you to add an additional strategy lookup path, which gets
checked before the default locations (The passed path must be a directory!):
```bash
freqtrade --strategy AwesomeStrategy --strategy-path /some/directory
```

#### How to install a strategy?

This is very simple. Copy paste your strategy file into the directory
`user_data/strategies` or use `--strategy-path`. And voila, the bot is ready to use it.

### How to use **--db-url**?

When you run the bot in Dry-run mode, per default no transactions are
stored in a database. If you want to store your bot actions in a DB
using `--db-url`. This can also be used to specify a custom database
in production mode. Example command:

```bash
freqtrade -c config.json --db-url sqlite:///tradesv3.dry_run.sqlite
```

## Backtesting commands

Backtesting also uses the config specified via `-c/--config`.

```
usage: freqtrade backtesting [-h] [-i TICKER_INTERVAL] [--timerange TIMERANGE]
                           [--max_open_trades MAX_OPEN_TRADES]
                           [--stake_amount STAKE_AMOUNT] [-r] [--eps] [--dmmp]
                           [-l]
                           [--strategy-list STRATEGY_LIST [STRATEGY_LIST ...]]
                           [--export EXPORT] [--export-filename PATH]

optional arguments:
  -h, --help            show this help message and exit
  -i TICKER_INTERVAL, --ticker-interval TICKER_INTERVAL
                        Specify ticker interval (1m, 5m, 30m, 1h, 1d).
  --timerange TIMERANGE
                        Specify what timerange of data to use.
  --max_open_trades MAX_OPEN_TRADES
                        Specify max_open_trades to use.
  --stake_amount STAKE_AMOUNT
                        Specify stake_amount.
  -r, --refresh-pairs-cached
                        Refresh the pairs files in tests/testdata with the
                        latest data from the exchange. Use it if you want to
                        run your optimization commands with up-to-date data.
  --eps, --enable-position-stacking
                        Allow buying the same pair multiple times (position
                        stacking).
  --dmmp, --disable-max-market-positions
                        Disable applying `max_open_trades` during backtest
                        (same as setting `max_open_trades` to a very high
                        number).
  -l, --live            Use live data.
  --strategy-list STRATEGY_LIST [STRATEGY_LIST ...]
                        Provide a commaseparated list of strategies to
                        backtest Please note that ticker-interval needs to be
                        set either in config or via command line. When using
                        this together with --export trades, the strategy-name
                        is injected into the filename (so backtest-data.json
                        becomes backtest-data-DefaultStrategy.json
  --export EXPORT       Export backtest results, argument are: trades. Example
                        --export=trades
  --export-filename PATH
                        Save backtest results to this filename requires
                        --export to be set as well Example --export-
                        filename=user_data/backtest_data/backtest_today.json
                        (default: user_data/backtest_data/backtest-
                        result.json)
```

### How to use **--refresh-pairs-cached** parameter?

The first time your run Backtesting, it will take the pairs you have
set in your config file and download data from the Exchange.

If for any reason you want to update your data set, you use
`--refresh-pairs-cached` to force Backtesting to update the data it has.

!!! Note
    Use it only if you want to update your data set. You will not be able to come back to the previous version.

To test your strategy with latest data, we recommend continuing using
the parameter `-l` or `--live`.

## Hyperopt commands

To optimize your strategy, you can use hyperopt parameter hyperoptimization
to find optimal parameter values for your stategy.

```
usage: freqtrade hyperopt [-h] [-i TICKER_INTERVAL] [--timerange TIMERANGE]
                          [--max_open_trades INT]
                          [--stake_amount STAKE_AMOUNT] [-r]
                          [--customhyperopt NAME] [--eps] [-e INT]
                          [-s {all,buy,sell,roi,stoploss} [{all,buy,sell,roi,stoploss} ...]]
                          [--dmmp] [--print-all] [-j JOBS]
                          [--random-state INT] [--min-trades INT] [--continue]
                          [--hyperopt-loss NAME]

optional arguments:
  -h, --help            show this help message and exit
  -i TICKER_INTERVAL, --ticker-interval TICKER_INTERVAL
                        Specify ticker interval (`1m`, `5m`, `30m`, `1h`,
                        `1d`).
  --timerange TIMERANGE
                        Specify what timerange of data to use.
  --max_open_trades INT
                        Specify max_open_trades to use.
  --stake_amount STAKE_AMOUNT
                        Specify stake_amount.
  -r, --refresh-pairs-cached
                        Refresh the pairs files in tests/testdata with the
                        latest data from the exchange. Use it if you want to
                        run your optimization commands with up-to-date data.
  --customhyperopt NAME
                        Specify hyperopt class name (default:
                        `DefaultHyperOpts`).
  --eps, --enable-position-stacking
                        Allow buying the same pair multiple times (position
                        stacking).
  -e INT, --epochs INT  Specify number of epochs (default: 100).
  -s {all,buy,sell,roi,stoploss} [{all,buy,sell,roi,stoploss} ...], --spaces {all,buy,sell,roi,stoploss} [{all,buy,sell,roi,stoploss} ...]
                        Specify which parameters to hyperopt. Space-separated
                        list. Default: `all`.
  --dmmp, --disable-max-market-positions
                        Disable applying `max_open_trades` during backtest
                        (same as setting `max_open_trades` to a very high
                        number).
  --print-all           Print all results, not only the best ones.
  -j JOBS, --job-workers JOBS
                        The number of concurrently running jobs for
                        hyperoptimization (hyperopt worker processes). If -1
                        (default), all CPUs are used, for -2, all CPUs but one
                        are used, etc. If 1 is given, no parallel computing
                        code is used at all.
  --random-state INT    Set random state to some positive integer for
                        reproducible hyperopt results.
  --min-trades INT      Set minimal desired number of trades for evaluations
                        in the hyperopt optimization path (default: 1).
  --continue            Continue hyperopt from previous runs. By default,
                        temporary files will be removed and hyperopt will
                        start from scratch.
  --hyperopt-loss       NAME
                        Specify the class name of the hyperopt loss function
                        class (IHyperOptLoss). Different functions can
                        generate completely different results, since the
                        target for optimization is different. (default:
                        `DefaultHyperOptLoss`).
```

## Edge commands

To know your trade expectacny and winrate against historical data, you can use Edge.

```
usage: freqtrade edge [-h] [-i TICKER_INTERVAL] [--timerange TIMERANGE]
                    [--max_open_trades MAX_OPEN_TRADES]
                    [--stake_amount STAKE_AMOUNT] [-r]
                    [--stoplosses STOPLOSS_RANGE]

optional arguments:
  -h, --help            show this help message and exit
  -i TICKER_INTERVAL, --ticker-interval TICKER_INTERVAL
                        Specify ticker interval (1m, 5m, 30m, 1h, 1d).
  --timerange TIMERANGE
                        Specify what timerange of data to use.
  --max_open_trades MAX_OPEN_TRADES
                        Specify max_open_trades to use.
  --stake_amount STAKE_AMOUNT
                        Specify stake_amount.
  -r, --refresh-pairs-cached
                        Refresh the pairs files in tests/testdata with the
                        latest data from the exchange. Use it if you want to
                        run your optimization commands with up-to-date data.
  --stoplosses STOPLOSS_RANGE
                        Defines a range of stoploss against which edge will
                        assess the strategy the format is "min,max,step"
                        (without any space).example:
                        --stoplosses=-0.01,-0.1,-0.001
```

To understand edge and how to read the results, please read the [edge documentation](edge.md).

## A parameter missing in the configuration?

All parameters for `main.py`, `backtesting`, `hyperopt` are referenced
in [misc.py](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/misc.py#L84)

## Next step

The optimal strategy of the bot will change with time depending of the market trends. The next step is to
[Strategy Customization](strategy-customization.md).
