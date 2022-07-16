import asyncio
import json
import os
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing.context import Process
from pathlib import Path
from typing import List

import arrow
import numpy as np
import uvicorn
import websockets
from fastapi import FastAPI

import ccxt
from freqtrade.kabuto.credentials import KABUTO_CREDENTIAL as kCred


@dataclass
class PriceDynamics:
    mu: float = 0.1
    sigma: float = 5.0
    initial_price: int = 500
    limit: int = 100


@dataclass
class Cache:
    """
    Cache to store current price data sent from PUSH server
    and to be used to compute TOHLCV
    ------
    data: [[Price, RelativeVolume, Timestamp], ...]
    last_volume: Last volume informed, used to compute relative volume change
    """
    data: List[List] = field(default_factory=list)
    last_volume: float = None


@dataclass()
class TOHLCV:
    """
    Experimental dataclass for TOHCLV data.
    Only used partially so far.
    """
    t: int
    o: float
    h: float
    c: float
    l: float
    v: float
    nonce: int = 0

    def as_list(self):
        return [self.t, self.o, self.h, self.l, self.c, self.v, self.nonce]


class PriceServer:
    API = FastAPI()

    def __init__(self, config):
        self.dummy_config: dict = config['kabuto']['dummy']
        self.timeframe = config['timeframe']
        self.pairlist = config['exchange']['pair_whitelist']
        self.possible_timeframes = ['5s', '1m', '1d']  # Possible timeframe the server can serve
        self.timeframe_sec = self.timeframe_to_seconds(config['timeframe'])
        self.access_token = self.get_token()
        self.price_dynamics = PriceDynamics(**self.dummy_config['dynamics'])

        # TODO: Set path to InfluxDB (or any other more well-equipped? DB)
        if self.dummy_config['enabled']:
            self.database_path = './kabuto_dummy.json'
        else:
            self.database_path = './kabuto_live.json'

        # TODO: Maybe find a better way to clear exiting data
        if Path(self.database_path).exists():
            os.remove(self.database_path)

        self._api = FastAPI()
        self._setup_routes()

    async def run(self):
        config = uvicorn.Config(
            self._api,
            port=8999,
            lifespan='off',
        )
        server = uvicorn.Server(config=config)
        await server.serve()

    def start_api(self):
        Process(target=self._run_blocking).start()

    def _run_blocking(self):
        uvicorn.run(self._api, port=8999)

    def _setup_routes(self):
        self._api.add_api_route(
            path='/charts/{market}/{fiat}/{interval}',
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

        dummy_data = self.prepare_data(self.pairlist, self.price_dynamics.limit)

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
            # Entire data to be saved in the database (Intended to work with JSON but not very efficient)
            market_data = {pair: [] for pair in self.pairlist}

            # Cached price within a timeframe.
            # At the end of the frame, OHLCV will be calculated and appened to the market data
            caches = {pair: Cache() for pair in self.pairlist}
            time_last_saved = time.time()

            while not ws.closed:
                timeout_raised = False
                try:
                    res = await asyncio.wait_for(ws.recv(), timeout=self.timeframe_sec)
                    data = json.loads(res)
                    stock_code, exchange = data['Symbol'], data['Exchange']
                    pair = f'{stock_code}@{exchange}/JPY'
                    # Drop the first data to compute the relative increase of volume
                    if caches[pair].last_volume is None:
                        caches[pair].last_volume = data['TradingVolume']
                        continue
                    else:
                        int_timestamp = arrow.utcnow().int_timestamp * 1000
                        caches[pair].data.append([data['CurrentPrice'],
                                                  data['TradingVolume'] - caches[pair].last_volume,
                                                  int_timestamp])
                        caches[pair].last_volume = data['TradingVolume']
                except asyncio.TimeoutError:
                    timeout_raised = True
                    for pair, ohlcvs in market_data.items():
                        # Handle in case no prior OHLCV exits
                        if len(ohlcvs) == 0:
                            continue
                        last_close = ohlcvs[-1][4]
                        int_timestamp = arrow.utcnow().int_timestamp * 1000
                        caches[pair].data = [[last_close, 0, int_timestamp]]
                    print('Websocket timeout. Proceed to compute TOHLCV from cache if any.')

                if time.time() - time_last_saved > self.timeframe_sec or timeout_raised:
                    print('Writing TOHLCV to JSON')
                    for pair, cache in caches.items():
                        if len(cache.data) == 0:
                            continue
                        market_data[pair].append(
                            TOHLCV(t=cache.data[-1][2],  # Last timestamp
                                   o=cache.data[0][0], h=max(d[0] for d in cache.data),
                                   l=min(d[0] for d in cache.data), c=cache.data[-1][0],
                                   v=sum(d[1] for d in cache.data), nonce=0).as_list()
                        )
                        print(f'\nUpdate @ {datetime.now()} {pair}: {market_data[pair][-1]}')
                    # Clear caches
                    caches = {pair: Cache() for pair in self.pairlist}
                    time_last_saved = time.time()
                    # Save data after receiving updates
                    with open(self.database_path, 'w') as f:
                        json.dump(market_data, f)

    async def serve_price(self, market, fiat, interval):
        # TODO: Read OHLCV data from the database
        try:
            with open(self.database_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {f'{market}/{fiat}': []}
        return {market: str(data[f'{market}/JPY'])}

    def prepare_data(self, pairs, limit):
        dummy_data = {}
        for pair in pairs:
            ohlcvs = [self._get_tohlcv(limit=limit)]
            # Prepare for limit - 1 ticks [-(limit - 2), 0]
            for _ in range(limit):
                ohlcvs.append(self._get_tohlcv(prev_t=ohlcvs[-1][0], prev_c=ohlcvs[-1][4]))
            dummy_data[pair] = ohlcvs

        if self.dummy_config['real_scale'] and self.price_dynamics.limit == 300:
            # Insert break if real scale is on and limit is exactly 300 ticks (equals 300 mins = 5hr)
            for pair in pairs:
                ohlcvs = dummy_data[pair]
                bf_close = ohlcvs[150][4]
                bf_time = ohlcvs[150][0]
                for i, (t, o, h, l, c, v, nonce) in enumerate(ohlcvs[150:], 150):
                    ohlcvs[i] = [t + (60 * 60 * 1000), o, h, l, c, v, nonce]
                # Lunch break is 60 min = 60 ticks
                for i in range(60):
                    bf_time += (self.timeframe_sec * 1000)
                    ohlcvs.insert(150 + i, [bf_time, bf_close, bf_close, bf_close, bf_close, 0, 0])

        return dummy_data

    def _get_tohlcv(self, prev_t=None, prev_c=None, limit=None):
        if prev_c is None:
            o = self.price_dynamics.initial_price
        else:
            # Last close is the next open
            o = prev_c
        if prev_t is None:
            assert limit, 'Limit is required to initialize time'
            starting_time = arrow.utcnow().int_timestamp * 1000
            t = starting_time + (self.timeframe_sec * 1000) * (-limit)
        else:
            t = prev_t + (self.timeframe_sec) * 1000

        c = o + np.random.normal(loc=self.price_dynamics.mu, scale=self.price_dynamics.sigma)
        h = max(o, c) + np.random.randint(1, 5)
        l = min(o, c) - np.random.randint(1, 5)
        v = np.random.randint(10000, 15000)
        nonce = 0
        return [t, o, h, l, c, v, nonce]

    async def write_dummy(self, dummy_data):
        pairs = list(dummy_data.keys())

        while True:
            last_pair_data = {pair: dummy_data[pair][-1] for pair in pairs}
            for pair, last_data in last_pair_data.items():
                dummy_data[pair].append(self._get_tohlcv(prev_t=last_data[0], prev_c=last_data[4]))

            with open(self.database_path, 'w') as f:
                json.dump(dummy_data, f)
            print('Write a dummy OHLCV data for each pair.')
            await asyncio.sleep(self.timeframe_sec)

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

    def register(self, symbols):
        """
        Register symbols to receive PUSHed data of them
        :param: symbols: List of pair symbols to register (same with self.pairlist)
        """
        # Register pairlist in watch list and receive PUSH data
        url = f'http://{kCred.host_live}/kabusapi/register'

        body = {'Symbols': []}
        for symbol in symbols:
            stock_code, exchange = self.parse_symbol(symbol)
            body['Symbols'].append({'Symbol': stock_code, 'Exchange': exchange})

        body_str = json.dumps(body).encode('utf8')
        req = urllib.request.Request(url, body_str, method='PUT')
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

    def unregister(self, symbols):
        """
        Unregister symbols and do not receive PUSHed data
        :param: symbols: List of pair symbols to unregister (same with self.pairlist). If none, unregister all.
        """
        body = {'Symbols': []}
        url = f'http://{kCred.host_live}/kabusapi/unregister'
        if len(symbols) > 0:
            for symbol in symbols:
                stock_code, exchange = self.parse_symbol(symbol)
                body['Symbols'].append(dict(Symbol=stock_code, Exchange=exchange))
            body_str = json.dumps(body).encode('utf8')
            req = urllib.request.Request(url, body_str, method='PUT')
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

    def unregister_all(self):
        """
        Unregister all symbols from PUSH
        """
        body = {'Symbols': []}
        url = f'http://{kCred.host_live}/kabusapi/unregister/all'
        body_str = json.dumps(body).encode('utf8')
        req = urllib.request.Request(url, body_str, method='PUT')
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
    def parse_symbol(pair):
        assert len(pair.split('/')) == 2
        identifier, _ = pair.split('/')
        assert len(identifier.split('@')) == 2
        stock_code, exchange = identifier.split('@')
        assert stock_code.isnumeric() and exchange.isnumeric(), f'ERROR: Unexpected stock code/exhange format {(stock_code, exchange)}'
        exchange = int(exchange)
        return stock_code, exchange


if __name__ == '__main__':
    print(TOHLCV(1, 1, 0, 0, 0, 0, 0).as_list())

    with open('../../user_data/config_tse.json', 'r') as f:
        config = json.load(f)
    pserv = PriceServer(config)
    # pserv.start_generation()
    # print(pserv.register(['5020@1/JPY', '8306@1/JPY', '9318@1/JPY']))
    # time.sleep(3)
    print(pserv.unregister_all())
