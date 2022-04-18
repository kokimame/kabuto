import asyncio
import json
import os
from dataclasses import dataclass
from multiprocessing.context import Process
from pathlib import Path

import arrow
import numpy as np
import uvicorn
from fastapi import FastAPI


@dataclass
class PriceDynamics:
    mu: float = 0.1
    sigma: float = 5.0
    initial_price: int = 500
    limit: int = 100


class PriceServer:
    API = FastAPI()

    def __init__(self, config):
        self.dummy_enabled: bool = config['kabuto']['dummy']['enabled']
        self.timeframe = config['timeframe']
        self.pairlist = config['exchange']['pair_whitelist']
        self.access_token = config['kabuto']['token']
        self.intervals = ['1m']

        self.dynamics = PriceDynamics(mu=0.5)

        if self.dummy_enabled:
            self.database_path = config['kabuto']['dummy']['database_path']
        else:
            self.database_path = config['kabuto']['database_path']

        self._api = FastAPI()
        self._setup_routes()
        Process(target=self.run_blocking).start()

    async def run(self):
        config = uvicorn.Config(
            self._api,
            port=8999,
            lifespan='off',
        )
        server = uvicorn.Server(config=config)
        await server.serve()

    def run_blocking(self):
        uvicorn.run(self._api, port=8999)

    def _setup_routes(self):
        self._api.add_api_route(
            path='/charts/{symbol}/JPY/{interval}',
            endpoint=self.serve_price,
            methods=['GET']
        )

    async def serve_price(self, symbol, interval):
        if self.dummy_enabled:
            # TODO: Read OHLCV data from the database
            with open(self.database_path, 'r') as f:
                data = json.load(f)
            return {symbol: str(data[f'{symbol}/JPY'])}

    def prepare_data(self, pairs, limit):
        dummy_data = {}
        for pair in pairs:
            o = self.dynamics.initial_price
            h, l, c, v = self._get_hlcv(o)
            starting_time = arrow.utcnow().int_timestamp * 1000
            ohlcvs = [[starting_time, o, h, l, c, v, 0]]
            for i in range(limit - 1):
                o = ohlcvs[0][4]  # The last close is the next open
                h, l, c, v = self._get_hlcv(o)
                timestamp = starting_time - 60 * (i + 1)
                ohlcvs.insert(0, [timestamp, o, h, l, c, v, 0])
            dummy_data[pair] = ohlcvs
        return dummy_data

    def _get_hlcv(self, open):
        c = open + np.random.normal(loc=self.dynamics.mu, scale=self.dynamics.sigma)
        h = max(open, c) + np.random.randint(1, 5)
        l = min(open, c) - np.random.randint(1, 5)

        v = np.random.randint(10000, 15000)
        return h, l, c, v

    async def write_dummy(self, dummy_data):
        pairs = list(dummy_data.keys())

        while True:
            last_pair_data = {pair: dummy_data[pair][-1] for pair in pairs}
            t = arrow.utcnow().int_timestamp * 1000
            for pair, last_data in last_pair_data.items():
                next_open = last_data[4]  # Last close is the next open price
                h, l, c, v = self._get_hlcv(next_open)
                ohlcv = [t, next_open, h, l, c, v, 0]
                dummy_data[pair].append(ohlcv)

            with open(self.database_path, 'w') as f:
                json.dump(dummy_data, f, indent=1)

            await asyncio.sleep(np.random.randint(1, 5))

    async def data_generation(self):
        if Path(self.database_path).exists():
            os.remove(self.database_path)

        dummy_data = self.prepare_data(self.pairlist, self.dynamics.limit)
        for pair in self.pairlist:
            dummy_data[pair] = dummy_data[self.pairlist[0]]

        # TODO: Use InfluxDB instead
        with open(self.database_path, 'w') as f:
            json.dump(dummy_data, f, indent=1)

        server_task = asyncio.create_task(self.write_dummy(dummy_data))
        # api_task = asyncio.create_task(self.run())
        return await asyncio.gather(server_task,)

    def start_generation(self):
        asyncio.run(self.data_generation())

    def start_listener(self):
        pass

    async def push_listener(self):
        pass

    def listen(self):
        pass

    def save(self):
        pass

    def register(self):
        pass


if __name__ == '__main__':
    with open('../../user_data/config_tse.json', 'r') as f:
        config = json.load(f)
    pserv = PriceServer(config)
    pserv.start_generation()