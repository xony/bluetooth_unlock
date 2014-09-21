# INSTALLATION
### we require subprocess, python-bluez and optionally python-daemon

`sudo apt-get install python-pip python-bluez`
`sudo pip install subprocess.run`


# CONFIG

### choose the config.py appropriate to your setup / modify it. You will need to fill in your username in 'userstr' at the very least.
`cp config.py_gnome3 config.py`

### now set your phone into discoverable mode for bluetooth, use the script to update known_clients
`./get_strongest_id.py myphone`
### after this in known_clients your phone's bluetooth id should show up in JSON format

### you should now use your OS pairing capabilities to pair yourself with your phone

### now you can start the bluetooth unlock script
`sudo ./bluetooth_unlock.py`
### to start this permantly add the script to rc.local, you may have to set the filepaths absolute
