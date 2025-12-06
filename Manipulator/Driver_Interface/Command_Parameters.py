from .IO import CommandParameter, linTypes

class Command_Parameters:
    target_position = CommandParameter(
        description="Target position", 
        type=linTypes.Sint32,
        unit="m",
        conversion_factor=1e7
    )
    velocity_unsigned = CommandParameter(
        description="Maximal velocity",
        type=linTypes.Uint32,
        unit="m/s",
        conversion_factor=1e6
    )
    acceleration_unsigned = CommandParameter(
        description="Acceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    deceleration_unsigned = CommandParameter(
        description="Deceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    demand_position = CommandParameter(
        description="Demand position",
        type=linTypes.Sint32,
        unit="m",
        conversion_factor=1e7
    )
    velocity_signed = CommandParameter(
        description="Demand velocity",
        type=linTypes.Sint32,
        unit="m/s",
        conversion_factor=1e6
    )
    acceleration_signed = CommandParameter(
        description="Demand acceleration",
        type=linTypes.Sint32,
        unit="m/s^2",
        conversion_factor=1e5
    )
    velocity_signed = CommandParameter(
        description="velocity",
        type=linTypes.Sint32,
        unit="m/s",
        conversion_factor=1e6,
    )
    velocity_unsigned = CommandParameter(
        description="velocity",
        type=linTypes.Uint32,
        unit="m/s",
        conversion_factor=1e6,
    )
    acceleration_unsigned = CommandParameter(
        description="acceleration",
        type=linTypes.Uint32,
        unit="m/s^2",
        conversion_factor=1e5,
    )
    UPID = CommandParameter(
        description="UPID",
        type=linTypes.Uint16,
        unit="",
        conversion_factor=1 
    )
    timer_value = CommandParameter(
        description="Slave timer value",
        type=linTypes.Sint32,
        unit="mym",
        conversion_factor=1
    )