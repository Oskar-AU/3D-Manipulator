from .IO import Connection, Request, Response
from .Control_Words import Control_Word
from .Drivers import Drivers

class _MC_COUNT:
    def __init__(self) -> None:
        self.value = 0x0

    def increment(self) -> None:
        self.value = self.value + 0x1 if self.value < 0xf else 0x0

MC_COUNT = _MC_COUNT()