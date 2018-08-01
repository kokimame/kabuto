# SQL Helper
This page constains some help if you want to edit your sqlite db.

## Install sqlite3
**Ubuntu/Debian installation**
```bash
sudo apt-get install sqlite3
```

## Open the DB
```bash
sqlite3
.open <filepath>
```

## Table structure

### List tables
```bash
.tables
```

### Display table structure
```bash
.schema <table_name>
```

### Trade table structure
```sql
CREATE TABLE trades (
	id INTEGER NOT NULL,
	exchange VARCHAR NOT NULL,
	pair VARCHAR NOT NULL,
	is_open BOOLEAN NOT NULL,
	fee_open FLOAT NOT NULL,
	fee_close FLOAT NOT NULL,
	open_rate FLOAT,
	open_rate_requested FLOAT,
	close_rate FLOAT,
	close_rate_requested FLOAT,
	close_profit FLOAT,
	stake_amount FLOAT NOT NULL,
	amount FLOAT,
	open_date DATETIME NOT NULL,
	close_date DATETIME,
	open_order_id VARCHAR,
	PRIMARY KEY (id),
	CHECK (is_open IN (0, 1))
);
```

## Get all trades in the table

```sql
SELECT * FROM trades;
```

## Fix trade still open after a /forcesell

```sql
UPDATE trades
SET is_open=0, close_date=<close_date>, close_rate=<close_rate>, close_profit=close_rate/open_rate-1  
WHERE id=<trade_ID_to_update>;
```

**Example:**
```sql
UPDATE trades
SET is_open=0, close_date='2017-12-20 03:08:45.103418', close_rate=0.19638016, close_profit=0.0496  
WHERE id=31;
```

## Insert manually a new trade

```sql
INSERT 
INTO trades (exchange, pair, is_open, fee_open, fee_close, open_rate, stake_amount, amount, open_date) 
VALUES ('BITTREX', 'BTC_<COIN>', 1, 0.0025, 0.0025, <open_rate>, <stake_amount>, <amount>, '<datetime>')
```

**Example:**
```sql
INSERT INTO trades (exchange, pair, is_open, fee_open, fee_close, open_rate, stake_amount, amount, open_date) VALUES ('BITTREX', 'BTC_ETC', 1, 0.0025, 0.0025, 0.00258580, 0.002, 0.7715262081, '2017-11-28 12:44:24.000000')
```

## Fix wrong fees in the table
If your DB was created before 
[PR#200](https://github.com/freqtrade/freqtrade/pull/200) was merged
(before 12/23/17).

```sql
UPDATE trades SET fee=0.0025 WHERE fee=0.005;
```
