import asyncio
import json
import os
import time
from pathlib import Path

import arrow
import numpy as np
import websockets

from freqtrade.kabuto.exchange_beta import timeframe_to_seconds

np.random.seed(1)
mu = 0.1
sigma = 5
initial_price = 500
limit = 1000
ws_port = 8765
DATABASE_PATH = ''


def get_hlcv(open):
    c = open + np.random.normal(loc=mu, scale=sigma)
    h = max(open, c) + np.random.randint(1, 5)
    l = min(open, c) - np.random.randint(1, 5)

    v = np.random.randint(10000, 15000)
    return h, l, c, v


def price_generator_by_pair(last_pair_data):
    while True:
        t = arrow.utcnow().int_timestamp * 1000
        for pair, last_data in last_pair_data.items():
            next_open = last_data[4]  # Last close is the next open price
            h, l, c, v = get_hlcv(next_open)
            ohlcv = [t, next_open, h, l, c, v, 0]
            last_pair_data[pair] = ohlcv
        yield last_pair_data


async def send_dummy_data(websocket):
    with open(DATABASE_PATH, 'r') as f:
        dummy_data = json.load(f)
    pairs = list(dummy_data.keys())
    last_pair_data = {pair: dummy_data[pair][-1] for pair in pairs}

    for pair_data in price_generator_by_pair(last_pair_data):
        # Format data compatible with JSON (no single quote wrapping a string)
        # and send the string via the socket
        await websocket.send(str(json.dumps(pair_data)))
        # PUSH data comes to the client sporadically
        await asyncio.sleep(np.random.randint(1, 5))


async def dummy_server():
    async with websockets.serve(send_dummy_data, 'localhost', ws_port):
        await asyncio.Future()


async def push_listener(pairs, timeframe):
    # Load existing dummy data
    with open(DATABASE_PATH, 'r') as f:
        dummy_data = json.load(f)

    async with websockets.connect(f'ws://localhost:{ws_port}') as ws:
        cached_ohlcvs = {pair: [] for pair in pairs}
        ohlcv_last_updated = time.time()
        timeframe_sec = timeframe_to_seconds(timeframe)
        while not ws.closed:
            res = await ws.recv()
            # print(res)
            data = json.loads(res)

            for pair, ohlcv in data.items():
                cached_ohlcvs[pair].append(ohlcv)

            if time.time() - ohlcv_last_updated > timeframe_sec:
                for pair, ohlcvs in cached_ohlcvs.items():
                    # Open for this timeframe is the first open price in the cache
                    # Close for this timeframe is the last close price in the cache
                    o, c = ohlcvs[0][1], ohlcvs[-1][4]
                    h, l = max(ohlcv[4] for ohlcv in ohlcvs), min(ohlcv[4] for ohlcv in ohlcvs)
                    v = sum(ohlcv[5] for ohlcv in ohlcvs)
                    t = ohlcvs[-1][0]  # Last timestamp
                    dummy_data[pair].append([t, o, h, l, c, v, 0])
                    del dummy_data[pair][0]

                for pair in pairs:
                    cached_ohlcvs[pair] = cached_ohlcvs[pairs[0]]

                # Save data after receiving updates
                with open(DATABASE_PATH, 'w') as f:
                    # NOTE Having indentation with extra memory may delay the process
                    json.dump(dummy_data, f, indent=1)

                    ohlcv_last_updated = time.time()
                    print(f'OHLCV updated @ {ohlcv_last_updated}: '
                          f'{[v[-1] for k, v in dummy_data.items()]}')
                    cached_ohlcvs = {pair: [] for pair in pairs}


def setup_fixed_amount_data(pairs, limit):
    dummy_data = {}
    for pair in pairs:
        o = initial_price
        h, l, c, v = get_hlcv(o)
        starting_time = arrow.utcnow().int_timestamp * 1000
        ohlcvs = [[starting_time, o, h, l, c, v, 0]]
        for i in range(limit - 1):
            o = ohlcvs[0][4]  # The last close is the next open
            h, l, c, v = get_hlcv(o)
            timestamp = starting_time - 60 * (i + 1)
            ohlcvs.insert(0, [timestamp, o, h, l, c, v, 0])
        dummy_data[pair] = ohlcvs
    return dummy_data


async def start_data_generation(database_path, pairs, timeframe):
    global DATABASE_PATH
    DATABASE_PATH = database_path  # Will be accessed in async function
    if Path(DATABASE_PATH).exists():
        os.remove(DATABASE_PATH)

    dummy_data = setup_fixed_amount_data(pairs, limit)
    for pair in pairs:
        dummy_data[pair] = dummy_data[pairs[0]]

    with open(DATABASE_PATH, 'w') as f:
        json.dump(dummy_data, f, indent=1)

    server = asyncio.create_task(dummy_server())
    client = asyncio.create_task(push_listener(pairs, timeframe))
    tasks = await asyncio.gather(server, client)
    return tasks


def dummy_data_generator(database_path, whitelist, timeframe):
    # Entrypoint to the data generation
    asyncio.run(
        start_data_generation(database_path, whitelist, timeframe))


if __name__ == '__main__':
    asyncio.run(start_data_generation(
        './test_dummy_server.json', ['5020/JPY'], '1m'))
    # import matplotlib.pyplot as plt
    # dummy_data = setup_fixed_amount_data(['5020/JPY'], 2000)
    # for key, ohlcvs in dummy_data.items():
    #     closes = [ohlcv[4] for ohlcv in ohlcvs]
    #     d1, d2 = closes[:1000], closes[1000:]
    #     d2 = [2 * d2[0] - d for d in d2]
    #     plt.plot(d1 + d2)
    #     plt.show()
    #     break
