# Configure the bot

This page explains how to configure your `config.json` file.

## Table of Contents

- [Bot commands](#bot-commands)
- [Backtesting commands](#backtesting-commands)
- [Hyperopt commands](#hyperopt-commands)

## Setup config.json

We recommend to copy and use the `config.json.example` as a template
for your bot configuration.

The table below will list all configuration parameters. 

|  Command | Default | Mandatory | Description |
|----------|---------|----------|-------------|
| `max_open_trades` | 3 | Yes | Number of trades open your bot will have.
| `stake_currency` | BTC | Yes | Crypto-currency used for trading.
| `stake_amount` | 0.05 | Yes | Amount of crypto-currency your bot will use for each trade. Per default, the bot will use (0.05 BTC x 3) = 0.15 BTC in total will be always engaged. Set it to 'unlimited' to allow the bot to use all avaliable balance.
| `ticker_interval` | [1m, 5m, 30m, 1h, 1d] | No | The ticker interval to use (1min, 5 min, 30 min, 1 hour or 1 day). Default is 5 minutes
| `fiat_display_currency` | USD | Yes | Fiat currency used to show your profits. More information below. 
| `dry_run` | true | Yes | Define if the bot must be in Dry-run or production mode. 
| `minimal_roi` | See below | No | Set the threshold in percent the bot will use to sell a trade. More information below. If set, this parameter will override `minimal_roi` from your strategy file. 
| `stoploss` | -0.10 | No | Value of the stoploss in percent used by the bot. More information below. If set, this parameter will override `stoploss` from your strategy file. 
| `trailing_stoploss` | false | No | Enables trailing stop-loss (based on `stoploss` in either configuration or strategy file).
| `trailing_stoploss_positve` | 0 | No | Changes stop-loss once profit has been reached.
| `unfilledtimeout.buy` | 10 | Yes | How long (in minutes) the bot will wait for an unfilled buy order to complete, after which the order will be cancelled.
| `unfilledtimeout.sell` | 10 | Yes | How long (in minutes) the bot will wait for an unfilled sell order to complete, after which the order will be cancelled.
| `bid_strategy.ask_last_balance` | 0.0 | Yes | Set the bidding price. More information below.
| `exchange.name` | bittrex | Yes | Name of the exchange class to use. [List below](#user-content-what-values-for-exchangename).
| `exchange.key` | key | No | API key to use for the exchange. Only required when you are in production mode.
| `exchange.secret` | secret | No | API secret to use for the exchange. Only required when you are in production mode.
| `exchange.pair_whitelist` | [] | No | List of currency to use by the bot. Can be overrided with `--dynamic-whitelist` param.
| `exchange.pair_blacklist` | [] | No | List of currency the bot must avoid. Useful when using `--dynamic-whitelist` param.
| `experimental.use_sell_signal` | false | No | Use your sell strategy in addition of the `minimal_roi`.
| `experimental.sell_profit_only` | false | No | waits until you have made a positive profit before taking a sell decision.
| `experimental.ignore_roi_if_buy_signal` | false | No | Does not sell if the buy-signal is still active. Takes preference over `minimal_roi` and `use_sell_signal`
| `telegram.enabled` | true | Yes | Enable or not the usage of Telegram.
| `telegram.token` | token | No | Your Telegram bot token. Only required if `telegram.enabled` is `true`.
| `telegram.chat_id` | chat_id | No | Your personal Telegram account id. Only required if `telegram.enabled` is `true`.
| `webhook.enabled` | false | No | Enable useage of Webhook notifications
| `webhook.url` | false | No | URL for the webhook. Only required if `webhook.enabled` is `true`. See the [webhook documentation](webhook-config.md) for more details.
| `webhook.webhookbuy` | false | No | Payload to send on buy. Only required if `webhook.enabled` is `true`. See the [webhook documentationV](webhook-config.md) for more details.
| `webhook.webhooksell` | false | No | Payload to send on sell. Only required if `webhook.enabled` is `true`. See the [webhook documentationV](webhook-config.md) for more details.
| `webhook.webhookstatus` | false | No | Payload to send on status calls. Only required if `webhook.enabled` is `true`. See the [webhook documentationV](webhook-config.md) for more details.
| `db_url` | `sqlite:///tradesv3.sqlite` | No | Declares database URL to use. NOTE: This defaults to `sqlite://` if `dry_run` is `True`.
| `initial_state` | running | No | Defines the initial application state. More information below.
| `strategy` | DefaultStrategy | No | Defines Strategy class to use.
| `strategy_path` | null | No | Adds an additional strategy lookup path (must be a folder).
| `internals.process_throttle_secs` | 5 | Yes | Set the process throttle. Value in second.

The definition of each config parameters is in [misc.py](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/misc.py#L205).

### Understand stake_amount

`stake_amount` is an amount of crypto-currency your bot will use for each trade.
The minimal value is 0.0005. If there is not enough crypto-currency in 
the account an exception is generated.
To allow the bot to trade all the avaliable `stake_currency` in your account set `stake_amount` = `unlimited`.
In this case a trade amount is calclulated as `currency_balanse / (max_open_trades - current_open_trades)`.

### Understand minimal_roi

`minimal_roi` is a JSON object where the key is a duration
in minutes and the value is the minimum ROI in percent.
See the example below:

```
"minimal_roi": {
    "40": 0.0,    # Sell after 40 minutes if the profit is not negative
    "30": 0.01,   # Sell after 30 minutes if there is at least 1% profit
    "20": 0.02,   # Sell after 20 minutes if there is at least 2% profit
    "0":  0.04    # Sell immediately if there is at least 4% profit
},
```

Most of the strategy files already include the optimal `minimal_roi`
value. This parameter is optional. If you use it, it will take over the
`minimal_roi` value from the strategy file.

### Understand stoploss

`stoploss` is loss in percentage that should trigger a sale.
For example value `-0.10` will cause immediate sell if the
profit dips below -10% for a given trade. This parameter is optional.

Most of the strategy files already include the optimal `stoploss`
value. This parameter is optional. If you use it, it will take over the
`stoploss` value from the strategy file.

### Understand trailing stoploss

Go to the [trailing stoploss Documentation](stoploss.md) for details on trailing stoploss.

### Understand initial_state

`initial_state` is an optional field that defines the initial application state.
Possible values are `running` or `stopped`. (default=`running`)
If the value is `stopped` the bot has to be started with `/start` first.

### Understand process_throttle_secs

`process_throttle_secs` is an optional field that defines in seconds how long the bot should wait
before asking the strategy if we should buy or a sell an asset. After each wait period, the strategy is asked again for
every opened trade wether or not we should sell, and for all the remaining pairs (either the dynamic list of pairs or
the static list of pairs) if we should buy.

### Understand ask_last_balance

`ask_last_balance` sets the bidding price. Value `0.0` will use `ask` price, `1.0` will
use the `last` price and values between those interpolate between ask and last
price. Using `ask` price will guarantee quick success in bid, but bot will also
end up paying more then would probably have been necessary.

### What values for exchange.name?

Freqtrade is based on [CCXT library](https://github.com/ccxt/ccxt) that supports 115 cryptocurrency
exchange markets and trading APIs. The complete up-to-date list can be found in the
[CCXT repo homepage](https://github.com/ccxt/ccxt/tree/master/python). However, the bot was tested
with only Bittrex and Binance.

The bot was tested with the following exchanges:

- [Bittrex](https://bittrex.com/): "bittrex"
- [Binance](https://www.binance.com/): "binance"

Feel free to test other exchanges and submit your PR to improve the bot.

### What values for fiat_display_currency?

`fiat_display_currency` set the base currency to use for the conversion from coin to fiat in Telegram.
The valid values are: "AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK", "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PKR", "PLN", "RUB", "SEK", "SGD", "THB", "TRY", "TWD", "ZAR", "USD".
In addition to central bank currencies, a range of cryto currencies are supported.
The valid values are: "BTC", "ETH", "XRP", "LTC", "BCH", "USDT".

## Switch to dry-run mode

We recommend starting the bot in dry-run mode to see how your bot will
behave and how is the performance of your strategy. In Dry-run mode the
bot does not engage your money. It only runs a live simulation without
creating trades.

### To switch your bot in Dry-run mode:

1. Edit your `config.json`  file
2. Switch dry-run to true and specify db_url for a persistent db

```json
"dry_run": true,
"db_url": "sqlite///tradesv3.dryrun.sqlite",
```

3. Remove your Exchange API key (change them by fake api credentials)

```json
"exchange": {
        "name": "bittrex",
        "key": "key",
        "secret": "secret",
        ...
}
```

Once you will be happy with your bot performance, you can switch it to 
production mode.

## Switch to production mode

In production mode, the bot will engage your money. Be careful a wrong 
strategy can lose all your money. Be aware of what you are doing when 
you run it in production mode.

### To switch your bot in production mode:

1. Edit your `config.json`  file

2. Switch dry-run to false and don't forget to adapt your database URL if set

```json
"dry_run": false,
```

3. Insert your Exchange API key (change them by fake api keys)

```json
"exchange": {
        "name": "bittrex",
        "key": "af8ddd35195e9dc500b9a6f799f6f5c93d89193b",
        "secret": "08a9dc6db3d7b53e1acebd9275677f4b0a04f1a5",
        ...
}

```
If you have not your Bittrex API key yet, [see our tutorial](https://github.com/freqtrade/freqtrade/blob/develop/docs/pre-requisite.md).

## Next step

Now you have configured your config.json, the next step is to [start your bot](https://github.com/freqtrade/freqtrade/blob/develop/docs/bot-usage.md).
