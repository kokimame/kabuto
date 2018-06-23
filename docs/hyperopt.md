# Hyperopt
This page explains how to tune your strategy by finding the optimal
parameters with Hyperopt.

## Table of Contents
- [Prepare your Hyperopt](#prepare-hyperopt)
    - [1. Configure your Guards and Triggers](#1-configure-your-guards-and-triggers)
    - [2. Update the hyperopt config file](#2-update-the-hyperopt-config-file)
- [Advanced Hyperopt notions](#advanced-notions)
    - [Understand the Guards and Triggers](#understand-the-guards-and-triggers)
- [Execute Hyperopt](#execute-hyperopt)
- [Understand the hyperopts result](#understand-the-backtesting-result)

## Prepare Hyperopt
Before we start digging in Hyperopt, we recommend you to take a look at 
your strategy file located into [user_data/strategies/](https://github.com/freqtrade/freqtrade/blob/develop/user_data/strategies/test_strategy.py)
 
### 1. Configure your Guards and Triggers
There are two places you need to change in your strategy file to add a 
new buy strategy for testing:
- Inside [populate_buy_trend()](https://github.com/freqtrade/freqtrade/blob/develop/user_data/strategies/test_strategy.py#L278-L294).
- Inside [hyperopt_space()](https://github.com/freqtrade/freqtrade/blob/develop/user_data/strategies/test_strategy.py#L244-L297) known as `SPACE`.

There you have two different type of indicators: 1. `guards` and 2. 
`triggers`.
1. Guards are conditions like "never buy if ADX < 10", or never buy if 
current price is over EMA10.
2. Triggers are ones that actually trigger buy in specific moment, like 
"buy when EMA5 crosses over EMA10" or buy when close price touches lower 
bollinger band.

HyperOpt will, for each eval round, pick just ONE trigger, and possibly 
multiple guards. So that the constructed strategy will be something like 
"*buy exactly when close price touches lower bollinger band, BUT only if 
ADX > 10*".


If you have updated the buy strategy, means change the content of
`populate_buy_trend()` method you have to update the `guards` and 
`triggers` hyperopts must used.

As for an example if your `populate_buy_trend()` method is:
```python
def populate_buy_trend(dataframe: DataFrame) -> DataFrame:
    dataframe.loc[
        (dataframe['rsi'] < 35) &
        (dataframe['adx'] > 65),
        'buy'] = 1

    return dataframe
```

Your hyperopt file must contain `guards` to find the right value for 
`(dataframe['adx'] > 65)` & and `(dataframe['plus_di'] > 0.5)`. That 
means you will need to enable/disable triggers.
 
In our case the `SPACE` and `populate_buy_trend` in your strategy file 
will look like:
```python
space = {
    'rsi': hp.choice('rsi', [
        {'enabled': False},
        {'enabled': True, 'value': hp.quniform('rsi-value', 20, 40, 1)}
    ]),
    'adx': hp.choice('adx', [
        {'enabled': False},
        {'enabled': True, 'value': hp.quniform('adx-value', 15, 50, 1)}
    ]),
    'trigger': hp.choice('trigger', [
        {'type': 'lower_bb'},
        {'type': 'faststoch10'},
        {'type': 'ao_cross_zero'},
        {'type': 'ema5_cross_ema10'},
        {'type': 'macd_cross_signal'},
        {'type': 'sar_reversal'},
        {'type': 'stochf_cross'},
        {'type': 'ht_sine'},
    ]),
}

... 

def populate_buy_trend(self, dataframe: DataFrame) -> DataFrame:
        conditions = []
        # GUARDS AND TRENDS
        if params['adx']['enabled']:
            conditions.append(dataframe['adx'] > params['adx']['value'])
        if params['rsi']['enabled']:
            conditions.append(dataframe['rsi'] < params['rsi']['value'])

        # TRIGGERS
        triggers = {
            'lower_bb': dataframe['tema'] <= dataframe['blower'],
            'faststoch10': (crossed_above(dataframe['fastd'], 10.0)),
            'ao_cross_zero': (crossed_above(dataframe['ao'], 0.0)),
            'ema5_cross_ema10': (crossed_above(dataframe['ema5'], dataframe['ema10'])),
            'macd_cross_signal': (crossed_above(dataframe['macd'], dataframe['macdsignal'])),
            'sar_reversal': (crossed_above(dataframe['close'], dataframe['sar'])),
            'stochf_cross': (crossed_above(dataframe['fastk'], dataframe['fastd'])),
            'ht_sine': (crossed_above(dataframe['htleadsine'], dataframe['htsine'])),
        }
        ...
```


### 2. Update the hyperopt config file
Hyperopt is using a dedicated config file. Currently hyperopt 
cannot use your config file. It is also made on purpose to allow you
testing your strategy with different configurations.

The Hyperopt configuration is located in 
[user_data/hyperopt_conf.py](https://github.com/freqtrade/freqtrade/blob/develop/user_data/hyperopt_conf.py).


## Advanced notions
### Understand the Guards and Triggers
When you need to add the new guards and triggers to be hyperopt 
parameters, you do this by adding them into the [hyperopt_space()](https://github.com/freqtrade/freqtrade/blob/develop/user_data/strategies/test_strategy.py#L244-L297).

If it's a trigger, you add one line to the 'trigger' choice group and that's it.

If it's a guard, you will add a line like this:
```
'rsi': hp.choice('rsi', [
    {'enabled': False},
    {'enabled': True, 'value': hp.quniform('rsi-value', 20, 40, 1)}
]),
```
This says, "*one of the guards is RSI, it can have two values, enabled or 
disabled. If it is enabled, try different values for it between 20 and 40*".

So, the part of the strategy builder using the above setting looks like 
this:

```
if params['rsi']['enabled']:
    conditions.append(dataframe['rsi'] < params['rsi']['value'])
```

It checks if Hyperopt wants the RSI guard to be enabled for this 
round `params['rsi']['enabled']` and if it is, then it will add a 
condition that says RSI must be smaller than the value hyperopt picked 
for this evaluation, which is given in the `params['rsi']['value']`.

That's it. Now you can add new parts of strategies to Hyperopt and it 
will try all the combinations with all different values in the search 
for best working algo.


### Add a new Indicators
If you want to test an indicator that isn't used by the bot currently, 
you need to add it to the `populate_indicators()` method in `hyperopt.py`.

## Execute Hyperopt
Once you have updated your hyperopt configuration you can run it. 
Because hyperopt tries a lot of combination to find the best parameters
it will take time you will have the result (more than 30 mins).

We strongly recommend to use `screen` to prevent any connection loss.
```bash
python3 ./freqtrade/main.py -c config.json hyperopt -e 5000
```

The `-e` flag will set how many evaluations hyperopt will do. We recommend
running at least several thousand evaluations.

### Execute hyperopt with different ticker-data source
If you would like to hyperopt parameters using an alternate ticker data that
you have on-disk, use the `--datadir PATH` option. Default hyperopt will
use data from directory `user_data/data`.

### Running hyperopt with smaller testset
Use the `--timeperiod` argument to change how much of the testset
you want to use. The last N ticks/timeframes will be used.
Example:

```bash
python3 ./freqtrade/main.py hyperopt --timeperiod -200
```

### Running hyperopt with smaller search space
Use the `--spaces` argument to limit the search space used by hyperopt.
Letting Hyperopt optimize everything is a huuuuge search space. Often it 
might make more sense to start by just searching for initial buy algorithm. 
Or maybe you just want to optimize your stoploss or roi table for that awesome 
new buy strategy you have.

Legal values are:

- `all`: optimize everything
- `buy`: just search for a new buy strategy
- `roi`: just optimize the minimal profit table for your strategy
- `stoploss`: search for the best stoploss value
- space-separated list of any of the above values for example `--spaces roi stoploss`

## Understand the hyperopts result 
Once Hyperopt is completed you can use the result to adding new buy 
signal. Given following result from hyperopt:
```
Best parameters:
{
    "adx": {
        "enabled": true,
        "value": 15.0
    },
    "fastd": {
        "enabled": true,
        "value": 40.0
    },
    "green_candle": {
        "enabled": true
    },
    "mfi": {
        "enabled": false
    },
    "over_sar": {
        "enabled": false
    },
    "rsi": {
        "enabled": true,
        "value": 37.0
    },
    "trigger": {
        "type": "lower_bb"
    },
    "uptrend_long_ema": {
        "enabled": true
    },
    "uptrend_short_ema": {
        "enabled": false
    },
    "uptrend_sma": {
        "enabled": false
    }
}

Best Result:
  2197 trades. Avg profit  1.84%. Total profit  0.79367541 BTC. Avg duration 241.0 mins.
```

You should understand this result like:
- You should **consider** the guard "adx" (`"adx"` is `"enabled": true`) 
and the best value is `15.0` (`"value": 15.0,`)
- You should **consider** the guard "fastd" (`"fastd"` is `"enabled": 
true`) and the best value is `40.0` (`"value": 40.0,`)
- You should **consider** to enable the guard "green_candle" 
(`"green_candle"` is `"enabled": true`) but this guards as no 
customizable value.
- You should **ignore** the guard "mfi" (`"mfi"` is `"enabled": false`)
- and so on...

You have to look inside your strategy file into `buy_strategy_generator()` 
method, what those values match to.   
  
So for example you had `adx:` with the `value: 15.0` so we would look 
at `adx`-block, that translates to the following code block:
```
(dataframe['adx'] > 15.0)
```
  
Translating your whole hyperopt result to as the new buy-signal 
would be the following:
```
def populate_buy_trend(self, dataframe: DataFrame) -> DataFrame:
    dataframe.loc[
        (
            (dataframe['adx'] > 15.0) & # adx-value
            (dataframe['fastd'] < 40.0) & # fastd-value
            (dataframe['close'] > dataframe['open']) & # green_candle
            (dataframe['rsi'] < 37.0) & # rsi-value
            (dataframe['ema50'] > dataframe['ema100']) # uptrend_long_ema
        ),
        'buy'] = 1
    return dataframe
```

## Next step
Now you have a perfect bot and want to control it from Telegram. Your
next step is to learn the [Telegram usage](https://github.com/freqtrade/freqtrade/blob/develop/docs/telegram-usage.md).
