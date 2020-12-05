# Setting up the VPN with PIA

## 1. Download Necessary Files
Here are the [OVPN Files] from pia. These zips also contain the `.crt` and the `.pem` files. 

**These `.ovpn` files do not work out of the box on Synology**. Open the one you want to use with any text editor and change the line: `compress` to  `comp-lzo`

## 2. Create a VPN Profile
This has been verified against DSM 6.2.3-25426.

1. Login to DSM Web UI
1. Control Panel -> Network -> Network Interface
1. Create -> Create VPN Profile -> OpenVPN (via importing a .ovpn file)
1. Configre the VPN profile with your username, password and the following files. The Certificate Revocation List can be found under `Advanced`.
![screenshot]
1. On the next screen, check 'Use default gateay on remote network' and `Reconnect when the VPN connection is lost'

After you've configured and enabled the VPN Profile, ensure that the VPN Profile is at the top of the Service order (Manage -> Service Order)

[OVPN Files]: https://www.privateinternetaccess.com/helpdesk/kb/articles/where-can-i-find-your-ovpn-files
[screenshot]: ovpn_setup.png
