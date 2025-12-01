from .IO import Command_Parameter, linTypes

class Command_Parameters:
    target_position = Command_Parameter(
        description="Target position", 
        type=linTypes.Sint32,
        unit="m",
        conversion_factor=1e7
    )
    velocity_unsigned = Command_Parameter(
        description="Maximal velocity",
        type=linTypes.Uint32,
        unit="m/s",
        conversion_factor=1e6
    )
    acceleration_unsigned = Command_Parameter(
        description="Acceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    deceleration_unsigned = Command_Parameter(
        description="Deceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    demand_position = Command_Parameter(
        description="Demand position",
        type=linTypes.Sint32,
        unit="m",
        conversion_factor=1e7
    )
    velocity_signed = Command_Parameter(
        description="Demand velocity",
        type=linTypes.Sint32,
        unit="m/s",
        conversion_factor=1e6
    )
    acceleration_signed = Command_Parameter(
        description="Demand acceleration",
        type=linTypes.Sint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    velocity_signed = Command_Parameter(
        description="velocity",
        type=linTypes.Sint32,
        unit="m/s",
        conversion_factor=1e6,
    )
    velocity_unsigned = Command_Parameter(
        description="velocity",
        type=linTypes.Uint32,
        unit="m/s",
        conversion_factor=1e6,
    )
    acceleration_unsigned = Command_Parameter(
        description="acceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5,
    )
    UPID = Command_Parameter(
        description="UPID",
        type=linTypes.Uint16,
        unit="",
        conversion_factor=1 
    )
    timer_value = Command_Parameter(
        description="Slave timer value",
        type=linTypes.Sint32,
        unit="mym",
        conversion_factor=1
    )