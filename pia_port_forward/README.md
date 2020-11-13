# Private Internet Access Next Gen Port Forwarding

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
1. Setup your conf file. 
    1. Copy `cp ng-seed-port.conf.sample ng-seed-port.conf`
    1. Populate all the values in `ng-seed-port.conf`
1. Run it `./ng-seed-port.py ng-seed-port.conf`
    - This is also how to call it in the Task Scheduler

- Everything in the `context` variable will be written to the `conf` file dynamically. You can add or remove params to this if you want to
 store them.
- If you want more verbose output, set the `DEBUG` property inside the script to `True`



## References
[PIA - FOSS](https://github.com/pia-foss/manual-connections) - Sample code of how to automate connecting via OpenVPN and Wireguard. This
code was referenced heavily in this solution

[PIA Server List](https://serverlist.piaservers.net/vpninfo/servers/v4) - This is a JSON dump of al the regions with a server from each
 regions. You can use this to find port forwarding servers.
