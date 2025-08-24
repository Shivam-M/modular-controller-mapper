# Modular Controller Mapper

Allows programmable mapping of controller input through configurable 'modules' which can be cycled between using custom controller shortcuts.

----

### Installation (Python 3.8+)

`pip install -r requirements.txt`

### Usage

Run `core.py` and configure using `data/config.json`

#### `config.json`
```JSON
{
    "quiet": false,  // log verbosity
    "ignore-multiple-buttons": true,  // only allow one button to be pressed at a time
    "switch-shortcut": [4, 5, 8, 9],  // press these buttons to switch between modules
    "modules": {
        "config": "data/modules.json",  // config file for all modules
        "directory": "modules/",  // directory to search for module_*.py files (unused)
        "blacklisted": [],  // list of modules to skip adding
        "initial": "media",  // module to start with
        "skip-dummy-module": false  // skip dummy when cycling between modules
    }
}
```

### Built-in Modules

#### `module_media.py`
* Maps controller input to keyboard input
* Uses media keys for play/pause/volume control
* Loosely based on VLC shortcuts (speed, seek, volume, subtitles)

#### `module_remote.py`
* LG WebOS remote control using [aiowebostv](https://github.com/home-assistant-libs/aiowebostv) (wrapped in a thread)
* Requires you to accept the pairing request on the TV when first connecting
* Auth key is stored at `data/remote-secrets.json` by default but ideally should be moved elsewhere by changing `data/modules.json`
* If the initial connection is unsuccessful, a Wake-on-LAN packet is sent when the mapped `POWER` button is pressed
* The MAC address is resolved automatically or it can be manually set in `data/remote-secrets.json`

#### `module_dummy.py`
* Does nothing and acts as a 'disabled' state to put the controller in when switching through modules

#### `modules.json`

```JSON
{
    "dummy": {},
    "remote": {
        "mappings": {},  // custom mappings
        "options": {
            "disconnect-on-unload": true,  // disconnect from the TV when switching out of the module
            "host": "192.168.1.159",  // IP address of the TV
            "secrets-file": "data/remote-secrets.json",  // stores the auth token and MAC address (for WoL)
            "wake-on-lan": {
                "enabled": true,  // send a WoL packet if the 'POWER' button is pressed while disconnected
                "sleep-after-wake": 25,  // time in seconds to wait before connecting after sending the packet
                "broadcast-address": "192.168.1.255"
            }
        }
    },
    "media": {
        "mappings": {}
    },
}
```

### Creating New Modules

1. Create a `module_<name>.py` in the modules directory
2. Create an object inheriting from the abstract base class `Module`
3. Call the super constructor and pass in the name in lowercase
4. The following methods must be implemented:
    * `load(self)` - when switching into the module (call super to load config)
    * `unload(self)` - clean up when switching out of the module
    * `on_key(self, key: Key)` - called when a controller button has been pressed
5. **optional:** add the module to `modules.json` to support configurable mappings and options
    * custom mappings and options will be loaded into `self.mappings`/`self.options` (on top of any defaults)
6. Import the module in `modules/__init__.py` and add it to the `MODULE_CLASSES` list

### Reference

#### Xbox One Controller Button SDL Number Layout

```
 l-bumper (btn)                          r-bumper (btn)
   [   4   ]                               [   5   ]

 l-stick (btn)                             xy/ab (btn)
    ╔═════╗      view (btn)   menu (btn)       3
    ║  8  ║        [ 6 ]         [ 7 ]       2 □ 1
    ╚═════╝                                    0

      d-pad (hat)
       ┌───────┐                      r-stick (btn)
       │   1   │                        ╔═════╗
       │ 8 ● 2 │                        ║  9  ║
       │   4   │                        ╚═════╝
       └───────┘
```

### TODO

* Serialise mappings to use with `modules.json`
* *Safely* load module classes with importlib
* Register and repeat actions when buttons are held down
* Axis mappings with respect for deadzone values
