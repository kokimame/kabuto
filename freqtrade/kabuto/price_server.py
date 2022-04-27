import asyncio
import json
import os
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from multiprocessing.context import Process
from pathlib import Path

import arrow
import numpy as np
import uvicorn
import websockets
from fastapi import FastAPI

import ccxt
from freqtrade.kabuto.credentials import KabutoCredential as kCred


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
        self.possible_timeframes = ['5s', '1m', '1d']  # Possible timeframe the server can serve
        self.timeframe_sec = self.timeframe_to_seconds(config['timeframe'])
        self.access_token = self.get_token()

        self.dynamics = PriceDynamics(mu=0.5)

        # TODO: Set path to InfluxDB (or any other more well-equipped? DB)
        if self.dummy_enabled:
            self.database_path = './kabuto_dummy.json'
        else:
            self.database_path = './kabuto_live.json'

        # TODO: Maybe find a better way to clear exiting data
        if Path(self.database_path).exists():
            os.remove(self.database_path)

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

    def start_generation(self):
        asyncio.run(self.data_generation())

    def start_listener(self):
        asyncio.run(self.push_listener())

    async def data_generation(self):
        if Path(self.database_path).exists():
            os.remove(self.database_path)

        dummy_data = self.prepare_data(self.pairlist, self.dynamics.limit)
        for pair in self.pairlist:
            dummy_data[pair] = dummy_data[self.pairlist[0]]

        # TODO: Use InfluxDB instead
        with open(self.database_path, 'w') as f:
            json.dump(dummy_data, f)

        server_task = asyncio.create_task(self.write_dummy(dummy_data))
        # api_task = asyncio.create_task(self.run())
        return await asyncio.gather(server_task, )

    async def push_listener(self):
        # NOTE: ping_timeout=None is requred since heartbeat is not supported on the server side
        # See a related issue on https://github.com/kabucom/kabusapi/issues/8
        async with websockets.connect(f'ws://{kCred.host_live}/kabusapi/websocket', ping_timeout=None) as ws:
            market_data = {pair: [] for pair in self.pairlist}
            cached_data = {pair: [] for pair in self.pairlist}
            last_volume = {pair: None for pair in self.pairlist}
            price_last_saved = time.time()

            while not ws.closed:
                res = await ws.recv()
                data = json.loads(res)
                # print(f'{timeframe_sec - (time.time() - price_last_saved):.2f}')
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

                # TODO: This heuristics is maybe wrong. Find more reliable way to detect a break
                if time.time() - price_last_saved > 10 * self.timeframe_sec:
                    print('Data ignored as the update took too much time (probably due to break)')
                    cached_data = {pair: [] for pair in self.pairlist}

                if time.time() - price_last_saved > self.timeframe_sec:
                    for pair, cache in cached_data.items():
                        if len(cache) > 0:  # Only if data cached in the timeframe
                            o, c = cache[0][0], cache[-1][0]
                            h, l = max(d[0] for d in cache), min(d[0] for d in cache)
                            v = sum(d[1] for d in cache)
                            t = cache[-1][2]  # Last timestamp
                            market_data[pair].append([t, o, h, l, c, v, 0])
                            if len(market_data[pair]) > self.dynamics.limit:
                                del market_data[pair][0]
                            print(f'\nUpdate @ {datetime.now()} {pair}: {market_data[pair][-1]}')
                        else:  # Save the last OHLCV if no data updated in the timeframe
                            if len(market_data[pair]) > 0:
                                last_ohlcv = market_data[pair][-1]
                                market_data[pair].append(last_ohlcv)

                    # Save data after receiving updates
                    with open(self.database_path, 'w') as f:
                        json.dump(market_data, f)

                        price_last_saved = time.time()
                    cached_data = {pair: [] for pair in self.pairlist}

    async def serve_price(self, symbol, interval):
        # TODO: Read OHLCV data from the database
        try:
            with open(self.database_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {f'{symbol}/JPY': []}
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
                json.dump(dummy_data, f)

            await asyncio.sleep(np.random.randint(1, 5))

    @staticmethod
    def timeframe_to_seconds(timeframe: str) -> int:
        """
        While this is the same with the one in exchange_beta, avoid circular import.
        There should be a better work-around.
        Translates the timeframe interval value written in the human readable
        form ('1m', '5m', '1h', '1d', '1w', etc.) to the number
        of seconds for one timeframe interval.
        """
        return ccxt.Exchange.parse_timeframe(timeframe)

    @staticmethod
    def get_token():
        kabusapi_url = f'http://{kCred.host_live}'
        obj = {'APIPassword': kCred.password_live}
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

    def register(self):
        # Register pairlist in watch list and receive PUSH data
        url = f'http://{kCred.host_live}/kabusapi/register'

        symbols = {'Symbols': []}
        for pair in self.pairlist:
            symbol, exchange = self.parse_ticker(pair)
            symbols['Symbols'].append({'Symbol': symbol, 'Exchange': exchange})

        json_data = json.dumps(symbols).encode('utf8')
        req = urllib.request.Request(url, json_data, method='PUT')
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-API-KEY', self.access_token)

        try:
            with urllib.request.urlopen(req) as res:
                content = json.loads(res.read())
            return content['RegistList']
        except Exception as e:
            content = json.loads(e.read())
            print(content)
            raise e

    @staticmethod
    def parse_ticker(pair):
        assert len(pair.split('/')) == 2
        identifier, _ = pair.split('/')
        assert len(identifier.split('@')) == 2
        symbol, exchange = identifier.split('@')
        assert symbol.isnumeric() and exchange.isnumeric()
        exchange = int(exchange)
        return symbol, exchange


if __name__ == '__main__':
    with open('../../user_data/config_tse.json', 'r') as f:
        config = json.load(f)
    pserv = PriceServer(config)
    pserv.start_generation()
