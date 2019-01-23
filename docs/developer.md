# Development Help

This page is intended for developers of FreqTrade, people who want to contribute to the FreqTrade codebase or documentation, or people who want to understand the source code of the application they're running.

All contributions, bug reports, bug fixes, documentation improvements, enhancements and ideas are welcome. We [track issues](https://github.com/freqtrade/freqtrade/issues) on [GitHub](https://github.com) and also have a dev channel in [slack](https://join.slack.com/t/highfrequencybot/shared_invite/enQtMjQ5NTM0OTYzMzY3LWMxYzE3M2MxNDdjMGM3ZTYwNzFjMGIwZGRjNTc3ZGU3MGE3NzdmZGMwNmU3NDM5ZTNmM2Y3NjRiNzk4NmM4OGE) where you can ask questions.

## Documentation

Documentation is available at [https://freqtrade.io](https://www.freqtrade.io/) and needs to be provided with every new feature PR.

Special fields for the documentation (like Note boxes, ...) can be found [here](https://squidfunk.github.io/mkdocs-material/extensions/admonition/).

## Developer setup

To configure a development environment, use best use the `setup.sh` script and answer "y" when asked "Do you want to install dependencies for dev [y/N]? ".
Alternatively (if your system is not supported by the setup.sh script), follow the manual installation process and run `pip3 install -r requirements-dev.txt`.

This will install all required tools for development, including `pytest`, `flake8`, `mypy`, and `coveralls`.

## Modules

### Dynamic Pairlist

You have a great idea for a new pair selection algorithm you would like to try out? Great.
Hopefully you also want to contribute this back upstream.

Whatever your motivations are - This should get you off the ground in trying to develop a new Pairlist provider.

First of all, have a look at the [VolumePairList](https://github.com/freqtrade/freqtrade/blob/develop/freqtrade/pairlist/VolumePairList.py) provider, and best copy this file with a name of your new Pairlist Provider.

This is a simple provider, which however serves as a good example on how to start developing.

Next, modify the classname of the provider (ideally align this with the Filename).

The base-class provides the an instance of the bot (`self._freqtrade`), as well as the configuration (`self._config`), and initiates both `_blacklist` and `_whitelist`.

```python
        self._freqtrade = freqtrade
        self._config = config
        self._whitelist = self._config['exchange']['pair_whitelist']
        self._blacklist = self._config['exchange'].get('pair_blacklist', [])
```


Now, let's step through the methods which require actions:

#### configuration

Configuration for PairListProvider is done in the bot configuration file in the element `"pairlist"`.
This Pairlist-object may contain a `"config"` dict with additional configurations for the configured pairlist.
By convention, `"number_assets"` is used to specify the maximum number of pairs to keep in the whitelist. Please follow this to ensure a consistent user experience.

Additional elements can be configured as needed. `VolumePairList` uses `"sort_key"` to specify the sorting value - however feel free to specify whatever is necessary for your great algorithm to be successfull and dynamic.

#### short_desc

Returns a description used for Telegram messages.
This should contain the name of the Provider, as well as a short description containing the number of assets. Please follow the format `"PairlistName - top/bottom X pairs"`.

#### refresh_pairlist

Override this method and run all calculations needed in this method.
This is called with each iteration of the bot - so consider implementing caching for compute/network heavy calculations.

Assign the resulting whiteslist to `self._whitelist` and `self._blacklist` respectively. These will then be used to run the bot in this iteration. Pairs with open trades will be added to the whitelist to have the sell-methods run correctly.

Please also run `self._validate_whitelist(pairs)` and to check and remove pairs with inactive markets. This function is available in the Parent class (`StaticPairList`) and should ideally not be overwritten.

##### sample

``` python
    def refresh_pairlist(self) -> None:
        # Generate dynamic whitelist
        pairs = self._gen_pair_whitelist(self._config['stake_currency'], self._sort_key)
        # Validate whitelist to only have active market pairs
        self._whitelist = self._validate_whitelist(pairs)[:self._number_pairs]
```

#### _gen_pair_whitelist

This is a simple method used by `VolumePairList` - however serves as a good example.
It implements caching (`@cached(TTLCache(maxsize=1, ttl=1800))`) as well as a configuration option to allow different (but similar) strategies to work with the same PairListProvider.

## Creating a release

This part of the documentation is aimed at maintainers, and shows how to create a release.

### create release branch

``` bash
# make sure you're in develop branch
git checkout develop

# create new branch
git checkout -b new_release
```

* edit `freqtrade/__init__.py` and add the desired version (for example `0.18.0`)
* Commit this part
* push that branch to the remote and create a PR

### create changelog from git commits

``` bash
# Needs to be done before merging / pulling that branch.
git log --oneline --no-decorate --no-merges master..develop
```

### Create github release / tag

* Use the version-number specified as tag. 
* Use "master" as reference (this step comes after the above PR is merged).
* use the above changelog as release comment (as codeblock)

### After-release

* update version in develop to next valid version and postfix that with `-dev` (`0.18.0 -> 0.18.1-dev`)
