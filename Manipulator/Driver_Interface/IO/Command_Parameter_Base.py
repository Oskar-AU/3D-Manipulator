from typing import TypedDict
from .linTypes import linType

class Command_Parameter(TypedDict):
    description: str
    type: linType
    unit: str
    conversion_factor: int
    value: int