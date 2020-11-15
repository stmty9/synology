#!/usr/bin/env python3

import base64  # decoding payload to get the port
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
    print('Example:\n\tpython3 ng-seed-port.py ng-seed-port.json\n\t./ng-seed-port.py ng-seed-port.json')
    print('Current input: {}'.format(sys.argv))
    exit(1)

DEBUG = False
DATE_FORMAT = '%Y-%m-%d %H%M'

# CONFIG_FILE to store data to keep between runs
CONFIG_FILE = sys.argv[1]

# this config is the default and is overriden by the contents of the CONFIG_FILE
config = {
    'user': None,
    'password': None,
    'token': None,
    'token_expiration': None,
    'port': None,
    'port_expiration': None,
    'port_renew_by': None,
    'payload': None,
    'signature': None
}

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
    except BaseException:
        _error('Could not convert to json:\n{}'.format(txt))
    return res


def from_time(dt: datetime) -> str:
    return datetime.strftime(dt, DATE_FORMAT)


def to_time(dt: str) -> datetime:
    return datetime.strptime(dt, DATE_FORMAT)


def is_expired(dt: str) -> bool:
    return True if dt is None else to_time(dt) <= datetime.now()


def read_config():
    _log(debug='Reading config file: {}'.format(CONFIG_FILE))
    with open(CONFIG_FILE, 'r') as json_file:
        config.update(json.load(json_file))

def write_config():
    _log(debug='Updating config')
    # remove None values
    writeable = {k:v for k,v in config.items() if v is not None}
    with open(CONFIG_FILE, 'w') as outfile:
        json.dump(writeable, outfile)


class PIAMeta:
    # this is the local IP of the 'meta' server when already connected
    local = None
    has_new_port = False

    def __init__(self):
        self.local = os.popen('ip route | head -1 | grep tun | awk \'{ print $3 }\'').read().strip()
        if self.local is None or self.local == '':
            _error('It does not look like you are connected to PIA!')
        
        self.find_token()
        self.find_port()
        success = self.bind_port()
        if not success:
            _log('Attempting again.')
            self.invalidate_exipirations()
            self.find_token()
            self.find_port()
            success = self.bind_port()
            if not success:
                _error('2 attempts failed, exiting.')

    def invalidate_exipirations(self) -> None:
        config['token_expiration'] = None
        config['port_expiration'] = None
        config['port_renew_by'] = None

    def find_token(self) -> None:
        if not is_expired(config['token_expiration']):
            _log('Using Existing token')
            return
        cmd = 'curl -sk -u {user}:{pwd} "https://10.0.0.1/authv3/generateToken"'.format(user=config['user'], pwd=config['password'])
        _log('Generating token', cmd)
        result = os.popen(cmd).read()
        j = str_to_json(result)
        token = j['token']
        _log(None, token)
        config['token'] = token
        # auth token lasts for 24hrs
        config['token_expiration'] = from_time(datetime.now() + timedelta(days=1))
    
    def find_port(self) -> None:
        if not is_expired(config['port_expiration']) and not is_expired(config['port_renew_by']):
            _log('Using Existing port')
            return
        cmd = 'curl -skG --data-urlencode "token={token}" "https://{ip}:19999/getSignature"'.format(ip=self.local, token=config['token'])
        _log('Generating signature', cmd)
        result = os.popen(cmd).read()
        _log(None, result)
        j = str_to_json(result)
        if j['status'] != 'OK':
            _error(j)

        # now we need to pull the data from the response
        config['payload'] = j['payload']
        config['signature'] = j['signature']
        payload = str_to_json(base64.b64decode(j['payload']))
        config['port'] = payload['port']

        # port lasts for 2 months. 58 days should work for dumb February?
        config['port_expiration'] = from_time(datetime.now() + timedelta(days=58))
        self.has_new_port = True

    def bind_port(self) -> bool:
        cmd = 'curl -skG --data-urlencode "payload={payload}" --data-urlencode "signature={signature}" "https://{ip}:19999/bindPort"'.format(
            payload=config['payload'], signature=config['signature'], ip=self.local
        )
        _log('Binding port')
        result = str_to_json(os.popen(cmd).read())
        if result['status'] != 'OK':
            _log(debug='Error binding port: {}\n{}'.format(result['message'], cmd))
            return False
        _log(result['message'])
        config['port_renew_by'] = from_time(datetime.now() + timedelta(minutes=16))  # give us 16m since this runs every 15m
        return True


class PortChangeConsumer:
    def consume(self) -> None:
        _error('Please override `update()`')


class TransmissionConsumer(PortChangeConsumer):
    cfg:dict = None

    def __init__(self):
        self.cfg = config['transmission']
        if 'port_test_delay' not in self.cfg:
            self.cfg['port_test_delay'] = 5 

    def consume(self) -> None:
        self.update_seed_port()
        self.test_seed_port()

    def update_seed_port(self):
        _log('Updating transmission to use port: {}'.format(config['port']))
        cmd = '{trx} -n {user}:{password} -p {port}'.format(
            trx=self.cfg['remote'], user=self.cfg['username'], password=self.cfg['password'], port=config['port']
        )
        _log(debug=cmd)
        result = os.popen(cmd).read()
        if '"success"' not in result:
            _error(result)

    def test_seed_port(self):
        _log('Testing port')
        cmd = '{trx} -n {user}:{password} -pt'.format(
            trx=self.cfg['remote'], user=self.cfg['username'], password=self.cfg['password']
        )
        # give it time to update - sometimes it needed a slight delay
        _log(debug='Sleeping for {}s'.format(self.cfg['port_test_delay']))
        time.sleep(self.cfg['port_test_delay'])
        _log(debug=cmd)
        result = os.popen(cmd).read()
        if 'Yes' not in result:
            _error(result)
        _log('Port bound successfully')


def get_consumers() -> list:
    consumers = []
    if 'transmission' in config:
        consumers.append(TransmissionConsumer())
    
    return filter(lambda consumer: type(consumer) is PortChangeConsumer, consumers)

def main():
    read_config()
    pia = PIAMeta()
    if pia.has_new_port:
        for c in get_consumers():
            c.consume()
    write_config()

if __name__ == '__main__':
    main()
