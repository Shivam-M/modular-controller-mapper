from modules.module import Module
from pyjoystick.sdl2 import Key


class Dummy(Module):
    def __init__(self):
        super().__init__(None, "dummy")

    def load(self) -> bool:
        super().load()
        return True

    def unload(self) -> bool:
        super().unload()
        return True

    def on_key(self, _: Key):
        pass
