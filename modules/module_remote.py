from modules.module import Module
from pyjoystick.sdl2 import Key
from pynput.keyboard import Controller
from aiowebostv import WebOsClient
import time
import asyncio
import json
import threading


DEFAULT_OPTIONS = {
    "disconnect-on-unload": True,
    "host": "192.168.1.1",
    "key-file": "data/webos-auth-key.json"
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
    }
}

class Remote(Module):
    def __init__(self, keyboard: Controller):
        super().__init__(keyboard, "remote")
        self.mappings = DEFAULT_MAPPINGS
        self.options = DEFAULT_OPTIONS
        self.client = None
        self.connected = False
        self.loop = None
        self.loop_thread = None
        self._shutdown_event = threading.Event()

    def load(self) -> bool:
        super().load()

        if self.client and self.connected:
            self._log("already connected")
            return True

        try:
            self._start_event_loop()
            time.sleep(0.25) 

            future = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
            success = future.result(timeout=10)

            if success and self.client:
                self.connected = True
                return True
        except Exception as e:
            self._log(f"remote connection failed: {e}")
            self.connected = False
            return False

    def unload(self) -> bool:
        super().unload()

        if not self.options.get("disconnect-on-unload", True):
            return True

        if self.client and self.connected:
            try:
                future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
                future.result(timeout=5)
                self._log("disconnected successfully")
            except Exception as e:
                self._log(f"error during disconnect: {e}")
                return False

        self._stop_event_loop()

        self.client = None
        self.connected = False
        return True

    def on_key(self, key: Key):
        if not self.connected or not self.client:
            return

        if mapped_key := self._get_mapped_key(key):
            self._send_command(mapped_key)
    
    def _load_key(self) -> str | None:
        try:
            with open(self.options["key-file"], "r") as key_file:
                if key := json.load(key_file).get("key"):
                    self._log(f"found stored key: {key[:8]}...")
                    return key
        except Exception:
            self._log(f"no existing key file found")

    def _save_key(self, key):
        with open(self.options["key-file"], "w") as key_file:
            json.dump({"key": key}, key_file, indent=4)
            self._log("saved new authentication key")

    def _start_event_loop(self):
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
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
            future = asyncio.run_coroutine_threadsafe(self.client.button(command), self.loop)
            future.result(timeout=5)
            self._log(f"sent command: {command}")
        except asyncio.TimeoutError:
            self._log(f"timeout sending command: {command}")
        except Exception as e:
            self._log(f"failed to send command {command}: {e}")

    async def _connect(self) -> bool:
        try:
            self.client = WebOsClient(self.options["host"])
            self._log(f"created webOS client")

            if stored_key := self._load_key():
                self.client.client_key = stored_key

            self._log(f"connecting to {self.options['host']}")
            await self.client.connect()
            self._log("connected successfully")

            system_info = await self.client.get_system_info()
            self._log(f"confirmed connection to TV: {system_info.get('modelName', 'unnkown')}")

            if self.client.client_key != stored_key:
                self._save_key(self.client.client_key)

            return True

        except Exception as e:
            self._log(f"connection error: {e}")
            self.client = None
            return False
