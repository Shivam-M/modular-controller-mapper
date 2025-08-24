from modules import MODULE_CLASSES
from modules.module import Module
from modules.module_dummy import Dummy
from pyjoystick.sdl2 import Key, Joystick, run_event_loop
from pynput.keyboard import Controller
from threading import Thread
from time import sleep
import os
import json
import sdl2


CONFIG_FILE = os.getenv("MAPPER_CONFIG_FILE", "data/config.json")
DEFAULT_CONFIG = {
    "quiet": False,
    "ignore-multiple-buttons": True,
    "haptic-feedback": True,
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
        self.haptic = None
        self.pressed_buttons = set()

    def configure(self, config_file=CONFIG_FILE):
        try:
            with open(config_file, "r") as config:
                self.config.update(json.load(config))
        except FileNotFoundError:
            print(f"warning: config file '{config_file}' does not exist - using defaults")

    def register(self, controller: Joystick):
        sdl2.SDL_Init(sdl2.SDL_INIT_JOYSTICK | sdl2.SDL_INIT_HAPTIC)
        if joystick := sdl2.SDL_JoystickOpen(0):
            haptic = sdl2.SDL_HapticOpenFromJoystick(joystick)
            if sdl2.SDL_HapticRumbleInit(haptic) == 0:
                self.haptic = haptic
                self._log("haptics enabled")

        self.vibrate(delay=0)
        self._log(f"controller: registered {controller}")

    def unregister(self, controller: Joystick):
        self.haptic = None
        self._log(f"controller: unregistered {controller}")

    def callback(self, key: Key):
        # self._log(f"key: {key.keytype=} {key.number=} {key.value=}")
        if key.keytype == Key.KeyTypes.BUTTON:
            self.pressed_buttons.add(key.number) if key.value else self.pressed_buttons.discard(key.number)

        if set(self.config["switch-shortcut"]).issubset(self.pressed_buttons):
            self._log("module: switching after triggering shortcut")
            self.pressed_buttons.clear()
            self.switch_module()
            return

        if key.keytype == Key.KeyTypes.BUTTON and len(self.pressed_buttons) > 1 and self.config["ignore-multiple-buttons"]:
            self._log(f"callback: ignoring button {key.number} because {self.pressed_buttons} are pressed")
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

    def switch_module(self, module: Module = None):
        self.current_module.unload()
        self.current_module = module if module else self._get_next_module()
        if not self.current_module.load():
            print(f"error: failed to load module '{self.current_module.name}'")

    def vibrate(self, strength: float = 0.5, duration: int = 500, count: int = 1, delay: float = 0.5):
        def _vibrate():
             for _ in range(count):
                sleep(delay)
                sdl2.SDL_HapticRumblePlay(self.haptic, strength, duration)

        if self.haptic and self.config["haptic-feedback"]:
            Thread(target=_vibrate, daemon=True).start()

    def _get_next_module(self):
        next_index = (self.modules.index(self.current_module) + 1) % len(self.modules)
        next_module = self.modules[next_index]
        if self.config["modules"]["skip-dummy-cycle"] and isinstance(next_module, Dummy):
            next_index = (next_index + 1) % len(self.modules)
            next_module = self.modules[next_index]
        self.vibrate(0.9, 100, next_index + 1, 0.25)
        return next_module

    def _log(self, message: str):
        if not self.config.get("quiet"):
            print(message)


if __name__ == "__main__":
    core = Core()
    core.configure()
    core.add_modules_from_list()
    # core.switch_module()
    run_event_loop(core.register, core.unregister, core.callback)
