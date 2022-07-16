"""
Create credentials.json under $HOME/.kabuto.
Write and fill the information in the following format:
* DONT UPLOAD/SHARE THE CREDENTIAL FILE WITH ANYONE FOR ANY REASON
* Do `chmod 600 $HOME/.kabuto/credentials.json` to make your file private
* KABUS_API_ONETIME_TOKEN is optional (but the key should be there)
{
  "KABUCOM_PASSWORD": "",
  "KABUSAPI_HOST": "xxx.xxx.xxx.xxx",
  "KABUSAPI_HOST_LIVE": "xxx.xxx.xxx.xxx:port/live",
  "KABUSAPI_HOST_TEST": "xxx.xxx.xxx.xxx:port/test",
  "KABUSAPI_PASSWORD_LIVE": "",
  "KABUSAPI_PASSWORD_TEST": "",
  "KABUSAPI_ONETIME_TOKEN": ""
}
See the comment in class Credential for mode detail on each property.
"""
import json
import os
from dataclasses import dataclass


@dataclass
class Credential:
    # Password you use to enter kabu.com
    kabucom_password: str
    # Local IP address with port of the Windows PC running kabu STATION app.
    host_ipaddr: str
    # IP address with port and live/test domain (e.g., ipaddr/live), as defined by NGINX on Windows
    # NOTE: This test API is not really "tested" much on our project yet...
    host_live: str
    host_test: str
    # Password you set on kabu STATION app (the API setting panel).
    # These are required to acquire the onetime access token.
    password_live: str
    password_test: str
    # This is not used for bot.
    # If you access to kabu STATION without using bot, say testing some function,
    # get onetime token in some way and write it in the JSON.
    onetime_token: str


try:
    with open(f'{os.environ["HOME"]}/.kabuto/credentials.json') as f:
        # CREDENTIAL_RAW can be used to hold any credential information even unrelated to the bot,
        # for example, the API credential of a service you use for fundamental analysis etc.
        # However, there are some properties necessary to be defined for KABUTO_CREDENTIAL.
        CREDENTIAL_RAW = json.load(f)

    KABUTO_CREDENTIAL = Credential(
        kabucom_password=CREDENTIAL_RAW['KABUCOM_PASSWORD'],
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
  "KABUSAPI_HOST": "xxx.xxx.xxx.xxx",
  "KABUSAPI_HOST_LIVE": "xxx.xxx.xxx.xxx:port/live",
  "KABUSAPI_HOST_TEST": "xxx.xxx.xxx.xxx:port/live",
  "KABUSAPI_PASSWORD_LIVE": "",
  "KABUSAPI_PASSWORD_TEST": "",
  "KABUSAPI_ONETIME_TOKEN": "",
}
 """)
