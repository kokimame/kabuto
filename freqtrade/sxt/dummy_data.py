import asyncio
import json
import os
from pathlib import Path

import arrow
import numpy as np
import websockets

np.random.seed(0)
mu = 0.001
sigma = 0.91
initial_price = 500
limit = 1000
ws_port = 8764
DATABASE_PATH = ''


def get_hlcv(open):
    h = open + np.random.randint(1, 10)
    l = open - np.random.randint(1, 5)
    c = (h + l) / 2
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
        await asyncio.sleep(np.random.randint(5, 10))


async def dummy_server():
    async with websockets.serve(send_dummy_data, 'localhost', ws_port):
        await asyncio.Future()


async def data_client():
    # Load existing dummy data
    with open(DATABASE_PATH, 'r') as f:
        dummy_data = json.load(f)

    async with websockets.connect(f'ws://localhost:{ws_port}') as ws:
        while not ws.closed:
            res = await ws.recv()
            # print(res)
            data = json.loads(res)

            for pair, ohlcv in data.items():
                dummy_data[pair].append(ohlcv)
                del dummy_data[pair][0]

            # Save data after receiving updates
            with open(DATABASE_PATH, 'w') as f:
                # Indentation may
                json.dump(dummy_data, f, indent=1)


async def start_data_generation(database_path, pairs):
    global DATABASE_PATH
    DATABASE_PATH = database_path  # Will be accessed in async function
    if Path(DATABASE_PATH).exists():
        os.remove(DATABASE_PATH)

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

    with open(DATABASE_PATH, 'w') as f:
        json.dump(dummy_data, f, indent=1)

    server = asyncio.create_task(dummy_server())
    client = asyncio.create_task(data_client())
    tasks = await asyncio.gather(server, client)
    return tasks


def dummy_data_generator(database_path, whitelist):
    # Entrypoint to the data generation
    asyncio.run(
        start_data_generation(database_path, whitelist))


if __name__ == '__main__':
    asyncio.run(start_data_generation(
        './test_dummy_server.json', ['5020/JPY']))
