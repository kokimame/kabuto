import json
import os
from dataclasses import dataclass


@dataclass
class Credential:
    password: str
    id: str
    host_ipaddr: str
    host_live: str
    password_live: str
    onetime_token: str


with open(f'{os.environ["HOME"]}/.kabuto/credentials.json') as f:
    data = json.load(f)

KabutoCredential = Credential(
    password=data['KABUCOM_PASSWORD'],
    id=data['KABUSAPI_ID'],
    host_ipaddr=data['KABUSAPI_HOST'],
    host_live=data['KABUSAPI_HOST_LIVE'],
    password_live=data['KABUSAPI_PASSWORD_LIVE'],
    onetime_token=data['KABUSAPI_ONETIME_TOKEN']
)
