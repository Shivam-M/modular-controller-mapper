from modules.module import Module
from pyjoystick.sdl2 import Key
from pynput.keyboard import Controller
from aiowebostv import WebOsClient
from threading import Thread, Event
from getmac import get_mac_address
from wakeonlan import send_magic_packet
from time import sleep
import asyncio
import json


DEFAULT_OPTIONS = {
    "disconnect-on-unload": True,
    "host": "192.168.1.1",
    "secrets-file": "data/remote-secrets.json",
    "wake-on-lan": {
        "enabled": True,
        "sleep-after-wake": 25,
        "broadcast-address": "192.168.1.255"
    }
}

DEFAULT_MAPPINGS = {
    Key.KeyTypes.HAT: {
        Key.HAT_UP:    "UP",
        Key.HAT_DOWN:  "DOWN",
        Key.HAT_LEFT:  "LEFT",
        Key.HAT_RIGHT: "RIGHT"
    },
    Key.KeyTypes.BUTTON: {
        0: "ENTER",        # A
        1: "BACK",         # B
        2: "PLAY",         # X
        3: "PAUSE",        # Y
        4: "VOLUMEDOWN",   # L-BUMPER
        5: "VOLUMEUP",     # R-BUMPER
        6: "HOME",         # VIEW / BACK
        7: "MENU",         # MENU / START
        8: "INPUT_HUB",    # L-STICK
        9: "POWER"         # R-STICK
    }
}

DEFAULT_SECRETS = {
    "key": None,
    "mac-address": None
}

class Remote(Module):
    def __init__(self, keyboard: Controller):
        super().__init__(keyboard, "remote")
        self.mappings = DEFAULT_MAPPINGS
        self.options = DEFAULT_OPTIONS
        self.secrets = DEFAULT_SECRETS
        self.connected = False
        self.client = None
        self.loop = None
        self.loop_thread = None
        self._shutdown_event = Event()

    def load(self) -> bool:
        super().load()

        if self.client and self.connected:
            self._log("already connected")
            return True

        try:
            self._load_secrets()
            self._start_event_loop()
            sleep(0.25) 
            self.connected = asyncio.run_coroutine_threadsafe(self._connect(), self.loop).result(timeout=15)

            if self.connected and not self.secrets["mac-address"]:
                self._find_mac_address()
        except Exception as e:
            self._log(f"remote connection failed: {repr(e)}")
            self.connected = False

        return self.connected

    def unload(self) -> bool:
        super().unload()

        if self.options["disconnect-on-unload"] and self.client and self.connected:
            try:
                asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop).result(timeout=5)
                self._log("disconnected successfully")
            except Exception as e:
                self._log(f"error during disconnect: {repr(e)}")
                return False

        self._stop_event_loop()
        self.client = None
        self.connected = False
        return True

    def on_key(self, key: Key):
        mapped_key = self._get_mapped_key(key)
        if not self.connected and mapped_key == "POWER" and self.options["wake-on-lan"]["enabled"]:
            self._wake_on_lan()
        elif self.connected and self.client and mapped_key:
            self._send_command(mapped_key)

    def _load_secrets(self):
        try:
            with open(self.options["secrets-file"], "r") as secrets_file:
                self.secrets.update(json.load(secrets_file))
                if key := self.secrets["key"]:
                    self._log(f"found stored key: {key[:8]}...")
                if mac_address := self.secrets["mac-address"]:
                    self._log(f"found stored mac-address: {mac_address[:6]}...")
        except Exception as e:
            self._log(f"failed to load existing secrets file: {repr(e)}")

    def _save_secrets(self):
        try:
            with open(self.options["secrets-file"], "w") as secrets_file:
                json.dump(self.secrets, secrets_file, indent=4)
                self._log("saved secrets")
        except Exception as e:
            self._log(f"failed to save secrets to file '{self.options['secrets-file']}': {repr(e)}")

    def _start_event_loop(self):
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.loop_thread = Thread(target=run_loop, daemon=True)
        self.loop_thread.start()

    def _stop_event_loop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.loop_thread and self.loop_thread.is_alive():
            self.loop_thread.join(timeout=2)

    def _send_command(self, command: str):
        if not self.client or not self.connected:
            self._log("no client connection available")
            return

        try:
            asyncio.run_coroutine_threadsafe(self.client.button(command), self.loop).result(timeout=5)
            self._log(f"sent command: {command}")
        except asyncio.TimeoutError:
            self._log(f"timeout sending command: {command}")
        except Exception as e:
            self._log(f"failed to send command {command}: {repr(e)}")

    async def _connect(self) -> bool:
        try:
            self.client = WebOsClient(self.options["host"], client_key=self.secrets["key"])

            self._log(f"connecting to {self.options['host']}")
            await self.client.connect()
            self._log("connected successfully")

            system_info = await self.client.get_system_info()
            self._log(f"confirmed connection to TV: {system_info.get('modelName', 'unnkown')}")

            if self.client.client_key != self.secrets["key"]:
                self.secrets["key"] = self.client.client_key
                self._save_secrets()

            return True
        except Exception as e:
            self._log(f"connection error: {repr(e)}")
            self.client = None
            return False

    def _find_mac_address(self):
        try:
            if mac := get_mac_address(ip=self.options["host"]):
                self._log(f"found MAC address: {mac[:6]}...")
                self.secrets["mac-address"] = mac
                self._save_secrets()
            else:
                self._log("failed to find MAC address")
        except Exception as e:
            self._log(f"error finding MAC address: {repr(e)}")

    def _wake_on_lan(self):
        if not (mac_address := self.secrets["mac-address"]):
            self._log("no MAC address found to send WoL packet to")
            return
        try:
            broadcast_address = self.options["wake-on-lan"]["broadcast-address"]
            self._log(f"broadcasting WoL packet via {broadcast_address}")
            send_magic_packet(mac_address, ip_address=broadcast_address)

            wait_to_power_on = self.options["wake-on-lan"]["sleep-after-wake"]
            self._log(f"waiting {wait_to_power_on} seconds for the TV to power on")
            sleep(wait_to_power_on)

            self.unload()
            self.load()
        except Exception as e:
            self._log(f"failed to send WoL packet: {repr(e)}")
