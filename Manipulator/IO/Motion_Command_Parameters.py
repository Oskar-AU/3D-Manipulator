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

class MC_Parameters:
    target_position = MC_Parameter(
        description="Target position", 
        type=linTypes.Sint32,
        unit="mm",
        conversion_factor=1e4
    )
    maximal_velocity = MC_Parameter(
        description="Maximal velocity",
        type=linTypes.Uint32,
        unit="m/s",
        conversion_factor=1e6
    )
    acceleration = MC_Parameter(
        description="Acceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    deceleration = MC_Parameter(
        description="Deceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5
    )