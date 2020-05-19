# Configure the bot

Freqtrade has many configurable features and possibilities.
By default, these settings are configured via the configuration file (see below).

## The Freqtrade configuration file

The bot uses a set of configuration parameters during its operation that all together conform the bot configuration. It normally reads its configuration from a file (Freqtrade configuration file).

Per default, the bot loads the configuration from the `config.json` file, located in the current working directory.

You can specify a different configuration file used by the bot with the `-c/--config` command line option.

In some advanced use cases, multiple configuration files can be specified and used by the bot or the bot can read its configuration parameters from the process standard input stream.

If you used the [Quick start](installation.md/#quick-start) method for installing 
the bot, the installation script should have already created the default configuration file (`config.json`) for you.

If default configuration file is not created we recommend you to copy and use the `config.json.example` as a template
for your bot configuration.

The Freqtrade configuration file is to be written in the JSON format.

Additionally to the standard JSON syntax, you may use one-line `// ...` and multi-line `/* ... */` comments in your configuration files and trailing commas in the lists of parameters.

Do not worry if you are not familiar with JSON format -- simply open the configuration file with an editor of your choice, make some changes to the parameters you need, save your changes and, finally, restart the bot or, if it was previously stopped, run it again with the changes you made to the configuration. The bot validates syntax of the configuration file at startup and will warn you if you made any errors editing it, pointing out problematic lines.

## Configuration parameters

The table below will list all configuration parameters available.

Freqtrade can also load many options via command line (CLI) arguments (check out the commands `--help` output for details).
The prevelance for all Options is as follows:

- CLI arguments override any other option
- Configuration files are used in sequence (last file wins), and override Strategy configurations.
- Strategy configurations are only used if they are not set via configuration or via command line arguments. These options are marked with [Strategy Override](#parameters-in-the-strategy) in the below table.

Mandatory parameters are marked as **Required**, which means that they are required to be set in one of the possible ways.

|  Parameter | Description |
|------------|-------------|
| `max_open_trades` | **Required.** Number of open trades your bot is allowed to have. Only one open trade per pair is possible, so the length of your pairlist is another limitation which can apply. If -1 then it is ignored (i.e. potentially unlimited open trades, limited by the pairlist). [More information below](#configuring-amount-per-trade).<br> **Datatype:** Positive integer or -1.
| `stake_currency` | **Required.** Crypto-currency used for trading. [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** String
| `stake_amount` | **Required.** Amount of crypto-currency your bot will use for each trade. Set it to `"unlimited"` to allow the bot to use all available balance. [More information below](#configuring-amount-per-trade). [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** Positive float or `"unlimited"`.
| `tradable_balance_ratio` | Ratio of the total account balance the bot is allowed to trade. [More information below](#configuring-amount-per-trade). <br>*Defaults to `0.99` 99%).*<br> **Datatype:** Positive float between `0.1` and `1.0`.
| `amend_last_stake_amount` | Use reduced last stake amount if necessary. [More information below](#configuring-amount-per-trade). <br>*Defaults to `false`.* <br> **Datatype:** Boolean
| `last_stake_amount_min_ratio` | Defines minimum stake amount that has to be left and executed. Applies only to the last stake amount when it's amended to a reduced value (i.e. if `amend_last_stake_amount` is set to `true`). [More information below](#configuring-amount-per-trade). <br>*Defaults to `0.5`.* <br> **Datatype:** Float (as ratio)
| `amount_reserve_percent` | Reserve some amount in min pair stake amount. The bot will reserve `amount_reserve_percent` + stoploss value when calculating min pair stake amount in order to avoid possible trade refusals. <br>*Defaults to `0.05` (5%).* <br> **Datatype:** Positive Float as ratio.
| `ticker_interval` | The timeframe (ticker interval) to use (e.g `1m`, `5m`, `15m`, `30m`, `1h` ...). [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** String
| `fiat_display_currency` | Fiat currency used to show your profits. [More information below](#what-values-can-be-used-for-fiat_display_currency). <br> **Datatype:** String
| `dry_run` | **Required.** Define if the bot must be in Dry Run or production mode. <br>*Defaults to `true`.* <br> **Datatype:** Boolean
| `dry_run_wallet` | Define the starting amount in stake currency for the simulated wallet used by the bot running in the Dry Run mode.<br>*Defaults to `1000`.* <br> **Datatype:** Float
| `cancel_open_orders_on_exit` | Cancel open orders when the `/stop` RPC command is issued, `Ctrl+C` is pressed or the bot dies unexpectedly. When set to `true`, this allows you to use `/stop` to cancel unfilled and partially filled orders in the event of a market crash. It does not impact open positions. <br>*Defaults to `false`.* <br> **Datatype:** Boolean
| `process_only_new_candles` | Enable processing of indicators only when new candles arrive. If false each loop populates the indicators, this will mean the same candle is processed many times creating system load but can be useful of your strategy depends on tick data not only candle. [Strategy Override](#parameters-in-the-strategy). <br>*Defaults to `false`.*  <br> **Datatype:** Boolean
| `minimal_roi` | **Required.** Set the threshold in percent the bot will use to sell a trade. [More information below](#understand-minimal_roi). [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** Dict
| `stoploss` |  **Required.** Value of the stoploss in percent used by the bot. More details in the [stoploss documentation](stoploss.md). [Strategy Override](#parameters-in-the-strategy).  <br> **Datatype:** Float (as ratio)
| `trailing_stop` | Enables trailing stoploss (based on `stoploss` in either configuration or strategy file). More details in the [stoploss documentation](stoploss.md). [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** Boolean
| `trailing_stop_positive` | Changes stoploss once profit has been reached. More details in the [stoploss documentation](stoploss.md). [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** Float
| `trailing_stop_positive_offset` | Offset on when to apply `trailing_stop_positive`. Percentage value which should be positive. More details in the [stoploss documentation](stoploss.md). [Strategy Override](#parameters-in-the-strategy). <br>*Defaults to `0.0` (no offset).* <br> **Datatype:** Float
| `trailing_only_offset_is_reached` | Only apply trailing stoploss when the offset is reached. [stoploss documentation](stoploss.md). [Strategy Override](#parameters-in-the-strategy). <br>*Defaults to `false`.*  <br> **Datatype:** Boolean
| `unfilledtimeout.buy` | **Required.** How long (in minutes) the bot will wait for an unfilled buy order to complete, after which the order will be cancelled. [Strategy Override](#parameters-in-the-strategy).<br> **Datatype:** Integer
| `unfilledtimeout.sell` | **Required.** How long (in minutes) the bot will wait for an unfilled sell order to complete, after which the order will be cancelled. [Strategy Override](#parameters-in-the-strategy).<br> **Datatype:** Integer
| `bid_strategy.price_side` | Select the side of the spread the bot should look at to get the buy rate. [More information below](#buy-price-side).<br> *Defaults to `bid`.* <br> **Datatype:** String (either `ask` or `bid`).
| `bid_strategy.ask_last_balance` | **Required.** Set the bidding price. More information [below](#buy-price-without-orderbook-enabled).
| `bid_strategy.use_order_book` | Enable buying using the rates in [Order Book Bids](#buy-price-with-orderbook-enabled). <br> **Datatype:** Boolean
| `bid_strategy.order_book_top` | Bot will use the top N rate in Order Book Bids to buy. I.e. a value of 2 will allow the bot to pick the 2nd bid rate in [Order Book Bids](#buy-price-with-orderbook-enabled). <br>*Defaults to `1`.*  <br> **Datatype:** Positive Integer
| `bid_strategy. check_depth_of_market.enabled` | Do not buy if the difference of buy orders and sell orders is met in Order Book. [Check market depth](#check-depth-of-market). <br>*Defaults to `false`.* <br> **Datatype:** Boolean
| `bid_strategy. check_depth_of_market.bids_to_ask_delta` | The difference ratio of buy orders and sell orders found in Order Book. A value below 1 means sell order size is greater, while value greater than 1 means buy order size is higher. [Check market depth](#check-depth-of-market) <br> *Defaults to `0`.*  <br> **Datatype:** Float (as ratio)
| `ask_strategy.price_side` | Select the side of the spread the bot should look at to get the sell rate. [More information below](#sell-price-side).<br> *Defaults to `ask`.* <br> **Datatype:** String (either `ask` or `bid`).
| `ask_strategy.use_order_book` | Enable selling of open trades using [Order Book Asks](#sell-price-with-orderbook-enabled). <br> **Datatype:** Boolean
| `ask_strategy.order_book_min` | Bot will scan from the top min to max Order Book Asks searching for a profitable rate. <br>*Defaults to `1`.* <br> **Datatype:** Positive Integer
| `ask_strategy.order_book_max` | Bot will scan from the top min to max Order Book Asks searching for a profitable rate. <br>*Defaults to `1`.* <br> **Datatype:** Positive Integer
| `ask_strategy.use_sell_signal` | Use sell signals produced by the strategy in addition to the `minimal_roi`. [Strategy Override](#parameters-in-the-strategy). <br>*Defaults to `true`.* <br> **Datatype:** Boolean
| `ask_strategy.sell_profit_only` | Wait until the bot makes a positive profit before taking a sell decision. [Strategy Override](#parameters-in-the-strategy). <br>*Defaults to `false`.* <br> **Datatype:** Boolean
| `ask_strategy.ignore_roi_if_buy_signal` | Do not sell if the buy signal is still active. This setting takes preference over `minimal_roi` and `use_sell_signal`. [Strategy Override](#parameters-in-the-strategy). <br>*Defaults to `false`.* <br> **Datatype:** Boolean
| `order_types` | Configure order-types depending on the action (`"buy"`, `"sell"`, `"stoploss"`, `"stoploss_on_exchange"`). [More information below](#understand-order_types). [Strategy Override](#parameters-in-the-strategy).<br> **Datatype:** Dict
| `order_time_in_force` | Configure time in force for buy and sell orders. [More information below](#understand-order_time_in_force). [Strategy Override](#parameters-in-the-strategy). <br> **Datatype:** Dict
| `exchange.name` | **Required.** Name of the exchange class to use. [List below](#user-content-what-values-for-exchangename). <br> **Datatype:** String
| `exchange.sandbox` | Use the 'sandbox' version of the exchange, where the exchange provides a sandbox for risk-free integration. See [here](sandbox-testing.md) in more details.<br> **Datatype:** Boolean
| `exchange.key` | API key to use for the exchange. Only required when you are in production mode.<br>**Keep it in secret, do not disclose publicly.** <br> **Datatype:** String
| `exchange.secret` | API secret to use for the exchange. Only required when you are in production mode.<br>**Keep it in secret, do not disclose publicly.** <br> **Datatype:** String
| `exchange.password` | API password to use for the exchange. Only required when you are in production mode and for exchanges that use password for API requests.<br>**Keep it in secret, do not disclose publicly.** <br> **Datatype:** String
| `exchange.pair_whitelist` | List of pairs to use by the bot for trading and to check for potential trades during backtesting. Not used by VolumePairList (see [below](#pairlists-and-pairlist-handlers)). <br> **Datatype:** List
| `exchange.pair_blacklist` | List of pairs the bot must absolutely avoid for trading and backtesting (see [below](#pairlists-and-pairlist-handlers)). <br> **Datatype:** List
| `exchange.ccxt_config` | Additional CCXT parameters passed to the regular ccxt instance. Parameters may differ from exchange to exchange and are documented in the [ccxt documentation](https://ccxt.readthedocs.io/en/latest/manual.html#instantiation) <br> **Datatype:** Dict
| `exchange.ccxt_async_config` | Additional CCXT parameters passed to the async ccxt instance. Parameters may differ from exchange to exchange  and are documented in the [ccxt documentation](https://ccxt.readthedocs.io/en/latest/manual.html#instantiation) <br> **Datatype:** Dict
| `exchange.markets_refresh_interval` | The interval in minutes in which markets are reloaded. <br>*Defaults to `60` minutes.* <br> **Datatype:** Positive Integer
| `edge.*` | Please refer to [edge configuration document](edge.md) for detailed explanation.
| `experimental.block_bad_exchanges` | Block exchanges known to not work with freqtrade. Leave on default unless you want to test if that exchange works now. <br>*Defaults to `true`.* <br> **Datatype:** Boolean
| `pairlists` | Define one or more pairlists to be used. [More information below](#pairlists-and-pairlist-handlers). <br>*Defaults to `StaticPairList`.*  <br> **Datatype:** List of Dicts
| `telegram.enabled` | Enable the usage of Telegram. <br> **Datatype:** Boolean
| `telegram.token` | Your Telegram bot token. Only required if `telegram.enabled` is `true`. <br>**Keep it in secret, do not disclose publicly.** <br> **Datatype:** String
| `telegram.chat_id` | Your personal Telegram account id. Only required if `telegram.enabled` is `true`. <br>**Keep it in secret, do not disclose publicly.** <br> **Datatype:** String
| `webhook.enabled` | Enable usage of Webhook notifications <br> **Datatype:** Boolean
| `webhook.url` | URL for the webhook. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details. <br> **Datatype:** String
| `webhook.webhookbuy` | Payload to send on buy. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details. <br> **Datatype:** String
| `webhook.webhookbuycancel` | Payload to send on buy order cancel. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details. <br> **Datatype:** String
| `webhook.webhooksell` | Payload to send on sell. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details. <br> **Datatype:** String
| `webhook.webhooksellcancel` | Payload to send on sell order cancel. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details. <br> **Datatype:** String
| `webhook.webhookstatus` | Payload to send on status calls. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details. <br> **Datatype:** String
| `api_server.enabled` | Enable usage of API Server. See the [API Server documentation](rest-api.md) for more details. <br> **Datatype:** Boolean
| `api_server.listen_ip_address` | Bind IP address. See the [API Server documentation](rest-api.md) for more details. <br> **Datatype:** IPv4
| `api_server.listen_port` | Bind Port. See the [API Server documentation](rest-api.md) for more details. <br>**Datatype:** Integer between 1024 and 65535
| `api_server.username` | Username for API server. See the [API Server documentation](rest-api.md) for more details. <br>**Keep it in secret, do not disclose publicly.**<br> **Datatype:** String
| `api_server.password` | Password for API server. See the [API Server documentation](rest-api.md) for more details. <br>**Keep it in secret, do not disclose publicly.**<br> **Datatype:** String
| `db_url` | Declares database URL to use. NOTE: This defaults to `sqlite:///tradesv3.dryrun.sqlite` if `dry_run` is `true`, and to `sqlite:///tradesv3.sqlite` for production instances. <br> **Datatype:** String, SQLAlchemy connect string
| `initial_state` | Defines the initial application state. More information below. <br>*Defaults to `stopped`.* <br> **Datatype:** Enum, either `stopped` or `running`
| `forcebuy_enable` | Enables the RPC Commands to force a buy. More information below. <br> **Datatype:** Boolean
| `strategy` | **Required** Defines Strategy class to use. Recommended to be set via `--strategy NAME`. <br> **Datatype:** ClassName
| `strategy_path` | Adds an additional strategy lookup path (must be a directory). <br> **Datatype:** String
| `internals.process_throttle_secs` | Set the process throttle. Value in second. <br>*Defaults to `5` seconds.* <br> **Datatype:** Positive Integer
| `internals.heartbeat_interval` | Print heartbeat message every N seconds. Set to 0 to disable heartbeat messages. <br>*Defaults to `60` seconds.* <br> **Datatype:** Positive Integer or 0
| `internals.sd_notify` | Enables use of the sd_notify protocol to tell systemd service manager about changes in the bot state and issue keep-alive pings. See [here](installation.md#7-optional-configure-freqtrade-as-a-systemd-service) for more details. <br> **Datatype:** Boolean
| `logfile` | Specifies logfile name. Uses a rolling strategy for log file rotation for 10 files with the 1MB limit per file. <br> **Datatype:** String
| `user_data_dir` | Directory containing user data. <br> *Defaults to `./user_data/`*. <br> **Datatype:** String
| `dataformat_ohlcv` | Data format to use to store historical candle (OHLCV) data. <br> *Defaults to `json`*. <br> **Datatype:** String
| `dataformat_trades` | Data format to use to store historical trades data. <br> *Defaults to `jsongz`*. <br> **Datatype:** String

### Parameters in the strategy

The following parameters can be set in either configuration file or strategy.
Values set in the configuration file always overwrite values set in the strategy.

* `minimal_roi`
* `ticker_interval`
* `stoploss`
* `trailing_stop`
* `trailing_stop_positive`
* `trailing_stop_positive_offset`
* `trailing_only_offset_is_reached`
* `process_only_new_candles`
* `order_types`
* `order_time_in_force`
* `stake_currency`
* `stake_amount`
* `unfilledtimeout`
* `use_sell_signal` (ask_strategy)
* `sell_profit_only` (ask_strategy)
* `ignore_roi_if_buy_signal` (ask_strategy)

### Configuring amount per trade

There are several methods to configure how much of the stake currency the bot will use to enter a trade. All methods respect the [available balance configuration](#available-balance) as explained below.

#### Available balance

By default, the bot assumes that the `complete amount - 1%` is at it's disposal, and when using [dynamic stake amount](#dynamic-stake-amount), it will split the complete balance into `max_open_trades` buckets per trade.
Freqtrade will reserve 1% for eventual fees when entering a trade and will therefore not touch that by default.

You can configure the "untouched" amount by using the `tradable_balance_ratio` setting.

For example, if you have 10 ETH available in your wallet on the exchange and `tradable_balance_ratio=0.5` (which is 50%), then the bot will use a maximum amount of 5 ETH for trading and considers this as available balance. The rest of the wallet is untouched by the trades.

!!! Warning
    The `tradable_balance_ratio` setting applies to the current balance (free balance + tied up in trades). Therefore, assuming the starting balance of 1000, a configuration with `tradable_balance_ratio=0.99` will not guarantee that 10 currency units will always remain available on the exchange. For example, the free amount may reduce to 5 units if the total balance is reduced to 500 (either by a losing streak, or by withdrawing balance).

#### Amend last stake amount

Assuming we have the tradable balance of 1000 USDT, `stake_amount=400`, and `max_open_trades=3`.
The bot would open 2 trades, and will be unable to fill the last trading slot, since the requested 400 USDT are no longer available, since 800 USDT are already tied in other trades.

To overcome this, the option `amend_last_stake_amount` can be set to `True`, which will enable the bot to reduce stake_amount to the available balance in order to fill the last trade slot.

In the example above this would mean:

- Trade1: 400 USDT
- Trade2: 400 USDT
- Trade3: 200 USDT

!!! Note
    This option only applies with [Static stake amount](#static-stake-amount) - since [Dynamic stake amount](#dynamic-stake-amount) divides the balances evenly.

!!! Note
    The minimum last stake amount can be configured using `amend_last_stake_amount` - which defaults to 0.5 (50%). This means that the minimum stake amount that's ever used is `stake_amount * 0.5`. This avoids very low stake amounts, that are close to the minimum tradable amount for the pair and can be refused by the exchange.

#### Static stake amount

The `stake_amount` configuration statically configures the amount of stake-currency your bot will use for each trade.

The minimal configuration value is 0.0001, however, please check your exchange's trading minimums for the stake currency you're using to avoid problems.

This setting works in combination with `max_open_trades`. The maximum capital engaged in trades is `stake_amount * max_open_trades`.
For example, the bot will at most use (0.05 BTC x 3) = 0.15 BTC, assuming a configuration of `max_open_trades=3` and `stake_amount=0.05`.

!!! Note
    This setting respects the [available balance configuration](#available-balance).

#### Dynamic stake amount

Alternatively, you can use a dynamic stake amount, which will use the available balance on the exchange, and divide that equally by the amount of allowed trades (`max_open_trades`).

To configure this, set `stake_amount="unlimited"`. We also recommend to set `tradable_balance_ratio=0.99` (99%) - to keep a minimum balance for eventual fees.

In this case a trade amount is calculated as:

```python
currency_balance / (max_open_trades - current_open_trades)
```

To allow the bot to trade all the available `stake_currency` in your account (minus `tradable_balance_ratio`) set

```json
"stake_amount" : "unlimited",
"tradable_balance_ratio": 0.99,
```

!!! Note
    This configuration will allow increasing / decreasing stakes depending on the performance of the bot (lower stake if bot is loosing, higher stakes if the bot has a winning record, since higher balances are available).

!!! Note "When using Dry-Run Mode"
    When using `"stake_amount" : "unlimited",` in combination with Dry-Run, the balance will be simulated starting with a stake of `dry_run_wallet` which will evolve over time. It is therefore important to set `dry_run_wallet` to a sensible value (like 0.05 or 0.01 for BTC and 1000 or 100 for USDT, for example), otherwise it may simulate trades with 100 BTC (or more) or 0.05 USDT (or less) at once - which may not correspond to your real available balance or is less than the exchange minimal limit for the order amount for the stake currency.

### Understand minimal_roi

The `minimal_roi` configuration parameter is a JSON object where the key is a duration
in minutes and the value is the minimum ROI in percent.
See the example below:

```json
"minimal_roi": {
    "40": 0.0,    # Sell after 40 minutes if the profit is not negative
    "30": 0.01,   # Sell after 30 minutes if there is at least 1% profit
    "20": 0.02,   # Sell after 20 minutes if there is at least 2% profit
    "0":  0.04    # Sell immediately if there is at least 4% profit
},
```

Most of the strategy files already include the optimal `minimal_roi` value.
This parameter can be set in either Strategy or Configuration file. If you use it in the configuration file, it will override the
`minimal_roi` value from the strategy file.
If it is not set in either Strategy or Configuration, a default of 1000% `{"0": 10}` is used, and minimal roi is disabled unless your trade generates 1000% profit.

!!! Note "Special case to forcesell after a specific time"
    A special case presents using `"<N>": -1` as ROI. This forces the bot to sell a trade after N Minutes, no matter if it's positive or negative, so represents a time-limited force-sell.

### Understand stoploss

Go to the [stoploss documentation](stoploss.md) for more details.

### Understand trailing stoploss

Go to the [trailing stoploss Documentation](stoploss.md#trailing-stop-loss) for details on trailing stoploss.

### Understand initial_state

The `initial_state` configuration parameter is an optional field that defines the initial application state.
Possible values are `running` or `stopped`. (default=`running`)
If the value is `stopped` the bot has to be started with `/start` first.

### Understand forcebuy_enable

The `forcebuy_enable` configuration parameter enables the usage of forcebuy commands via Telegram.
This is disabled for security reasons by default, and will show a warning message on startup if enabled.
For example, you can send `/forcebuy ETH/BTC` Telegram command when this feature if enabled to the bot,
who then buys the pair and holds it until a regular sell-signal (ROI, stoploss, /forcesell) appears.

This can be dangerous with some strategies, so use with care.

See [the telegram documentation](telegram-usage.md) for details on usage.

### Understand process_throttle_secs

The `process_throttle_secs` configuration parameter is an optional field that defines in seconds how long the bot should wait
before asking the strategy if we should buy or a sell an asset. After each wait period, the strategy is asked again for
every opened trade wether or not we should sell, and for all the remaining pairs (either the dynamic list of pairs or
the static list of pairs) if we should buy.

### Understand order_types

The `order_types` configuration parameter maps actions (`buy`, `sell`, `stoploss`) to order-types (`market`, `limit`, ...) as well as configures stoploss to be on the exchange and defines stoploss on exchange update interval in seconds.

This allows to buy using limit orders, sell using
limit-orders, and create stoplosses using using market orders. It also allows to set the
stoploss "on exchange" which means stoploss order would be placed immediately once
the buy order is fulfilled.
If `stoploss_on_exchange` and `trailing_stop` are both set, then the bot will use `stoploss_on_exchange_interval` to check and update the stoploss on exchange periodically.
`order_types` can be set in the configuration file or in the strategy.
`order_types` set in the configuration file overwrites values set in the strategy as a whole, so you need to configure the whole `order_types` dictionary in one place.

If this is configured, the following 4 values (`buy`, `sell`, `stoploss` and
`stoploss_on_exchange`) need to be present, otherwise the bot will fail to start.

`emergencysell` is an optional value, which defaults to `market` and is used when creating stoploss on exchange orders fails.
The below is the default which is used if this is not configured in either strategy or configuration file.

Since `stoploss_on_exchange` uses limit orders, the exchange needs 2 prices, the stoploss_price and the Limit price.
`stoploss` defines the stop-price - and limit should be slightly below this. This defaults to 0.99 / 1% (configurable via `stoploss_on_exchange_limit_ratio`).
Calculation example: we bought the asset at 100$.
Stop-price is 95$, then limit would be `95 * 0.99 = 94.05$` - so the stoploss will happen between 95$ and 94.05$.

Syntax for Strategy:

```python
order_types = {
    "buy": "limit",
    "sell": "limit",
    "emergencysell": "market",
    "stoploss": "market",
    "stoploss_on_exchange": False,
    "stoploss_on_exchange_interval": 60,
    "stoploss_on_exchange_limit_ratio": 0.99,
}
```

Configuration:

```json
"order_types": {
    "buy": "limit",
    "sell": "limit",
    "emergencysell": "market",
    "stoploss": "market",
    "stoploss_on_exchange": false,
    "stoploss_on_exchange_interval": 60
}
```

!!! Note
    Not all exchanges support "market" orders.
    The following message will be shown if your exchange does not support market orders:
    `"Exchange <yourexchange>  does not support market orders."`

!!! Note
    Stoploss on exchange interval is not mandatory. Do not change its value if you are
    unsure of what you are doing. For more information about how stoploss works please
    refer to [the stoploss documentation](stoploss.md).

!!! Note
    If `stoploss_on_exchange` is enabled and the stoploss is cancelled manually on the exchange, then the bot will create a new order.

!!! Warning "Warning: stoploss_on_exchange failures"
    If stoploss on exchange creation fails for some reason, then an "emergency sell" is initiated. By default, this will sell the asset using a market order. The order-type for the emergency-sell can be changed by setting the `emergencysell` value in the `order_types` dictionary - however this is not advised.

### Understand order_time_in_force

The `order_time_in_force` configuration parameter defines the policy by which the order
is executed on the exchange. Three commonly used time in force are:

**GTC (Good Till Canceled):**

This is most of the time the default time in force. It means the order will remain
on exchange till it is canceled by user. It can be fully or partially fulfilled.
If partially fulfilled, the remaining will stay on the exchange till cancelled.

**FOK (Fill Or Kill):**

It means if the order is not executed immediately AND fully then it is canceled by the exchange.

**IOC (Immediate Or Canceled):**

It is the same as FOK (above) except it can be partially fulfilled. The remaining part
is automatically cancelled by the exchange.

The `order_time_in_force` parameter contains a dict with buy and sell time in force policy values.
This can be set in the configuration file or in the strategy.
Values set in the configuration file overwrites values set in the strategy.

The possible values are: `gtc` (default), `fok` or `ioc`.

``` python
"order_time_in_force": {
    "buy": "gtc",
    "sell": "gtc"
},
```

!!! Warning
    This is an ongoing work. For now it is supported only for binance and only for buy orders.
    Please don't change the default value unless you know what you are doing.

### Exchange configuration

Freqtrade is based on [CCXT library](https://github.com/ccxt/ccxt) that supports over 100 cryptocurrency
exchange markets and trading APIs. The complete up-to-date list can be found in the
[CCXT repo homepage](https://github.com/ccxt/ccxt/tree/master/python).
 However, the bot was tested by the development team with only Bittrex, Binance and Kraken,
 so the these are the only officially supported exhanges:

- [Bittrex](https://bittrex.com/): "bittrex"
- [Binance](https://www.binance.com/): "binance"
- [Kraken](https://kraken.com/): "kraken"

Feel free to test other exchanges and submit your PR to improve the bot.

Some exchanges require special configuration, which can be found on the [Exchange-specific Notes](exchanges.md) documentation page.

#### Sample exchange configuration

A exchange configuration for "binance" would look as follows:

```json
"exchange": {
    "name": "binance",
    "key": "your_exchange_key",
    "secret": "your_exchange_secret",
    "ccxt_config": {"enableRateLimit": true},
    "ccxt_async_config": {
        "enableRateLimit": true,
        "rateLimit": 200
    },
```

This configuration enables binance, as well as rate limiting to avoid bans from the exchange.
`"rateLimit": 200` defines a wait-event of 0.2s between each call. This can also be completely disabled by setting `"enableRateLimit"` to false.

!!! Note
    Optimal settings for rate limiting depend on the exchange and the size of the whitelist, so an ideal parameter will vary on many other settings.
    We try to provide sensible defaults per exchange where possible, if you encounter bans please make sure that `"enableRateLimit"` is enabled and increase the `"rateLimit"` parameter step by step.

#### Advanced Freqtrade Exchange configuration

Advanced options can be configured using the `_ft_has_params` setting, which will override Defaults and exchange-specific behaviours.

Available options are listed in the exchange-class as `_ft_has_default`.

For example, to test the order type `FOK` with Kraken, and modify candle limit to 200 (so you only get 200 candles per API call):

```json
"exchange": {
    "name": "kraken",
    "_ft_has_params": {
        "order_time_in_force": ["gtc", "fok"],
        "ohlcv_candle_limit": 200
        }
```

!!! Warning
    Please make sure to fully understand the impacts of these settings before modifying them.

### What values can be used for fiat_display_currency?

The `fiat_display_currency` configuration parameter sets the base currency to use for the
conversion from coin to fiat in the bot Telegram reports.

The valid values are:

```json
"AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB", "TRY", "TWD", "ZAR", "USD"
```

In addition to fiat currencies, a range of cryto currencies are supported.

The valid values are:

```json
"BTC", "ETH", "XRP", "LTC", "BCH", "USDT"
```

## Prices used for orders

Prices for regular orders can be controlled via the parameter structures `bid_strategy` for buying and `ask_strategy` for selling.
Prices are always retrieved right before an order is placed, either by querying the exchange tickers or by using the orderbook data.

!!! Note
    Orderbook data used by Freqtrade are the data retrieved from exchange by the ccxt's function `fetch_order_book()`, i.e. are usually data from the L2-aggregated orderbook, while the ticker data are the structures returned by the ccxt's `fetch_ticker()`/`fetch_tickers()` functions. Refer to the ccxt library [documentation](https://github.com/ccxt/ccxt/wiki/Manual#market-data) for more details.

### Buy price

#### Check depth of market

When check depth of market is enabled (`bid_strategy.check_depth_of_market.enabled=True`), the buy signals are filtered based on the orderbook depth (sum of all amounts) for each orderbook side.

Orderbook `bid` (buy) side depth is then divided by the orderbook `ask` (sell) side depth and the resulting delta is compared to the value of the `bid_strategy.check_depth_of_market.bids_to_ask_delta` parameter. The buy order is only executed if the orderbook delta is greater than or equal to the configured delta value.

!!! Note
    A delta value below 1 means that `ask` (sell) orderbook side depth is greater than the depth of the `bid` (buy) orderbook side, while a value greater than 1 means opposite (depth of the buy side is higher than the depth of the sell side).

#### Buy price side

The configuration setting `bid_strategy.price_side` defines the side of the spread the bot looks for when buying.

The following displays an orderbook.

``` explanation
...
103
102
101  # ask
-------------Current spread
99   # bid
98
97
...
```

If `bid_strategy.price_side` is set to `"bid"`, then the bot will use 99 as buying price.  
In line with that, if `bid_strategy.price_side` is set to `"ask"`, then the bot will use 101 as buying price.

Using `ask` price often guarantees quicker filled orders, but the bot can also end up paying more than what would have been necessary.
Taker fees instead of maker fees will most likely apply even when using limit buy orders.
Also, prices at the "ask" side of the spread are higher than prices at the "bid" side in the orderbook, so the order behaves similar to a market order (however with a maximum price).

#### Buy price with Orderbook enabled

When buying with the orderbook enabled (`bid_strategy.use_order_book=True`), Freqtrade fetches the `bid_strategy.order_book_top` entries from the orderbook and then uses the entry specified as `bid_strategy.order_book_top` on the configured side (`bid_strategy.price_side`) of the orderbook. 1 specifies the topmost entry in the orderbook, while 2 would use the 2nd entry in the orderbook, and so on.

#### Buy price without Orderbook enabled

The following section uses `side` as the configured `bid_strategy.price_side`.

When not using orderbook (`bid_strategy.use_order_book=False`), Freqtrade uses the best `side` price from the ticker if it's below the `last` traded price from the ticker. Otherwise (when the `side` price is above the `last` price), it calculates a rate between `side` and `last` price.

The `bid_strategy.ask_last_balance` configuration parameter controls this. A value of `0.0` will use `side` price, while `1.0` will use the `last` price and values between those interpolate between ask and last price.

### Sell price

#### Sell price side

The configuration setting `ask_strategy.price_side` defines the side of the spread the bot looks for when selling.

The following displays an orderbook:

``` explanation
...
103
102
101  # ask
-------------Current spread
99   # bid
98
97
...
```

If `ask_strategy.price_side` is set to `"ask"`, then the bot will use 101 as selling price.  
In line with that, if `ask_strategy.price_side` is set to `"bid"`, then the bot will use 99 as selling price.

#### Sell price with Orderbook enabled

When selling with the orderbook enabled (`ask_strategy.use_order_book=True`), Freqtrade fetches the `ask_strategy.order_book_max` entries in the orderbook. Then each of the orderbook steps between `ask_strategy.order_book_min` and `ask_strategy.order_book_max` on the configured orderbook side are validated for a profitable sell-possibility based on the strategy configuration (`minimal_roi` conditions) and the sell order is placed at the first profitable spot.

!!! Note
    Using `order_book_max` higher than `order_book_min` only makes sense when ask_strategy.price_side is set to `"ask"`.

The idea here is to place the sell order early, to be ahead in the queue.

A fixed slot (mirroring `bid_strategy.order_book_top`) can be defined by setting `ask_strategy.order_book_min` and `ask_strategy.order_book_max` to the same number.

!!! Warning "Order_book_max > 1 - increased risks for stoplosses!"
    Using `ask_strategy.order_book_max` higher than 1 will increase the risk the stoploss on exchange is cancelled too early, since an eventual [stoploss on exchange](#understand-order_types) will be cancelled as soon as the order is placed.
    Also, the sell order will remain on the exchange for `unfilledtimeout.sell` (or until it's filled) - which can lead to missed stoplosses (with or without using stoploss on exchange).

!!! Warning "Order_book_max > 1 in dry-run"
    Using `ask_strategy.order_book_max` higher than 1 will result in improper dry-run results (significantly better than real orders executed on exchange), since dry-run assumes orders to be filled almost instantly.
    It is therefore advised to not use this setting for dry-runs.

#### Sell price without Orderbook enabled

When not using orderbook (`ask_strategy.use_order_book=False`), the price at the `ask_strategy.price_side` side (defaults to `"ask"`) from the ticker will be used as the sell price.

## Pairlists and Pairlist Handlers

Pairlist Handlers define the list of pairs (pairlist) that the bot should trade. They are configured in the `pairlists` section of the configuration settings.

In your configuration, you can use Static Pairlist (defined by the [`StaticPairList`](#static-pair-list) Pairlist Handler) and Dynamic Pairlist (defined by the [`VolumePairList`](#volume-pair-list) Pairlist Handler).

Additionaly, [`PrecisionFilter`](#precisionfilter), [`PriceFilter`](#pricefilter), [`ShuffleFilter`](#shufflefilter) and [`SpreadFilter`](#spreadfilter) act as Pairlist Filters, removing certain pairs and/or moving their positions in the pairlist.

If multiple Pairlist Handlers are used, they are chained and a combination of all Pairlist Handlers forms the resulting pairlist the bot uses for trading and backtesting. Pairlist Handlers are executed in the sequence they are configured. You should always configure either `StaticPairList` or `VolumePairList` as the starting Pairlist Handler.

Inactive markets are always removed from the resulting pairlist. Explicitly blacklisted pairs (those in the `pair_blacklist` configuration setting) are also always removed from the resulting pairlist.

### Available Pairlist Handlers

* [`StaticPairList`](#static-pair-list) (default, if not configured differently)
* [`VolumePairList`](#volume-pair-list)
* [`PrecisionFilter`](#precisionfilter)
* [`PriceFilter`](#pricefilter)
* [`ShuffleFilter`](#shufflefilter)
* [`SpreadFilter`](#spreadfilter)

!!! Tip "Testing pairlists"
    Pairlist configurations can be quite tricky to get right. Best use the [`test-pairlist`](utils.md#test-pairlist) utility subcommand to test your configuration quickly.

#### Static Pair List

By default, the `StaticPairList` method is used, which uses a statically defined pair whitelist from the configuration. 

It uses configuration from `exchange.pair_whitelist` and `exchange.pair_blacklist`.

```json
"pairlists": [
    {"method": "StaticPairList"}
    ],
```

#### Volume Pair List

`VolumePairList` employs sorting/filtering of pairs by their trading volume. I selects `number_assets` top pairs with sorting based on the `sort_key` (which can only be `quoteVolume`).

When used in the chain of Pairlist Handlers in a non-leading position (after StaticPairList and other Pairlist Filters), `VolumePairList` considers outputs of previous Pairlist Handlers, adding its sorting/selection of the pairs by the trading volume.

When used on the leading position of the chain of Pairlist Handlers, it does not consider `pair_whitelist` configuration setting, but selects the top assets from all available markets (with matching stake-currency) on the exchange.

The `refresh_period` setting allows to define the period (in seconds), at which the pairlist will be refreshed. Defaults to 1800s (30 minutes).

`VolumePairList` is based on the ticker data from exchange, as reported by the ccxt library:

* The `quoteVolume` is the amount of quote (stake) currency traded (bought or sold) in last 24 hours.

```json
"pairlists": [{
        "method": "VolumePairList",
        "number_assets": 20,
        "sort_key": "quoteVolume",
        "refresh_period": 1800,
],
```

#### PrecisionFilter

Filters low-value coins which would not allow setting stoplosses.

#### PriceFilter

The `PriceFilter` allows filtering of pairs by price.

Currently, only `low_price_ratio` setting is implemented, where a raise of 1 price unit (pip) is below the `low_price_ratio` ratio.
This option is disabled by default, and will only apply if set to <> 0.

Calculation example:

Min price precision is 8 decimals. If price is 0.00000011 - one step would be 0.00000012 - which is almost 10% higher than the previous value.

These pairs are dangerous since it may be impossible to place the desired stoploss - and often result in high losses. Here is what the PriceFilters takes over.

#### ShuffleFilter

Shuffles (randomizes) pairs in the pairlist. It can be used for preventing the bot from trading some of the pairs more frequently then others when you want all pairs be treated with the same priority.

!!! Tip
    You may set the `seed` value for this Pairlist to obtain reproducible results, which can be useful for repeated backtesting sessions. If `seed` is not set, the pairs are shuffled in the non-repeatable random order.

#### SpreadFilter

Removes pairs that have a difference between asks and bids above the specified ratio, `max_spread_ratio` (defaults to `0.005`).

Example:

If `DOGE/BTC` maximum bid is 0.00000026 and minimum ask is 0.00000027, the ratio is calculated as: `1 - bid/ask ~= 0.037` which is `> 0.005` and this pair will be filtered out.

### Full example of Pairlist Handlers

The below example blacklists `BNB/BTC`, uses `VolumePairList` with `20` assets, sorting pairs by `quoteVolume` and applies both [`PrecisionFilter`](#precisionfilter) and [`PriceFilter`](#price-filter), filtering all assets where 1 priceunit is > 1%. Then the `SpreadFilter` is applied and pairs are finally shuffled with the random seed set to some predefined value.

```json
"exchange": {
    "pair_whitelist": [],
    "pair_blacklist": ["BNB/BTC"]
},
"pairlists": [
    {
        "method": "VolumePairList",
        "number_assets": 20,
        "sort_key": "quoteVolume",
    },
    {"method": "PrecisionFilter"},
    {"method": "PriceFilter", "low_price_ratio": 0.01},
    {"method": "SpreadFilter", "max_spread_ratio": 0.005},
    {"method": "ShuffleFilter", "seed": 42}
    ],
```

## Switch to Dry-run mode

We recommend starting the bot in the Dry-run mode to see how your bot will
behave and what is the performance of your strategy. In the Dry-run mode the
bot does not engage your money. It only runs a live simulation without
creating trades on the exchange.

1. Edit your `config.json` configuration file.
2. Switch `dry-run` to `true` and specify `db_url` for a persistence database.

```json
"dry_run": true,
"db_url": "sqlite:///tradesv3.dryrun.sqlite",
```

3. Remove your Exchange API key and secret (change them by empty values or fake credentials):

```json
"exchange": {
        "name": "bittrex",
        "key": "key",
        "secret": "secret",
        ...
}
```

Once you will be happy with your bot performance running in the Dry-run mode, you can switch it to production mode.

!!! Note
    A simulated wallet is available during dry-run mode, and will assume a starting capital of `dry_run_wallet` (defaults to 1000).

### Considerations for dry-run

* API-keys may or may not be provided. Only Read-Only operations (i.e. operations that do not alter account state) on the exchange are performed in the dry-run mode.
* Wallets (`/balance`) are simulated.
* Orders are simulated, and will not be posted to the exchange.
* In combination with `stoploss_on_exchange`, the stop_loss price is assumed to be filled.
* Open orders (not trades, which are stored in the database) are reset on bot restart.

## Switch to production mode

In production mode, the bot will engage your money. Be careful, since a wrong
strategy can lose all your money. Be aware of what you are doing when
you run it in production mode.

### Setup your exchange account

You will need to create API Keys (usually you get `key` and `secret`, some exchanges require an additional `password`) from the Exchange website and you'll need to insert this into the appropriate fields in the configuration or when asked by the `freqtrade new-config` command.
API Keys are usually only required for live trading (trading for real money, bot running in "production mode", executing real orders on the exchange) and are not required for the bot running in dry-run (trade simulation) mode. When you setup the bot in dry-run mode, you may fill these fields with empty values.

### To switch your bot in production mode

**Edit your `config.json`  file.**

**Switch dry-run to false and don't forget to adapt your database URL if set:**

```json
"dry_run": false,
```

**Insert your Exchange API key (change them by fake api keys):**

```json
"exchange": {
        "name": "bittrex",
        "key": "af8ddd35195e9dc500b9a6f799f6f5c93d89193b",
        "secret": "08a9dc6db3d7b53e1acebd9275677f4b0a04f1a5",
        ...
}
```

You should also make sure to read the [Exchanges](exchanges.md) section of the documentation to be aware of potential configuration details specific to your exchange.

### Using proxy with Freqtrade

To use a proxy with freqtrade, add the kwarg `"aiohttp_trust_env"=true` to the `"ccxt_async_kwargs"` dict in the exchange section of the configuration.

An example for this can be found in `config_full.json.example`

``` json
"ccxt_async_config": {
    "aiohttp_trust_env": true
}
```

Then, export your proxy settings using the variables `"HTTP_PROXY"` and `"HTTPS_PROXY"` set to the appropriate values

``` bash
export HTTP_PROXY="http://addr:port"
export HTTPS_PROXY="http://addr:port"
freqtrade
```

## Embedding Strategies

Freqtrade provides you with with an easy way to embed the strategy into your configuration file.
This is done by utilizing BASE64 encoding and providing this string at the strategy configuration field,
in your chosen config file.

### Encoding a string as BASE64

This is a quick example, how to generate the BASE64 string in python

```python
from base64 import urlsafe_b64encode

with open(file, 'r') as f:
    content = f.read()
content = urlsafe_b64encode(content.encode('utf-8'))
```

The variable 'content', will contain the strategy file in a BASE64 encoded form. Which can now be set in your configurations file as following

```json
"strategy": "NameOfStrategy:BASE64String"
```

Please ensure that 'NameOfStrategy' is identical to the strategy name!

## Next step

Now you have configured your config.json, the next step is to [start your bot](bot-usage.md).
