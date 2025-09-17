from typing import TypedDict

class linType(TypedDict):
    size: int

class linTypes:
    Uint16 = linType(size=16)
    Uint32 = linType(size=32)
    Sint32 = linType(size=32)

class MC_Parameter(TypedDict):
    description: str
    bite_size: int
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