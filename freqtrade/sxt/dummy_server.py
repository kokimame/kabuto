import json
import shutil
from multiprocessing import Process

import asyncio
from pathlib import Path

import arrow
import numpy as np
import websockets

np.random.seed(0)
mu = 0.001
sigma = 0.91
initial_price = 500
limit = 1000
DATABASE_PATH = ''


def get_hlcv(open):
    h = open + np.random.randint(1, 10)
    l = open - np.random.randint(1, 5)
    c = (h + l) / 2
    v = np.random.randint(10000, 15000)
    return h, l, c, v


def price_generator(last_pair_data):
    while True:
        t = arrow.utcnow().int_timestamp * 1000
        for pair, last_data in last_pair_data.items():
            next_open = last_data[4]  # Last close is the next open price
            h, l, c, v = get_hlcv(next_open)
            ohlcv = [t, next_open, h, l, c, v, 0]
            last_pair_data[pair] = ohlcv
        yield last_pair_data


async def generate_price(websocket):
    with open(DATABASE_PATH, 'r') as f:
        dummy_data = json.load(f)
    pairs = list(dummy_data.keys())
    last_pair_data = {pair: dummy_data[pair][-1] for pair in pairs}

    for price in price_generator(last_pair_data):
        await websocket.send(str(price))
        await asyncio.sleep(1)


async def update_data():
    async with websockets.serve(generate_price, 'localhost', 8765):
        await asyncio.Future()

    async with websockets.connect('ws://localhost:8765') as ws:
        while not ws.closed:
            res = await ws.recv()
            data = json.loads(res)

            # Load existing dummy data
            with open(DATABASE_PATH, 'r') as f:
                dummy_data = json.load(f)

            for pair, ohlcv in data.items():
                dummy_data[pair].append(ohlcv)
                del dummy_data[pair][0]

            # Save data after update
            with open(DATABASE_PATH, 'w') as f:
                json.dump(dummy_data, f)


def run_dummy(database_path, pairs):
    global DATABASE_PATH
    DATABASE_PATH = database_path  # Will be accessed in async function
    if Path(DATABASE_PATH).exists():
        shutil.rmtree(DATABASE_PATH, ignore_errors=True)

    dummy_data = {}
    for pair in pairs:
        ohlcvs = []
        o = initial_price
        h, l, c, v = get_hlcv(o)
        starting_time = arrow.utcnow().int_timestamp * 1000
        ohlcvs.append([starting_time, o, h, l, c, v, 0])
        for i in range(limit - 1):
            o = ohlcvs[0][4]  # The last close is the next open
            h, l, c, v = get_hlcv(o)
            timestamp = starting_time - 60 * (i + 1)
            ohlcvs.insert(0, [timestamp, o, h, l, c, v, 0])
        dummy_data[pair] = ohlcvs

    with open(DATABASE_PATH, 'w') as f:
        json.dump(dummy_data, f)

    asyncio.run(update_data())


if __name__ == '__main__':
    run_dummy('./test_dummy_server.json', ['5020/JPY', '8326/JPY'])
