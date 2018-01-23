import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from hyperopt import hp
from functools import reduce
from typing import Dict, List


class_name = 'DefaultStrategy'


class DefaultStrategy(IStrategy):
    """
    Default Strategy provided by freqtrade bot.
    You can override it with your own strategy
    """

    # Minimal ROI designed for the strategy
    minimal_roi = {
        "40":  0.0,
        "30":  0.01,
        "20":  0.02,
        "0":  0.04
    }

    # Optimal stoploss designed for the strategy
    stoploss = -0.10

    def populate_indicators(self, dataframe: DataFrame) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame

        Performance Note: For the best performance be frugal on the number of indicators
        you are using. Let uncomment only the indicator you are using in your strategies
        or your hyperopt configuration, otherwise you will waste your memory and CPU usage.
        """

        # Momentum Indicator
        # ------------------------------------

        # ADX
        dataframe['adx'] = ta.ADX(dataframe)

        # Awesome oscillator
        dataframe['ao'] = qtpylib.awesome_oscillator(dataframe)
        """
        # Commodity Channel Index: values Oversold:<-100, Overbought:>100
        dataframe['cci'] = ta.CCI(dataframe)
        """
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']

        # MFI
        dataframe['mfi'] = ta.MFI(dataframe)

        # Minus Directional Indicator / Movement
        dataframe['minus_dm'] = ta.MINUS_DM(dataframe)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe)

        # Plus Directional Indicator / Movement
        dataframe['plus_dm'] = ta.PLUS_DM(dataframe)
        dataframe['plus_di'] = ta.PLUS_DI(dataframe)
        dataframe['minus_di'] = ta.MINUS_DI(dataframe)

        """
        # ROC
        dataframe['roc'] = ta.ROC(dataframe)
        """
        # RSI
        dataframe['rsi'] = ta.RSI(dataframe)
        """
        # Inverse Fisher transform on RSI, values [-1.0, 1.0] (https://goo.gl/2JGGoy)
        rsi = 0.1 * (dataframe['rsi'] - 50)
        dataframe['fisher_rsi'] = (numpy.exp(2 * rsi) - 1) / (numpy.exp(2 * rsi) + 1)
        # Inverse Fisher transform on RSI normalized, value [0.0, 100.0] (https://goo.gl/2JGGoy)
        dataframe['fisher_rsi_norma'] = 50 * (dataframe['fisher_rsi'] + 1)
        # Stoch
        stoch = ta.STOCH(dataframe)
        dataframe['slowd'] = stoch['slowd']
        dataframe['slowk'] = stoch['slowk']
        """
        # Stoch fast
        stoch_fast = ta.STOCHF(dataframe)
        dataframe['fastd'] = stoch_fast['fastd']
        dataframe['fastk'] = stoch_fast['fastk']
        """
        # Stoch RSI
        stoch_rsi = ta.STOCHRSI(dataframe)
        dataframe['fastd_rsi'] = stoch_rsi['fastd']
        dataframe['fastk_rsi'] = stoch_rsi['fastk']
        """

        # Overlap Studies
        # ------------------------------------

        # Previous Bollinger bands
        # Because ta.BBANDS implementation is broken with small numbers, it actually
        # returns middle band for all the three bands. Switch to qtpylib.bollinger_bands
        # and use middle band instead.
        dataframe['blower'] = ta.BBANDS(dataframe, nbdevup=2, nbdevdn=2)['lowerband']

        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_middleband'] = bollinger['mid']
        dataframe['bb_upperband'] = bollinger['upper']

        # EMA - Exponential Moving Average
        dataframe['ema3'] = ta.EMA(dataframe, timeperiod=3)
        dataframe['ema5'] = ta.EMA(dataframe, timeperiod=5)
        dataframe['ema10'] = ta.EMA(dataframe, timeperiod=10)
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema100'] = ta.EMA(dataframe, timeperiod=100)

        # SAR Parabol
        dataframe['sar'] = ta.SAR(dataframe)

        # SMA - Simple Moving Average
        dataframe['sma'] = ta.SMA(dataframe, timeperiod=40)

        # TEMA - Triple Exponential Moving Average
        dataframe['tema'] = ta.TEMA(dataframe, timeperiod=9)

        # Cycle Indicator
        # ------------------------------------
        # Hilbert Transform Indicator - SineWave
        hilbert = ta.HT_SINE(dataframe)
        dataframe['htsine'] = hilbert['sine']
        dataframe['htleadsine'] = hilbert['leadsine']

        # Pattern Recognition - Bullish candlestick patterns
        # ------------------------------------
        """
        # Hammer: values [0, 100]
        dataframe['CDLHAMMER'] = ta.CDLHAMMER(dataframe)
        # Inverted Hammer: values [0, 100]
        dataframe['CDLINVERTEDHAMMER'] = ta.CDLINVERTEDHAMMER(dataframe)
        # Dragonfly Doji: values [0, 100]
        dataframe['CDLDRAGONFLYDOJI'] = ta.CDLDRAGONFLYDOJI(dataframe)
        # Piercing Line: values [0, 100]
        dataframe['CDLPIERCING'] = ta.CDLPIERCING(dataframe) # values [0, 100]
        # Morningstar: values [0, 100]
        dataframe['CDLMORNINGSTAR'] = ta.CDLMORNINGSTAR(dataframe) # values [0, 100]
        # Three White Soldiers: values [0, 100]
        dataframe['CDL3WHITESOLDIERS'] = ta.CDL3WHITESOLDIERS(dataframe) # values [0, 100]
        """

        # Pattern Recognition - Bearish candlestick patterns
        # ------------------------------------
        """
        # Hanging Man: values [0, 100]
        dataframe['CDLHANGINGMAN'] = ta.CDLHANGINGMAN(dataframe)
        # Shooting Star: values [0, 100]
        dataframe['CDLSHOOTINGSTAR'] = ta.CDLSHOOTINGSTAR(dataframe)
        # Gravestone Doji: values [0, 100]
        dataframe['CDLGRAVESTONEDOJI'] = ta.CDLGRAVESTONEDOJI(dataframe)
        # Dark Cloud Cover: values [0, 100]
        dataframe['CDLDARKCLOUDCOVER'] = ta.CDLDARKCLOUDCOVER(dataframe)
        # Evening Doji Star: values [0, 100]
        dataframe['CDLEVENINGDOJISTAR'] = ta.CDLEVENINGDOJISTAR(dataframe)
        # Evening Star: values [0, 100]
        dataframe['CDLEVENINGSTAR'] = ta.CDLEVENINGSTAR(dataframe)
        """

        # Pattern Recognition - Bullish/Bearish candlestick patterns
        # ------------------------------------
        """
        # Three Line Strike: values [0, -100, 100]
        dataframe['CDL3LINESTRIKE'] = ta.CDL3LINESTRIKE(dataframe)
        # Spinning Top: values [0, -100, 100]
        dataframe['CDLSPINNINGTOP'] = ta.CDLSPINNINGTOP(dataframe) # values [0, -100, 100]
        # Engulfing: values [0, -100, 100]
        dataframe['CDLENGULFING'] = ta.CDLENGULFING(dataframe) # values [0, -100, 100]
        # Harami: values [0, -100, 100]
        dataframe['CDLHARAMI'] = ta.CDLHARAMI(dataframe) # values [0, -100, 100]
        # Three Outside Up/Down: values [0, -100, 100]
        dataframe['CDL3OUTSIDE'] = ta.CDL3OUTSIDE(dataframe) # values [0, -100, 100]
        # Three Inside Up/Down: values [0, -100, 100]
        dataframe['CDL3INSIDE'] = ta.CDL3INSIDE(dataframe) # values [0, -100, 100]
        """

        # Chart type
        # ------------------------------------
        # Heikinashi stategy
        heikinashi = qtpylib.heikinashi(dataframe)
        dataframe['ha_open'] = heikinashi['open']
        dataframe['ha_close'] = heikinashi['close']
        dataframe['ha_high'] = heikinashi['high']
        dataframe['ha_low'] = heikinashi['low']

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame) -> DataFrame:
        """
        Based on TA indicators, populates the buy signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                (dataframe['rsi'] < 35) &
                (dataframe['fastd'] < 35) &
                (dataframe['adx'] > 30) &
                (dataframe['plus_di'] > 0.5)
            ) |
            (
                (dataframe['adx'] > 65) &
                (dataframe['plus_di'] > 0.5)
            ),
            'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame) -> DataFrame:
        """
        Based on TA indicators, populates the sell signal for the given dataframe
        :param dataframe: DataFrame
        :return: DataFrame with buy column
        """
        dataframe.loc[
            (
                (
                    (qtpylib.crossed_above(dataframe['rsi'], 70)) |
                    (qtpylib.crossed_above(dataframe['fastd'], 70))
                ) &
                (dataframe['adx'] > 10) &
                (dataframe['minus_di'] > 0)
            ) |
            (
                (dataframe['adx'] > 70) &
                (dataframe['minus_di'] > 0.5)
            ),
            'sell'] = 1
        return dataframe

    def hyperopt_space(self) -> List[Dict]:
        """
        Define your Hyperopt space for the strategy
        """
        space = {
            'macd_below_zero': hp.choice('macd_below_zero', [
                {'enabled': False},
                {'enabled': True}
            ]),
            'mfi': hp.choice('mfi', [
                {'enabled': False},
                {'enabled': True, 'value': hp.quniform('mfi-value', 5, 25, 1)}
            ]),
            'fastd': hp.choice('fastd', [
                {'enabled': False},
                {'enabled': True, 'value': hp.quniform('fastd-value', 10, 50, 1)}
            ]),
            'adx': hp.choice('adx', [
                {'enabled': False},
                {'enabled': True, 'value': hp.quniform('adx-value', 15, 50, 1)}
            ]),
            'rsi': hp.choice('rsi', [
                {'enabled': False},
                {'enabled': True, 'value': hp.quniform('rsi-value', 20, 40, 1)}
            ]),
            'uptrend_long_ema': hp.choice('uptrend_long_ema', [
                {'enabled': False},
                {'enabled': True}
            ]),
            'uptrend_short_ema': hp.choice('uptrend_short_ema', [
                {'enabled': False},
                {'enabled': True}
            ]),
            'over_sar': hp.choice('over_sar', [
                {'enabled': False},
                {'enabled': True}
            ]),
            'green_candle': hp.choice('green_candle', [
                {'enabled': False},
                {'enabled': True}
            ]),
            'uptrend_sma': hp.choice('uptrend_sma', [
                {'enabled': False},
                {'enabled': True}
            ]),
            'trigger': hp.choice('trigger', [
                {'type': 'lower_bb'},
                {'type': 'lower_bb_tema'},
                {'type': 'faststoch10'},
                {'type': 'ao_cross_zero'},
                {'type': 'ema3_cross_ema10'},
                {'type': 'macd_cross_signal'},
                {'type': 'sar_reversal'},
                {'type': 'ht_sine'},
                {'type': 'heiken_reversal_bull'},
                {'type': 'di_cross'},
            ]),
            'stoploss': hp.uniform('stoploss', -0.5, -0.02),
        }
        return space

    def buy_strategy_generator(self, params) -> None:
        """
        Define the buy strategy parameters to be used by hyperopt
        """
        def populate_buy_trend(dataframe: DataFrame) -> DataFrame:
            conditions = []
            # GUARDS AND TRENDS
            if params['uptrend_long_ema']['enabled']:
                conditions.append(dataframe['ema50'] > dataframe['ema100'])
            if params['macd_below_zero']['enabled']:
                conditions.append(dataframe['macd'] < 0)
            if params['uptrend_short_ema']['enabled']:
                conditions.append(dataframe['ema5'] > dataframe['ema10'])
            if params['mfi']['enabled']:
                conditions.append(dataframe['mfi'] < params['mfi']['value'])
            if params['fastd']['enabled']:
                conditions.append(dataframe['fastd'] < params['fastd']['value'])
            if params['adx']['enabled']:
                conditions.append(dataframe['adx'] > params['adx']['value'])
            if params['rsi']['enabled']:
                conditions.append(dataframe['rsi'] < params['rsi']['value'])
            if params['over_sar']['enabled']:
                conditions.append(dataframe['close'] > dataframe['sar'])
            if params['green_candle']['enabled']:
                conditions.append(dataframe['close'] > dataframe['open'])
            if params['uptrend_sma']['enabled']:
                prevsma = dataframe['sma'].shift(1)
                conditions.append(dataframe['sma'] > prevsma)

            # TRIGGERS
            triggers = {
                'lower_bb': (
                    dataframe['close'] < dataframe['bb_lowerband']
                ),
                'lower_bb_tema': (
                    dataframe['tema'] < dataframe['bb_lowerband']
                ),
                'faststoch10': (qtpylib.crossed_above(
                    dataframe['fastd'], 10.0
                )),
                'ao_cross_zero': (qtpylib.crossed_above(
                    dataframe['ao'], 0.0
                )),
                'ema3_cross_ema10': (qtpylib.crossed_above(
                    dataframe['ema3'], dataframe['ema10']
                )),
                'macd_cross_signal': (qtpylib.crossed_above(
                    dataframe['macd'], dataframe['macdsignal']
                )),
                'sar_reversal': (qtpylib.crossed_above(
                    dataframe['close'], dataframe['sar']
                )),
                'ht_sine': (qtpylib.crossed_above(
                    dataframe['htleadsine'], dataframe['htsine']
                )),
                'heiken_reversal_bull': (
                    (qtpylib.crossed_above(dataframe['ha_close'], dataframe['ha_open'])) &
                    (dataframe['ha_low'] == dataframe['ha_open'])
                ),
                'di_cross': (qtpylib.crossed_above(
                    dataframe['plus_di'], dataframe['minus_di']
                )),
            }
            conditions.append(triggers.get(params['trigger']['type']))

            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'buy'] = 1

            return dataframe

        return populate_buy_trend
