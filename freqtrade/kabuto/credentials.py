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


try:
    with open(f'{os.environ["HOME"]}/.kabuto/credentials.json') as f:
        CREDENTIAL_RAW = json.load(f)

    KABUTO_CREDENTIAL = Credential(
        kabusapi_password=CREDENTIAL_RAW['KABUCOM_PASSWORD'],
        kabusapi_id=CREDENTIAL_RAW['KABUSAPI_ID'],
        host_ipaddr=CREDENTIAL_RAW['KABUSAPI_HOST'],
        host_live=CREDENTIAL_RAW['KABUSAPI_HOST_LIVE'],
        host_test=CREDENTIAL_RAW['KABUSAPI_HOST_TEST'],
        password_live=CREDENTIAL_RAW['KABUSAPI_PASSWORD_LIVE'],
        password_test=CREDENTIAL_RAW['KABUSAPI_PASSWORD_TEST'],
        onetime_token=CREDENTIAL_RAW['KABUSAPI_ONETIME_TOKEN']
    )
except FileNotFoundError:
    print('ERROR: Credential file for kabu STATION API not found!')
    print('Create $HOME/.kabuto/credentials.json and fill the information in the following format.')
    print("""{
  "KABUCOM_PASSWORD": "",
  "KABUSAPI_ID": "",
  "KABUSAPI_HOST": "xxx.xxx.xxx.xxx",
  "KABUSAPI_HOST_LIVE": "xxx.xxx.xxx.xxx:port/live",
  "KABUSAPI_HOST_TEST": "xxx.xxx.xxx.xxx:port/live",
  "KABUSAPI_PASSWORD_LIVE": "",
  "KABUSAPI_PASSWORD_TEST": "",
  "KABUSAPI_ONETIME_TOKEN": "",
  "KABUPLUS_ID": "",
  "KABUPLUS_PASSWORD": ""
}
 """)
