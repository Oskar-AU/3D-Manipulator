from typing import TypedDict

class linType(TypedDict):
    format: str

class linTypes:
    Uint16 = linType(format="H")
    Uint32 = linType(format="I")
    Sint32 = linType(format="i")

class MC_Parameter(TypedDict):
    description: str
    type: linType
    unit: str
    conversion_factor: int
    value: int