# PIA Next Gen Port Forwarding

This is designed to grab the port and set the port in transmission. This could easily be adapted to work as a shell script as well.

This script does the following things:
1. Fetch an auth token
1. Acquire Port from PIA
1. Renews port
1. Updates transmission with the new port (and verifies the port is open)

It will honor the following TTLs:
- Auth tokens are used for 24hrs
- Ports last for 2 months (set at 58 days)
- The port should be renewed every 16 minutes (so it can be used on a task running every 15m)

## Quick Start
1. You must have python3 installed. There should be no extra modules required.
1. You must already be connected to a PIA VPN Server that supports Port Forwarding
    - Sometimes it might take a little after being connected for these calls to work.
1. Setup your config file. 
    1. Copy `cp config.json.sample config.json`
    1. Update username and password in `config.json`
        - configure a Port Change Consumer (see below)
1. Run it `./ng-seed-port.py config.json`

#### Notes
- Everything in the `config` variable will be written to the `json` file dynamically. You can add or remove params to this if you want to
 store them.
- If you want more verbose output, change the log level in the script

## Config File
The only necessary fields to generate the seed port are your PIA username and password. You also need to configure a Port Change Consumer if you want to do anything with the port after it's setup.

The script will populate evrything else it needs in the config file after the first run, so make sure the file is writeable.
```
{
    "user": "pia_username",
    "password": "pia_password"
}
```

## Port Change Consumers
All configured Port Change Consumers will get called when the port changes. They have their own sections in the json config used to enable them.

### Transmission
This will update transmission with the new port and verify it is open

```
{
    "user": "pia_username",
    "password": "pia_password",
    "transmission": {
        "remote": "/usr/local/transmission/bin/transmission-remote",
        "username": "",
        "password": "",
        "port_test_delay": 5
    }
}
```
- `remote`: The path to the `transmission-remote` command. The default shown is the path to it when installed via the synology package manager for me
- `port_test_delay`: The delay (seconds) after updating the port before testing it. This is necessary to make sure transmission has had enough time to register the port

### How to Add a new Consumer
1. Create a new class extending `PortChangeConsumer` with a `consume` function.
2. Update `def get_consumers() -> list:` with your config key


## References
[PIA - FOSS] - Sample code of how to automate connecting via OpenVPN and Wireguard. This
code was referenced heavily in this solution

[PIA Server List] - This is a JSON dump of al the regions with a server from each
 regions. You can use this to find port forwarding servers.
 
[PIA Connection Issues] - I had my connection drop a lot using udp/1198, so I switched to udp/53. We will see if that works


[PIA - FOSS]: https://github.com/pia-foss/manual-connections
[PIA Server List]:https://serverlist.piaservers.net/vpninfo/servers/v4 
[PIA Connection Issues]: https://www.privateinternetaccess.com/helpdesk/kb/articles/i-have-trouble-connecting-or-the-connection-drops-frequently-changing-ports-4