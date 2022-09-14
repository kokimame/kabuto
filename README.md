# ![freqtrade](https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/assets/freqtrade_poweredby.svg)

[![Freqtrade CI](https://github.com/freqtrade/freqtrade/workflows/Freqtrade%20CI/badge.svg)](https://github.com/freqtrade/freqtrade/actions/)
[![Coverage Status](https://coveralls.io/repos/github/freqtrade/freqtrade/badge.svg?branch=develop&service=github)](https://coveralls.io/github/freqtrade/freqtrade?branch=develop)
[![Documentation](https://readthedocs.org/projects/freqtrade/badge/)](https://www.freqtrade.io)
[![Maintainability](https://api.codeclimate.com/v1/badges/5737e6d668200b7518ff/maintainability)](https://codeclimate.com/github/freqtrade/freqtrade/maintainability)

**Kabuto** は無料かつオープンソースな日本株取引Botです。仮想通貨取引Botの **Freqtrade** と日本株取引の発注基盤である **kabu STATION API** を組み合わせたサービスです。

![freqtrade](https://raw.githubusercontent.com/freqtrade/freqtrade/develop/docs/assets/freqtrade-screenshot.png)

## 注意

本ソフトウェア（以下Kabuto）は教育的利用に限ります。株式市場を取り巻く需給により株価が変動し投資元本を割り込むことがあります。
余剰資産を超えた取引はお控えください。ご利用に関する全ての責任は利用者にあります。
Kabutoの作成者や関係者は貴方の取引結果に関する一切の責任を負いません（詳細はGPL3ライセンスを確認）。

取引Botを使用する際はdry-runから実行し、Botの特性や期待できる損益を正しく理解しましょう。
Kabutoの利用の前にコーディングやPythonの知識を習得することを強く推奨します。Kabutoのソースコードを読み、Botの仕組みを理解することを勧めます。

また、日本株取引にあたり、auカブコム証券での口座開設（Fintechプラン以上）が必要です。

## Botを利用可能な取引
- [x] auカブコム証券 現物取引
- [x] auカブコム証券 デイトレ信用
- [ ] auカブコム証券 一般/制度信用
- [x] Freqtradeで利用可能な全ての仮想通貨取引所（詳細はFreqtrade公式ページを確認）


## ドキュメント

日本株取引の場合、Kabutoは貴方のauカブコム証券の口座情報を利用します。口座情報の取扱いについては[こちら](https://github.com/kokimame/kabuto/blob/dev/freqtrade/kabuto/credentials.py)をご覧ください。
その他の日本株取引に関するドキュメントは現在制作中になります。

Kabutoの大部分を構成するFreqtradeのドキュメントは[こちら](https://www.freqtrade.io)になります。

## Kabutoの特徴

- **Python 3.8+を利用**: Bot開発と実行はWindows・Mac・LinuxのOS上で可能です
- **SNSから取引Botを管理・操作**: Manage the bot with Telegram.
- **Dry-run**: 実際のリアルタイムの相場情報と、資産を使わない仮想取引による取引戦略の性能確認
- **バックテスト**: 過去の株価データを用いた取引戦略の性能確認
- **機械学習を用いた取引戦略の最適化**: Use machine learning to optimize your buy/sell strategy parameters with real exchange data.
- **パーシスタンス**: SQLiteを用いたパーシスタンス（Botやマシンを停止しても問題なし）
- **Edge position sizing** Calculate your win rate, risk reward ratio, the best stoploss and adjust your position size before taking a position for each specific market. [Learn more](https://www.freqtrade.io/en/stable/edge/).
- **ホワイトリスト銘柄**: Select which crypto-currency you want to trade or use dynamic whitelists.
- **ブラックリスト銘柄**: Select which crypto-currency you want to avoid.
- **ビルトインWebインターフェース**: Freqtradeに付随する可視化Webツール FreqUI に対応
- **損益の可視化**: Display your profit/loss in fiat currency.
- **パフォーマンスレポート**: Provide a performance status of your current trades.

## Quick start

Please refer to the [Docker Quickstart documentation](https://www.freqtrade.io/en/stable/docker_quickstart/) on how to get started quickly.

For further (native) installation methods, please refer to the [Installation documentation page](https://www.freqtrade.io/en/stable/installation/).

## Basic Usage

### Bot commands

```
usage: freqtrade [-h] [-V]
                 {trade,create-userdir,new-config,new-strategy,download-data,convert-data,convert-trade-data,list-data,backtesting,edge,hyperopt,hyperopt-list,hyperopt-show,list-exchanges,list-hyperopts,list-markets,list-pairs,list-strategies,list-timeframes,show-trades,test-pairlist,install-ui,plot-dataframe,plot-profit,webserver}
                 ...

Free, open source crypto trading bot

positional arguments:
  {trade,create-userdir,new-config,new-strategy,download-data,convert-data,convert-trade-data,list-data,backtesting,edge,hyperopt,hyperopt-list,hyperopt-show,list-exchanges,list-hyperopts,list-markets,list-pairs,list-strategies,list-timeframes,show-trades,test-pairlist,install-ui,plot-dataframe,plot-profit,webserver}
    trade               Trade module.
    create-userdir      Create user-data directory.
    new-config          Create new config
    new-strategy        Create new strategy
    download-data       Download backtesting data.
    convert-data        Convert candle (OHLCV) data from one format to
                        another.
    convert-trade-data  Convert trade data from one format to another.
    list-data           List downloaded data.
    backtesting         Backtesting module.
    edge                Edge module.
    hyperopt            Hyperopt module.
    hyperopt-list       List Hyperopt results
    hyperopt-show       Show details of Hyperopt results
    list-exchanges      Print available exchanges.
    list-hyperopts      Print available hyperopt classes.
    list-markets        Print markets on exchange.
    list-pairs          Print pairs on exchange.
    list-strategies     Print available strategies.
    list-timeframes     Print available timeframes for the exchange.
    show-trades         Show trades.
    test-pairlist       Test your pairlist configuration.
    install-ui          Install FreqUI
    plot-dataframe      Plot candles with indicators.
    plot-profit         Generate plot showing profits.
    webserver           Webserver module.

optional arguments:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit

```

### Telegram RPC コマンド

Telegramの利用は任意ですが、SNSを用いたBotの管理や操作は大変便利です。
詳細はFreqtradeの[ドキュメント](https://www.freqtrade.io/en/latest/telegram-usage/)をご確認ください。

- `/start`: Botの実行を開始
- `/stop`: Botの実行を停止
- `/stopbuy`: 新規発注を停止
- `/status <trade_id>|[table]`: 全て または 特定 の取引中の取引の詳細を表示
- `/profit [<n>]`: Lists cumulative profit from all finished trades, over the last n days.
- `/forceexit <trade_id>|all`: Instantly exits the given trade (Ignoring `minimum_roi`).
- `/fx <trade_id>|all`: Alias to `/forceexit`
- `/performance`: Show performance of each finished trade grouped by pair
- `/balance`: Show account balance per currency.
- `/daily <n>`: Shows profit or loss per day, over the last n days.
- `/help`: Show help message.
- `/version`: Show version.

## Development branches

The project is currently setup in two main branches:

- `develop` - This branch has often new features, but might also contain breaking changes. We try hard to keep this branch as stable as possible.
- `stable` - This branch contains the latest stable release. This branch is generally well tested.
- `feat/*` - These are feature branches, which are being worked on heavily. Please don't use these unless you want to test a specific feature.

## Support

### Help / Discord

For any questions not covered by the documentation or for further information about the bot, or to simply engage with like-minded individuals, we encourage you to join the Freqtrade [discord server](https://discord.gg/p7nuUNVfP7).

### [Bugs / Issues](https://github.com/freqtrade/freqtrade/issues?q=is%3Aissue)

If you discover a bug in the bot, please
[search the issue tracker](https://github.com/freqtrade/freqtrade/issues?q=is%3Aissue)
first. If it hasn't been reported, please
[create a new issue](https://github.com/freqtrade/freqtrade/issues/new/choose) and
ensure you follow the template guide so that the team can assist you as
quickly as possible.

### [Feature Requests](https://github.com/freqtrade/freqtrade/labels/enhancement)

Have you a great idea to improve the bot you want to share? Please,
first search if this feature was not [already discussed](https://github.com/freqtrade/freqtrade/labels/enhancement).
If it hasn't been requested, please
[create a new request](https://github.com/freqtrade/freqtrade/issues/new/choose)
and ensure you follow the template guide so that it does not get lost
in the bug reports.

### [Pull Requests](https://github.com/freqtrade/freqtrade/pulls)

Feel like the bot is missing a feature? We welcome your pull requests!

Please read the
[Contributing document](https://github.com/freqtrade/freqtrade/blob/develop/CONTRIBUTING.md)
to understand the requirements before sending your pull-requests.

Coding is not a necessity to contribute - maybe start with improving the documentation?
Issues labeled [good first issue](https://github.com/freqtrade/freqtrade/labels/good%20first%20issue) can be good first contributions, and will help get you familiar with the codebase.

**Note** before starting any major new feature work, *please open an issue describing what you are planning to do* or talk to us on [discord](https://discord.gg/p7nuUNVfP7) (please use the #dev channel for this). This will ensure that interested parties can give valuable feedback on the feature, and let others know that you are working on it.

**Important:** Always create your PR against the `develop` branch, not `stable`.

## Requirements

### Up-to-date clock

The clock must be accurate, synchronized to a NTP server very frequently to avoid problems with communication to the exchanges.

### Min hardware required

To run this bot we recommend you a cloud instance with a minimum of:

- Minimal (advised) system requirements: 2GB RAM, 1GB disk space, 2vCPU

### Software requirements

- [Python >= 3.8](http://docs.python-guide.org/en/latest/starting/installation/)
- [pip](https://pip.pypa.io/en/stable/installing/)
- [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git)
- [TA-Lib](https://mrjbq7.github.io/ta-lib/install.html)
- [virtualenv](https://virtualenv.pypa.io/en/stable/installation.html) (Recommended)
- [Docker](https://www.docker.com/products/docker) (Recommended)
