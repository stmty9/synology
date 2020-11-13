#!/usr/bin/env python3

import base64  # decoding payload to get the port
import configparser  # parsing the conf file
import json  # reading output from pia
import os  # making curl and transmission calls
import sys  # reading args
import time  # sleep after port assign before testing it
from datetime import datetime, timedelta  # storing expiration dates and logging

'''
  See README..md
'''

if len(sys.argv) != 2:
    print('ERROR: Please pass in the conf file as the only argument.')
    print('Example:\n\tpython3 ng-seed-port.py ng-seed-port.conf\n\t./ng-seed-port.py ng-seed-port.conf')
    print('Current input: {}'.format(sys.argv))
    exit(1)

DEBUG = False
DATE_FORMAT = '%Y-%m-%d %H%M'

# CONF file to store data to keep between runs
# I store it relative to the script in ng-seed-port.conf
CONF = sys.argv[1]
context = {
    'user': None,
    'password': None,
    'token': None,
    'token_expiration': None,
    'port': None,
    'port_expiration': None,
    'port_renew_by': None,
    'payload': None,
    'signature': None,
    'trx_remote': None,
    'trx_user': None,
    'trx_password': None,
    'trx_port_test_delay': 5
}
parser = configparser.ConfigParser()

# this is the local IP of the 'meta' server when already connected
local = os.popen('ip route | head -1 | grep tun | awk \'{ print $3 }\'').read().strip()


def _print(message: str):
    print('[{dt}] {msg}'.format(dt=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg=message))


def _error(message: str):
    _print('> ERROR < {}'.format(message))
    exit(1)


def _log(info: str = None, debug: str = None):
    if info is not None:
        _print(info)
    if DEBUG and debug is not None:
        _print('DEBUG: {}'.format(debug))


def str_to_json(txt: str) -> dict:
    res = None
    try:
        res = json.loads(txt)
    except BaseException as e:
        _error('Could not convert to json:\n{}'.format(txt))
    return res


def from_time(dt: datetime) -> str:
    return datetime.strftime(dt, DATE_FORMAT)


def to_time(dt: str) -> datetime:
    return datetime.strptime(dt, DATE_FORMAT)


def is_expired(dt: str) -> bool:
    return True if dt is None else to_time(dt) <= datetime.now()


def read_config():
    # _log(debug='Reading config file: {}'.format(CONF))
    parser.read(CONF)

    cfg = parser['DEFAULT']
    for key in context.keys():
        if key in cfg:
            context[key] = cfg[key]
    _log(debug='Using config: {}'.format(context))


def write_config():
    # _log(debug='Writing config file: {}'.format(CONF))
    for key in context.keys():
        if key is not None:
            parser.set('DEFAULT', key, str(context[key]))

    with open(CONF, 'w') as f:
        parser.write(f)


def get_token() -> bool:
    if not is_expired(context['token_expiration']):
        _log('Using Existing token')
        return False
    cmd = 'curl -sk -u {user}:{pwd} "https://10.0.0.1/authv3/generateToken"'.format(user=context['user'], pwd=context['password'])
    _log('Generating token', cmd)
    result = os.popen(cmd).read()
    j = str_to_json(result)
    token = j['token']
    _log(None, token)
    context['token'] = token
    context['token_expiration'] = from_time(datetime.now() + timedelta(days=1))  # auth token lasts for 24hrs
    return True


def get_port() -> bool:
    if not is_expired(context['port_expiration']) and not is_expired(context['port_renew_by']):
        _log('Using Existing port')
        return False
    cmd = 'curl -skG --data-urlencode "token={token}" "https://{ip}:19999/getSignature"'.format(ip=local, token=context['token'])
    _log('Generating signature', cmd)
    result = os.popen(cmd).read()
    _log(None, result)
    j = str_to_json(result)
    if j['status'] != 'OK':
        _error(j)

    # now we need to pull the data from the response
    context['payload'] = j['payload']
    context['signature'] = j['signature']
    payload = str_to_json(base64.b64decode(j['payload']))
    context['port'] = payload['port']
    context['port_expiration'] = from_time(
        datetime.now() + timedelta(days=58))  # port lasts for 2 months. 58 days should work for dumb February?
    return True


def bind_port() -> bool:
    cmd = 'curl -skG --data-urlencode "payload={payload}" --data-urlencode "signature={signature}" "https://{ip}:19999/bindPort"'.format(
        payload=context['payload'], signature=context['signature'], ip=local
    )
    _log('Binding port')
    result = str_to_json(os.popen(cmd).read())
    if result['status'] != 'OK':
        _error('Error binding port: {}\n{}'.format(result['message'], cmd))
    _log(result['message'])
    context['port_renew_by'] = from_time(datetime.now() + timedelta(minutes=16))  # give us 16m since this runs every 15m
    return True


def update_trx_seed_port():
    _log('Updating transmission to use port: {}'.format(context['port']))
    cmd = '{trx} -n {user}:{password} -p {port}'.format(
        trx=context['trx_remote'], user=context['trx_user'], password=context['trx_password'], port=context['port']
    )
    _log(debug=cmd)
    result = os.popen(cmd).read()
    if '"success"' not in result:
        _error(result)

    # now let's test to see that it is open
    _log('Testing port')
    cmd = '{trx} -n {user}:{password} -pt'.format(
        trx=context['trx_remote'], user=context['trx_user'], password=context['trx_password']
    )
    # give it time to update - sometimes it needed a slight delay
    _log(debug='Sleeping for {}s'.format(context['trx_port_test_delay']))
    time.sleep(int(context['trx_port_test_delay']))
    _log(debug=cmd)
    result = os.popen(cmd).read()
    if 'Yes' not in result:
        _error(result)
    _log('Port bound successfully')


def main():
    read_config()
    get_token()
    is_fresh_port = get_port()
    bind_port()
    # I write the config first in case updating fails.
    write_config()
    if is_fresh_port:
        update_trx_seed_port()


if __name__ == '__main__':
    main()
