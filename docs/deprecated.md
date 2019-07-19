# Deprecated features

This page contains description of the command line arguments, configuration parameters
and the bot features that were declared as DEPRECATED by the bot development team
and are no longer supported. Please avoid their usage in your configuration.

### The **--dynamic-whitelist** command line option

This command line option was deprecated in 2018 and removed freqtrade 2019.6-dev (develop branch)
and in freqtrade 2019.7 (master branch).

Per default `--dynamic-whitelist` will retrieve the 20 currencies based
on BaseVolume. This value can be changed when you run the script.

**By Default**
Get the 20 currencies based on BaseVolume.

```bash
freqtrade --dynamic-whitelist
```

**Customize the number of currencies to retrieve**
Get the 30 currencies based on BaseVolume.

```bash
freqtrade --dynamic-whitelist 30
```

**Exception**
`--dynamic-whitelist` must be greater than 0. If you enter 0 or a
negative value (e.g -2), `--dynamic-whitelist` will use the default
value (20).


