from freqtrade.persistence.models import Order, Trade
from datetime import datetime, timedelta, timezone

trade = Trade(
    pair='XRP/BTC',
    stake_amount=0.001,
    amount=123.0,
    amount_requested=123.0,
    fee_open=fee.return_value,
    fee_close=fee.return_value,
    open_rate=0.05,
    close_rate=0.06,
    close_profit=-0.01 if is_short else 0.01,
    close_profit_abs=-0.001155 if is_short else 0.000155,
    exchange='binance',
    is_open=False,
    strategy='StrategyTestV3',
    timeframe=5,
    exit_reason='roi',
    open_date=datetime.now(tz=timezone.utc) - timedelta(minutes=20),
    close_date=datetime.now(tz=timezone.utc),
    is_short=is_short
)