from .IO import MotionCommmandInterface
from .IO import linType
from .IO import CommandParameter
from .Command_Parameters import Command_Parameters
import copy

class No_Operation(MotionCommmandInterface):
    
    @property
    def MASTER_ID(self) -> int:
        return 0x00
 
    @property
    def SUB_ID(self) -> int:
        return 0x0
    
    @property
    def DESCRIPTION(self) -> str:
        return "No operation"

    def __init__(self) -> None:
        
        super().__init__()

class VAI_go_to_pos(MotionCommmandInterface):
    
    @property
    def MASTER_ID(self) -> int:
        return 0x01
    
    @property
    def SUB_ID(self) -> int:
        return 0x0
    
    @property
    def DESCRIPTION(self) -> str:
        return "VAI_go_to_pos"

    def __init__(self, target_position: float, maximal_velocity: float, acceleration: float, deceleration: float) -> None:
        """
        This commands sets a new target position and defines the maximal velocity, acceleration, and
        deceleration for the movement. The command execution starts immediatly when the command has
        been sent. The set points (demand position, demand velocity and demand acceleration) are
        calculated by the internal Velocity Acceleration Interpolator (VAI). This command initializes
        the VAI with the current demand position and demand velocity value. Therefore it is possible
        to start a new command while a former command is still being executed.

        Parameters
        ----------
        target_position : float
            The target position in mm.
        maximal_velocity : float
            The maximal velocity in m/s.
        acceleration : float
            The acceleration used in m/s^2.
        deceleration : float
            The deceleration used in m/s^2.
        """
        super().__init__(
            (
                Command_Parameters.target_position,
                Command_Parameters.velocity_unsigned,
                Command_Parameters.acceleration_unsigned,
                Command_Parameters.deceleration_unsigned
            ),
            (
                target_position,
                maximal_velocity,
                acceleration,
                deceleration
            )
        )

class P_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(MotionCommmandInterface):    

        @property
        def MASTER_ID(self) -> int:
            return 0x03
    
        @property
        def SUB_ID(self) -> int:
            return 0x2

        @property
        def DESCRIPTION(self) -> str:
            return "P stream with slave generated time stamp and configured period time"

        def __init__(self, demand_position: float) -> None:

            super().__init__((Command_Parameters.demand_position,), (demand_position,))

class PV_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(MotionCommmandInterface):

        @property
        def MASTER_ID(self) -> int:
            return 0x03
    
        @property
        def SUB_ID(self) -> int:
            return 0x3

        @property
        def DESCRIPTION(self) -> str:
            return "PV stream with slave generated time stamp and configured period time"

        def __init__(self, demand_position: float, demand_velocity: float) -> None:

            super().__init__(
                (
                    Command_Parameters.demand_position,
                    Command_Parameters.velocity_signed
                ),
                (
                    demand_position,
                    demand_velocity
                )
            )

class PVA_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(MotionCommmandInterface):    

    @property
    def MASTER_ID(self) -> int:
            return 0x03
    
    @property
    def SUB_ID(self) -> int:
        return 0x5

    @property
    def DESCRIPTION(self) -> str:
        return "PVA stream with slave generated time stamp and configured period time"

    def __init__(self, demand_position: float, demand_velocity: float, demand_acceleration: float) -> None:

        super().__init__(
            (
                Command_Parameters.demand_position,
                Command_Parameters.velocity_signed,
                Command_Parameters.acceleration_signed
            ),
            (
                demand_position,
                demand_velocity,
                demand_acceleration
            )
        )
    
class PV_Stream_With_Slave_Generated_Time_Stamp(MotionCommmandInterface):

        @property
        def MASTER_ID(self) -> int:
            return 0x03
    
        @property
        def SUB_ID(self) -> int:
            return 0x1

        @property
        def DESCRIPTION(self) -> str:
            return "PV stream with slave generated time stamp"

        def __init__(self, demand_position: float, demand_velocity: float) -> None:

            super().__init__(
                (
                    Command_Parameters.demand_position,
                    Command_Parameters.velocity_signed
                ),
                (
                    demand_position,
                    demand_velocity
                )
            )

class Stop_Streaming(MotionCommmandInterface):
     
    @property
    def MASTER_ID(self) -> int:
        return 0x03

    @property
    def SUB_ID(self) -> int:
        return 0xF

    @property
    def DESCRIPTION(self) -> str:
        return "Stop Streaming"

    def __init__(self) -> None:
        super().__init__()


class Write_Live_Parameter(MotionCommmandInterface):

    @property
    def MASTER_ID(self) -> int:
        return 0x00

    @property
    def SUB_ID(self) -> int:     # 0xF1 = 04F1h
        return 0x2

    @property
    def DESCRIPTION(self) -> str:
        return "Write Live Parameter"

    def __init__(self, UPID: int, parameter_value: int, parameter_type: linType) -> None:

        raw_parameter = CommandParameter(
            description="Write live parameter",
            type=parameter_type,
            unit="",
            conversion_factor=1
        )

        super().__init__(
            (
                Command_Parameters.UPID,
                raw_parameter   
            ),
            (
                UPID,
                parameter_value
            )
        )

class AccVAI_Infinite_Motion_Positive_Direction(MotionCommmandInterface):
    
    @property
    def MASTER_ID(self) -> int:
        return 0x0C
    
    @property
    def SUB_ID(self) -> int:
        return 0xE
    
    @property
    def DESCRIPTION(self) -> str:
        return "Infinite motion in positive direction."
    
    def __init__(self, velocity: float, acceleration: float = 10.0) -> None:
        
        super().__init__(
            (
                Command_Parameters.velocity_unsigned,
                Command_Parameters.acceleration_unsigned
            ),
            (
                velocity,
                acceleration
            )
        )

class AccVAI_Infinite_Motion_Negative_Direction(MotionCommmandInterface):
    
    @property
    def MASTER_ID(self) -> int:
        return 0x0C
    
    @property
    def SUB_ID(self) -> int:
        return 0xF
    
    @property
    def DESCRIPTION(self) -> str:
        return "Infinite motion in negative direction."
    
    def __init__(self, velocity: float, acceleration: float = 10.0) -> None:
        
        super().__init__(
            (
                Command_Parameters.velocity_unsigned,
                Command_Parameters.acceleration_unsigned
            ),
            (
                velocity,
                acceleration
            )
        )

class VAI_Stop(MotionCommmandInterface):

    @property
    def MASTER_ID(self) -> int:
        return 0x01
    
    @property
    def SUB_ID(self) -> int:
        return 0x7
    
    @property
    def DESCRIPTION(self) -> str:
        return "Stop VAI motion."
    
    def __init__(self, decceleration: float = 10.0) -> None:
        
        super().__init__((Command_Parameters.acceleration_unsigned,), (decceleration,))