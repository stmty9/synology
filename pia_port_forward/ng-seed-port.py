#!/usr/bin/env python3

import base64  # decoding payload to get the port
import json  # reading output from pia
import os  # making curl and transmission calls
import sys  # reading args
import time  # sleep after port assign before testing it
from datetime import datetime, timedelta  # reading/writing expiration dates
import logging as log

'''
  See README..md
'''

log.basicConfig(format='[%(asctime)s] [%(levelname)-5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level=log.DEBUG)

if len(sys.argv) != 2:
    log.error('ERROR: Please pass in the conf file as the only argument.')
    log.error('Example:\n\tpython3 ng-seed-port.py ng-seed-port.json\n\t./ng-seed-port.py ng-seed-port.json')
    log.error('Current input: {}'.format(sys.argv))
    exit(1)

# This is the date format for the expiration dates in the config
# BEWARE OF CHANGING THIS
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

def _error(message: str):
    log.error(message)
    exit(1)

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
    log.debug('Reading config file: {}'.format(CONFIG_FILE))
    with open(CONFIG_FILE, 'r') as json_file:
        config.update(json.load(json_file))

def write_config():
    log.debug('Updating config')
    # remove None values
    writeable = {k:v for k,v in config.items() if v is not None}
    with open(CONFIG_FILE, 'w') as outfile:
        json.dump(writeable, outfile, indent=2)


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
            log.info('Attempting again.')
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
            log.info('Using Existing token')
            return
        cmd = 'curl -sk -u {user}:{pwd} "https://10.0.0.1/authv3/generateToken"'.format(user=config['user'], pwd=config['password'])
        log.info('Generating token')
        log.debug(cmd)
        result = os.popen(cmd).read()
        j = str_to_json(result)
        token = j['token']
        log.debug(token)
        config['token'] = token
        # auth token lasts for 24hrs
        config['token_expiration'] = from_time(datetime.now() + timedelta(days=1))
    
    def find_port(self) -> None:
        if not is_expired(config['port_expiration']) and not is_expired(config['port_renew_by']):
            log.info('Using Existing port')
            return
        cmd = 'curl -skG --data-urlencode "token={token}" "https://{ip}:19999/getSignature"'.format(ip=self.local, token=config['token'])
        log.info('Generating signature') 
        log.debug(cmd)
        result = os.popen(cmd).read()
        log.debug(result)
        j = str_to_json(result)
        if j['status'] != 'OK':
            _error(j)

        # now we need to pull the data from the response
        config['payload'] = j['payload']
        config['signature'] = j['signature']
        payload = str_to_json(base64.b64decode(j['payload']))
        config['port'] = payload['port']
        log.debug('Port: {}'.format(config['port']))

        # port lasts for 2 months. 58 days should work for dumb February?
        config['port_expiration'] = from_time(datetime.now() + timedelta(days=58))
        self.has_new_port = True

    def bind_port(self) -> bool:
        cmd = 'curl -skG --data-urlencode "payload={payload}" --data-urlencode "signature={signature}" "https://{ip}:19999/bindPort"'.format(
            payload=config['payload'], signature=config['signature'], ip=self.local
        )
        log.info('Binding port')
        result = str_to_json(os.popen(cmd).read())
        if result['status'] != 'OK':
            log.debug('Error binding port: {}\n{}'.format(result['message'], cmd))
            return False
        log.info(result['message'])
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
        log.info('Updating transmission to use port: {}'.format(config['port']))
        cmd = '{trx} -n {user}:{password} -p {port}'.format(
            trx=self.cfg['remote'], user=self.cfg['username'], password=self.cfg['password'], port=config['port']
        )
        log.debug(cmd)
        result = os.popen(cmd).read()
        if '"success"' not in result:
            _error(result)

    def test_seed_port(self):
        log.info('Testing port')
        cmd = '{trx} -n {user}:{password} -pt'.format(
            trx=self.cfg['remote'], user=self.cfg['username'], password=self.cfg['password']
        )
        # give it time to update - sometimes it needed a slight delay
        log.debug('Sleeping for {}s'.format(self.cfg['port_test_delay']))
        time.sleep(self.cfg['port_test_delay'])
        log.debug(cmd)
        result = os.popen(cmd).read()
        if 'Yes' not in result:
            _error(result)
        log.info('Port bound successfully')


def get_consumers() -> list:
    consumers = []
    if 'transmission' in config:
        consumers.append(TransmissionConsumer())
    
    return filter(lambda consumer: issubclass(consumer.__class__, PortChangeConsumer), consumers)

def main():
    read_config()
    pia = PIAMeta()
    if pia.has_new_port:
        log.debug('New port detected. Updating consumers!')
        for c in get_consumers():
            c.consume()
    write_config()

if __name__ == '__main__':
    main()
