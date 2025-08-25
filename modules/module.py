from abc import ABC, abstractmethod
from pyjoystick.sdl2 import Key
from pynput.keyboard import Controller
import json


class Module(ABC):
    def __init__(self, keyboard: Controller, name):
        self.name = name
        self.keyboard = keyboard
        self.options = {}
        self.mappings = {}

    @abstractmethod
    def load(self) -> bool:
        self._log("loading")
        self._load_config()
        return True

    @abstractmethod
    def unload(self) -> bool:
        self._log("unloading")
        return True

    @abstractmethod
    def on_key(self, _: Key):
        pass

    def _get_mapped_key(self, key: Key, map_button_release: bool = False):
        if not (mapping := self.mappings.get(key.keytype)):
            return None

        if key.keytype == Key.KeyTypes.HAT:
            return mapping.get(key.value)

        if key.keytype == Key.KeyTypes.BUTTON and key.value == 0 and not map_button_release:
            return None

        return mapping.get(key.number)

    def _load_config(self):
        try:
            with open("data/modules.json", "r") as modules_file:
                config = json.load(modules_file)[self.name]
                self.options.update(config.get("options", {}))
                self.mappings.update(config.get("mappings", {}))
                self._log("config loaded successfully")
        except Exception:
            self._log(f"failed to load config")

    def _log(self, message: str):
        print(f"module-{self.name}: {message}")
