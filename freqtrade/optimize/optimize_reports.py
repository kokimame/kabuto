from datetime import timedelta
from typing import Dict

from pandas import DataFrame
from tabulate import tabulate


def generate_text_table(data: Dict[str, Dict], stake_currency: str, max_open_trades: int,
                        results: DataFrame, skip_nan: bool = False) -> str:
    """
    Generates and returns a text table for the given backtest data and the results dataframe
    :param data: Dict of <pair: dataframe> containing data that was used during backtesting.
    :param stake_currency: stake-currency - used to correctly name headers
    :param max_open_trades: Maximum allowed open trades
    :param results: Dataframe containing the backtest results
    :param skip_nan: Print "left open" open trades
    :return: pretty printed table with tabulate as string
    """

    floatfmt = ('s', 'd', '.2f', '.2f', '.8f', '.2f', 'd', '.1f', '.1f')
    tabular_data = []
    headers = [
        'Pair',
        'Buys',
        'Avg Profit %',
        'Cum Profit %',
        f'Tot Profit {stake_currency}',
        'Tot Profit %',
        'Avg Duration',
        'Wins',
        'Draws',
        'Losses'
    ]
    for pair in data:
        result = results[results.pair == pair]
        if skip_nan and result.profit_abs.isnull().all():
            continue

        tabular_data.append([
            pair,
            len(result.index),
            result.profit_percent.mean() * 100.0,
            result.profit_percent.sum() * 100.0,
            result.profit_abs.sum(),
            result.profit_percent.sum() * 100.0 / max_open_trades,
            str(timedelta(
                minutes=round(result.trade_duration.mean()))) if not result.empty else '0:00',
            len(result[result.profit_abs > 0]),
            len(result[result.profit_abs == 0]),
            len(result[result.profit_abs < 0])
        ])

    # Append Total
    tabular_data.append([
        'TOTAL',
        len(results.index),
        results.profit_percent.mean() * 100.0,
        results.profit_percent.sum() * 100.0,
        results.profit_abs.sum(),
        results.profit_percent.sum() * 100.0 / max_open_trades,
        str(timedelta(
            minutes=round(results.trade_duration.mean()))) if not results.empty else '0:00',
        len(results[results.profit_abs > 0]),
        len(results[results.profit_abs == 0]),
        len(results[results.profit_abs < 0])
    ])
    # Ignore type as floatfmt does allow tuples but mypy does not know that
    return tabulate(tabular_data, headers=headers,
                    floatfmt=floatfmt, tablefmt="orgtbl", stralign="right")  # type: ignore


def generate_text_table_sell_reason(
    data: Dict[str, Dict], stake_currency: str, max_open_trades: int, results: DataFrame
) -> str:
    """
    Generate small table outlining Backtest results
    :param data: Dict of <pair: dataframe> containing data that was used during backtesting.
    :param results: Dataframe containing the backtest results
    :return: pretty printed table with tabulate as string
    """
    tabular_data = []
    headers = [
        "Sell Reason",
        "Sells",
        "Wins",
        "Draws",
        "Losses",
        "Avg Profit %",
        "Cum Profit %",
        f"Tot Profit {stake_currency}",
        "Tot Profit %",
    ]
    for reason, count in results['sell_reason'].value_counts().iteritems():
        result = results.loc[results['sell_reason'] == reason]
        wins = len(result[result['profit_abs'] > 0])
        draws = len(result[result['profit_abs'] == 0])
        loss = len(result[result['profit_abs'] < 0])
        profit_mean = round(result['profit_percent'].mean() * 100.0, 2)
        profit_sum = round(result["profit_percent"].sum() * 100.0, 2)
        profit_tot = result['profit_abs'].sum()
        profit_percent_tot = round(result['profit_percent'].sum() * 100.0 / max_open_trades, 2)
        tabular_data.append(
            [
                reason.value,
                count,
                wins,
                draws,
                loss,
                profit_mean,
                profit_sum,
                profit_tot,
                profit_percent_tot,
            ]
        )
    return tabulate(tabular_data, headers=headers, tablefmt="orgtbl", stralign="right")


def generate_text_table_strategy(stake_currency: str, max_open_trades: str,
                                 all_results: Dict) -> str:
    """
    Generate summary table per strategy
    :param stake_currency: stake-currency - used to correctly name headers
    :param max_open_trades: Maximum allowed open trades used for backtest
    :param all_results: Dict of <Strategyname: BacktestResult> containing results for all strategies
    :return: pretty printed table with tabulate as string
    """

    floatfmt = ('s', 'd', '.2f', '.2f', '.8f', '.2f', 'd', '.1f', '.1f')
    tabular_data = []
    headers = ['Strategy', 'Buys', 'Avg Profit %', 'Cum Profit %',
               f'Tot Profit {stake_currency}', 'Tot Profit %', 'Avg Duration',
               'Wins', 'Draws', 'Losses']
    for strategy, results in all_results.items():
        tabular_data.append([
            strategy,
            len(results.index),
            results.profit_percent.mean() * 100.0,
            results.profit_percent.sum() * 100.0,
            results.profit_abs.sum(),
            results.profit_percent.sum() * 100.0 / max_open_trades,
            str(timedelta(
                minutes=round(results.trade_duration.mean()))) if not results.empty else '0:00',
            len(results[results.profit_abs > 0]),
            len(results[results.profit_abs == 0]),
            len(results[results.profit_abs < 0])
        ])
    # Ignore type as floatfmt does allow tuples but mypy does not know that
    return tabulate(tabular_data, headers=headers,
                    floatfmt=floatfmt, tablefmt="orgtbl", stralign="right")  # type: ignore


def generate_edge_table(results: dict) -> str:

    floatfmt = ('s', '.10g', '.2f', '.2f', '.2f', '.2f', 'd', '.d')
    tabular_data = []
    headers = ['Pair', 'Stoploss', 'Win Rate', 'Risk Reward Ratio',
               'Required Risk Reward', 'Expectancy', 'Total Number of Trades',
               'Average Duration (min)']

    for result in results.items():
        if result[1].nb_trades > 0:
            tabular_data.append([
                result[0],
                result[1].stoploss,
                result[1].winrate,
                result[1].risk_reward_ratio,
                result[1].required_risk_reward,
                result[1].expectancy,
                result[1].nb_trades,
                round(result[1].avg_trade_duration)
            ])

    # Ignore type as floatfmt does allow tuples but mypy does not know that
    return tabulate(tabular_data, headers=headers,
                    floatfmt=floatfmt, tablefmt="orgtbl", stralign="right")  # type: ignore
