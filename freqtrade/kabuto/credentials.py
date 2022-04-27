import json
import os
from dataclasses import dataclass


@dataclass
class Credential:
    kabusapi_password: str
    kabusapi_id: str
    host_ipaddr: str
    host_live: str
    host_test: str
    password_live: str
    password_test: str
    onetime_token: str


with open(f'{os.environ["HOME"]}/.kabuto/credentials.json') as f:
    CredentialRaw = json.load(f)

KabutoCredential = Credential(
    kabusapi_password=CredentialRaw['KABUCOM_PASSWORD'],
    kabusapi_id=CredentialRaw['KABUSAPI_ID'],
    host_ipaddr=CredentialRaw['KABUSAPI_HOST'],
    host_live=CredentialRaw['KABUSAPI_HOST_LIVE'],
    host_test=CredentialRaw['KABUSAPI_HOST_TEST'],
    password_live=CredentialRaw['KABUSAPI_PASSWORD_LIVE'],
    password_test=CredentialRaw['KABUSAPI_PASSWORD_TEST'],
    onetime_token=CredentialRaw['KABUSAPI_ONETIME_TOKEN']
)
