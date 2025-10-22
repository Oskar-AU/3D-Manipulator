from typing import TypedDict

class linType(TypedDict):
    format: str
    byte_size: int

class linTypes:
    Sint16 = linType(format="h", byte_size=2)
    Uint16 = linType(format="H", byte_size=2)
    Uint32 = linType(format="I", byte_size=4)
    Sint32 = linType(format="i", byte_size=4)