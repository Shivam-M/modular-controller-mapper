from modules import MODULE_CLASSES
from modules.module import Module
from modules.module_dummy import Dummy
from pyjoystick.sdl2 import Key, Joystick, run_event_loop
from pynput.keyboard import Controller
import json


CONFIG_FILE = "data/config.json"
DEFAULT_CONFIG = {
    "quiet": False,
    "ignore-multiple-buttons": True,
    "switch-shortcut": [4, 5, 8, 9],
    "modules": {
        "config": "data/modules.json",
        "directory": "modules/",
        "blacklisted": [],
        "initial": "dummy",
        "skip-dummy-cycle": False
    }
}

class Core:    
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.modules = [Dummy()]
        self.current_module = self.modules[0]
        self.keyboard = Controller()
        self.pressed_butons = set()

    def configure(self, config_file=CONFIG_FILE):
        try:
            with open(config_file, "r") as config:
                self.config.update(json.load(config))
        except FileNotFoundError:
            print(f"warning: config file '{config_file}' does not exist - using defaults")
    
    def register(self, controller: Joystick):
        self._log(f"controller: registered {controller}")

    def unregister(self, controller: Joystick):
        self._log(f"controller: unregistered {controller}")

    def callback(self, key: Key):
        # self._log(f"key: {key.keytype=} {key.number=} {key.value=}")
        if key.keytype == Key.KeyTypes.BUTTON:
            if key.value == 1:
                self.pressed_butons.add(key.number)
            elif key.value == 0:
                self.pressed_butons.discard(key.number)
        if set(self.config["switch-shortcut"]).issubset(self.pressed_butons):
            self._log("module: switching after triggering shortcut")
            self.pressed_butons.clear()
            self.switch_module()
            return
        if len(self.pressed_butons) > 1 and self.config["ignore-multiple-buttons"]:
            return
        if self.current_module:
            self.current_module.on_key(key)
    
    def add_modules_from_list(self):
        for module_class in MODULE_CLASSES:
            module_name = module_class.__name__.lower()
            if module_name in self.config["modules"]["blacklisted"]:
                self._log(f"module: skipping blacklisted '{module_name}'")
                continue
            self.add_module(module_class)

    def add_module(self, module_class):
        module = module_class(self.keyboard)
        self.modules.append(module)
        self._log(f"module: added '{module.name}'")
        if module.name == self.config["modules"]["initial"]:
            self._log(f"module: setting initial '{module.name}'")
            self.switch_module(module)

    def switch_module(self, module: Module=None):
        self.current_module.unload()

        if not module:
            current_index = self.modules.index(self.current_module)
            next_index = (current_index + 1) % len(self.modules)
            self.current_module = self.modules[next_index]
            if (self.current_module.name == "dummy" and
                self.config["modules"]["skip-dummy-cycle"]):
                next_index = (next_index + 1) % len(self.modules)
                self.current_module = self.modules[next_index]
        else:
            self.current_module = module

        if not self.current_module.load():
            print(f"error: failed to load module '{self.current_module.name}'")

    def _log(self, message: str):
        if not self.config.get("quiet"):
            print(message)


if __name__ == "__main__":
    core = Core()
    core.configure()
    core.add_modules_from_list()
    # core.switch_module()
    run_event_loop(core.register, core.unregister, core.callback)
