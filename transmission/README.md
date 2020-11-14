# Post Download Unrar

This is a script to run after transmission downloads to `unrar` the files if they need it. 

The devs at Radarr and Sonarr refuse to implement this themselves, so it needs to be implemented in Transmission.

There are two settings in the `settings.json` that need to be updated.
For those using the transmission package from the Synology Package Center, the settings file can be found here: `/var/packages/transmission
/target
/var/settings.json`
```
    "script-torrent-done-enabled": true,
    "script-torrent-done-filename": "/path/to/script/trx_unrar.sh",
```
