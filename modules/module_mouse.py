from modules.module import Module
from pyjoystick.sdl2 import Key
from pynput.keyboard import Controller, Key as KBKey
from pynput.mouse import Button
from pynput import mouse
from threading import Thread
import time
import math


MOUSE_X = 1
MOUSE_Y = 2
MOUSE_THROTTLE = 3
MOUSE_BOOST = 4
SCROLL_X = 5
SCROLL_Y = 6

DEFAULT_MAPPINGS = {
    Key.KeyTypes.HAT: {
        Key.HAT_UP:    KBKey.up,
        Key.HAT_DOWN:  KBKey.down,
        Key.HAT_LEFT:  KBKey.left,
        Key.HAT_RIGHT: KBKey.right
    },
    Key.KeyTypes.BUTTON: {
        0: Button.left,   # A
        1: Button.right,  # B
        2: Button.middle, # X
        3: KBKey.enter,   # Y
        4: None,          # L-BUMPER
        5: None,          # R-BUMPER
        6: None,          # VIEW / BACK
        7: None,          # MENU / START
        8: None,          # L-STICK
        9: None,          # R-STICK
    },
    Key.KeyTypes.AXIS: {
        0: MOUSE_X,        # L-STICK [X]
        1: MOUSE_Y,        # L-STICK [Y]
        2: MOUSE_THROTTLE, # L-TRIGGER
        3: SCROLL_X,       # R-STICK [X]
        4: SCROLL_Y,       # R-STICK [Y]
        5: MOUSE_BOOST,    # R-TRIGGER
    }
}

DEFAULT_OPTIONS = {
    "sensitivity": 1.0,
    "acceleration": 5.0,
    "deadzone": 0.15,
    "invert-horizontal": False,
    "scroll-sensitivity": 1.0,
    "movement-update-rate": 120
}

class Mouse(Module):
    def __init__(self, keyboard: Controller):
        super().__init__(keyboard, "mouse")
        self.mappings = DEFAULT_MAPPINGS
        self.options = DEFAULT_OPTIONS.copy()
        self.mouse = mouse.Controller()
        self.mouse_multiplier = 1.0
        self.mouse_speed = [0.0, 0.0]
        self.scroll_speed = [0.0, 0.0]
        self.movement_thread = None
        self.movement_active = False
        self.pressed_buttons = set()

        self._reset_mouse()

    def load(self) -> bool:
        super().load()
        self._reset_mouse()
        self._start_movement_thread()
        return True

    def unload(self) -> bool:
        super().unload()
        self._reset_mouse()
        self._stop_movement_thread()
        return True

    def on_key(self, key: Key):
        if not (action := self._get_mapped_key(key, map_button_release=True)):
            return

        if isinstance(action, Button):
            self._handle_mouse_button(key, action)
        elif key.keytype == Key.KeyTypes.AXIS:
            self._handle_axis(action, key.value)
        else:
            self._log(f"pressing {action}")
            self.keyboard.press(action)

    def _handle_mouse_button(self, key: Key, button: Button):
        now_pressed = key.value >= self.options["deadzone"]
        currently_pressed = key.number in self.pressed_buttons

        if now_pressed and not currently_pressed:
            self._log(f"pressing {button}")
            self.mouse.press(button)
            self.pressed_buttons.add(key.number)
        elif not now_pressed and currently_pressed:
            self._log(f"releasing {button}")
            self.mouse.release(button)
            self.pressed_buttons.remove(key.number)

    def _handle_axis(self, action, value):
        if abs(value) < self.options["deadzone"]:
            value = 0.0

        # match-case >= python 3.10...
        if action == MOUSE_X:
            self.mouse_speed[0] = value
        elif action == MOUSE_Y:
            self.mouse_speed[1] = -value if self.options["invert-horizontal"] else value
        elif action == SCROLL_X:
            self.scroll_speed[0] = value * self.options["scroll-sensitivity"]
        elif action == SCROLL_Y:
            self.scroll_speed[1] = -value * self.options["scroll-sensitivity"]
        elif action in (MOUSE_THROTTLE, MOUSE_BOOST):
            self.mouse_multiplier = 1 + (value * (1 if action == MOUSE_BOOST else -1))

    def _start_movement_thread(self):
        self.movement_active = True
        self.movement_thread = Thread(target=self._movement_loop, daemon=True)
        self.movement_thread.start()
        self._log("started mouse movement thread")

    def _stop_movement_thread(self):
        self.movement_active = False
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join(timeout=0.1)
        self._log("stopped mouse movement thread")

    def _movement_loop(self):
        update_rate = 1.0 / self.options["movement-update-rate"]
        while self.movement_active:
            self._update_mouse_position()
            time.sleep(update_rate)

    def _update_mouse_position(self):
        if (speed := math.hypot(*self.mouse_speed)) > 0:
            acceleration = 1.0 + (speed * (self.options["acceleration"] - 1.0)) * self.options["sensitivity"] * self.mouse_multiplier
            distance = [self.mouse_speed[0] * acceleration, self.mouse_speed[1] * acceleration]
            self.mouse.move(*distance)

        if any(self.scroll_speed):
            self.mouse.scroll(*self.scroll_speed)

    def _reset_mouse(self):
        for button in (Button.left, Button.middle, Button.right):
            if button in self.pressed_buttons:
                self.mouse.release(button)

        self.pressed_buttons.clear()
        self.mouse_velocity = [0.0, 0.0]
        self.scroll_velocity = [0.0, 0.0]
        self.mouse_multiplier = 1.0
