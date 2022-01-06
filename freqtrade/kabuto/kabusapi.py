import asyncio
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import arrow
import websockets

from freqtrade.credentials_DONT_UPLOAD import *
from freqtrade.kabuto.exchange_beta import timeframe_to_seconds

limit = 1000
DATABASE_PATH = ''


async def push_listener(pairs, timeframe, database_path):
    # NOTE: ping_timeout=None is requred since heartbeat is not supported on the server side
    # See a related issue on https://github.com/kabucom/kabusapi/issues/8
    async with websockets.connect(f'ws://{KABUSAPI_LIVE_HOST}/kabusapi/websocket',
                                  ping_timeout=None) as ws:
        market_data = {pair: [] for pair in pairs}
        cached_data = {pair: [] for pair in pairs}
        last_volume = {pair: None for pair in pairs}
        price_last_saved = time.time()
        timeframe_sec = timeframe_to_seconds(timeframe)
        while not ws.closed:
            res = await ws.recv()
            data = json.loads(res)
            print(f'{timeframe_sec - (time.time() - price_last_saved):.2f}')
            symbol, exchange = data['Symbol'], data['Exchange']
            pair = f'{symbol}@{exchange}/JPY'

            # Drop the first data to compute the relative increase of volume
            if last_volume[pair] is None:
                last_volume[pair] = data['TradingVolume']
                continue

            cache_by_pair = cached_data[pair]
            int_timestamp = arrow.utcnow().int_timestamp * 1000
            cache_by_pair.append([data['CurrentPrice'],
                                  data['TradingVolume'] - last_volume[pair],
                                  int_timestamp])
            last_volume[pair] = data['TradingVolume']

            if time.time() - price_last_saved > 2 * timeframe_sec:
                print('Data ignored as the update took too much time (probably due to break)')
                cached_data = {pair: [] for pair in pairs}

            if time.time() - price_last_saved > timeframe_sec:
                for pair, cache in cached_data.items():
                    if len(cache) > 0:  # Only if data cached in the timeframe
                        o, c = cache[0][0], cache[-1][0]
                        h, l = max(d[0] for d in cache), min(d[0] for d in cache)
                        v = sum(d[1] for d in cache)
                        t = cache[-1][2]  # Last timestamp
                        market_data[pair].append([t, o, h, l, c, v, 0])
                        if len(market_data[pair]) > limit:
                            del market_data[pair][0]
                        print(f'\nUpdate @ {datetime.now()} {pair}: {market_data[pair][-1]}')
                    else:  # Save the last OHLCV if no data updated in the timeframe
                        if len(market_data[pair]) > 0:
                            last_ohlcv = market_data[pair][-1]
                            market_data[pair].append(last_ohlcv)

                # Save data after receiving updates
                with open(database_path, 'w') as f:
                    # NOTE Having indentation with extra memory may delay the process
                    json.dump(market_data, f, indent=1)

                    price_last_saved = time.time()
                cached_data = {pair: [] for pair in pairs}


async def create_client_task(database_path, pairs, timeframe):
    client = asyncio.create_task(push_listener(pairs, timeframe, database_path))
    await client
    return client


def run_push_listener(database_path, whitelist, timeframe):
    # Entrypoint for the PUSH listener
    loop = asyncio.get_event_loop()
    loop.create_task(push_listener(whitelist, timeframe, database_path))
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        exit()
    # asyncio.run(create_client_task(database_path, whitelist, timeframe))


def parse_kabus_ticker(pair):
    assert len(pair.split('/')) == 2
    identifier, _ = pair.split('/')
    assert len(identifier.split('@')) == 2
    symbol, exchange = identifier.split('@')
    assert symbol.isnumeric() and exchange.isnumeric()
    exchange = int(exchange)
    return symbol, exchange


def register_whitelist(access_token, whitelist):
    url = f'http://{KABUSAPI_LIVE_HOST}/kabusapi/register'

    symbols = {'Symbols': []}
    for pair in whitelist:
        symbol, exchange = parse_kabus_ticker(pair)
        symbols['Symbols'].append({'Symbol': symbol, 'Exchange': exchange})

    json_data = json.dumps(symbols).encode('utf8')
    req = urllib.request.Request(url, json_data, method='PUT')
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-API-KEY', access_token)

    try:
        with urllib.request.urlopen(req) as res:
            content = json.loads(res.read())
        return content['RegistList']
    except Exception as e:
        raise e


def get_access_token():
    kabusapi_url = f'http://{KABUSAPI_LIVE_HOST}'
    obj = {'APIPassword': KABUSAPI_LIVE_PW}
    json_data = json.dumps(obj).encode('utf8')

    url = f'{kabusapi_url}/kabusapi/token'
    req = urllib.request.Request(url, json_data, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req) as res:
            content = json.loads(res.read())
            return content['Token']
    except Exception as e:
        raise e


if __name__ == '__main__':
    whitelist = [
        '8306@1/JPY', '4689@1/JPY', '6501@1/JPY', '3826@1/JPY', '5020@1/JPY', '3632@1/JPY'
    ]
    token = get_access_token()
    print(f'Token -> {token}')
    registry = register_whitelist(token, whitelist)
    print(f'Registered List -> {registry}')
    run_push_listener('./test_real_price.json', whitelist, '1m')