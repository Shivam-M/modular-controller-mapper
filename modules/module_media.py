from modules.module import Module
from pyjoystick.sdl2 import Key
from pynput.keyboard import Controller, KeyCode
from pynput.keyboard import Key as KBKey


DEFAULT_MAPPINGS = {
    Key.KeyTypes.HAT: {
        Key.HAT_UP:    KBKey.up,
        Key.HAT_DOWN:  KBKey.down,
        Key.HAT_LEFT:  KBKey.left,
        Key.HAT_RIGHT: KBKey.right
    },
    Key.KeyTypes.BUTTON: {
        0: KeyCode.from_char('G'),  # A
        3: KeyCode.from_char('H'),  # Y
        1: KeyCode.from_char(']'),  # B
        2: KeyCode.from_char('['),  # X
        4: KBKey.media_volume_down, # L-BUMPER
        5: KBKey.media_volume_up,   # R-BUMPER
        6: KBKey.media_stop,        # VIEW / BACK
        7: KBKey.media_play_pause,  # MENU / START
        8: KeyCode.from_char('V'),  # L-STICK
    }
}

class Media(Module):
    def __init__(self, keyboard: Controller):
        super().__init__(keyboard, "media")
        self.mappings = DEFAULT_MAPPINGS

    def load(self) -> bool:
        return super().load()

    def unload(self) -> bool:
        return super().unload()

    def on_key(self, key: Key):
        if mapped_key := self._get_mapped_key(key):
            self._log(f"pressing {mapped_key}")
            self.keyboard.press(mapped_key)
