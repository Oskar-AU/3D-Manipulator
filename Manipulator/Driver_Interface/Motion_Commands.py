from .IO import Motion_Commmand_Interface
from .Motion_Command_Parameters import MC_Parameters
import copy

class No_Operation(Motion_Commmand_Interface):
    
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

class VAI_go_to_pos(Motion_Commmand_Interface):
    
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
            (copy.deepcopy(MC_Parameters.target_position), target_position),
            (copy.deepcopy(MC_Parameters.maximal_velocity), maximal_velocity), 
            (copy.deepcopy(MC_Parameters.acceleration), acceleration), 
            (copy.deepcopy(MC_Parameters.deceleration), deceleration)
        )

class P(Motion_Commmand_Interface):    

        @property
        def MASTER_ID(self) -> int:
            return 0x03
    
        @property
        def SUB_ID(self) -> int:
            return 0x2

        @property
        def DESCRIPTION(self) -> str:
            return "PVA Motion Command"

        def __init__(self, demand_position: float) -> None:

            super().__init__(
                (copy.deepcopy(MC_Parameters.demand_position), demand_position)
            )

class PV(Motion_Commmand_Interface):    

        @property
        def MASTER_ID(self) -> int:
            return 0x03
    
        @property
        def SUB_ID(self) -> int:
            return 0x3

        @property
        def DESCRIPTION(self) -> str:
            return "P Motion Command"

        def __init__(self, demand_position: float, demand_velocity: float) -> None:

            super().__init__(
                (copy.deepcopy(MC_Parameters.demand_position), demand_position),
                (copy.deepcopy(MC_Parameters.demand_velocity), demand_velocity), 
            )

class PVA(Motion_Commmand_Interface):    

    @property
    def MASTER_ID(self) -> int:
            return 0x03
    
    @property
    def SUB_ID(self) -> int:
        return 0x5

    @property
    def DESCRIPTION(self) -> str:
        return "PVA Motion Command"

    def __init__(self, demand_position: float, demand_velocity: float, demand_acceleration: float) -> None:

            super().__init__(
                (copy.deepcopy(MC_Parameters.demand_position), ('value': demand_position),
                (copy.deepcopy(MC_Parameters.demand_velocity), demand_velocity), 
                (copy.deepcopy(MC_Parameters.demand_acceleration), demand_acceleration), 
                )
    
class Stop(Motion_Commmand_Interface):
    """
    LinMot 'Stop Streaming' (03Fxh).
    """
     
    @property
    def MASTER_ID(self) -> int:
        return 0x03

    @property
    def SUB_ID(self) -> int:     # 0xF = 03Fxh
        return 0xF

    @property
    def DESCRIPTION(self) -> str:
        return "Stop Streaming"

    def __init__(self) -> None:
        super().__init__()


class WriteLiveParameter(Motion_Commmand_Interface):
    """
    LinMot 'Write Live Parameter' (04F1h).
    """
     
    @property
    def MASTER_ID(self) -> int:
        return 0x04

    @property
    def SUB_ID(self) -> int:     # 0xF1 = 04F1h
        return 0xF1

    @property
    def DESCRIPTION(self) -> str:
        return "Write Live Parameter"

    def __init__(self, parameter: MC_Parameter, value: float) -> None:
        super().__init__(
            (copy.deepcopy(parameter), value)
        )