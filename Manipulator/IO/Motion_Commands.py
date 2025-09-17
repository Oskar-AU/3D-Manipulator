from .Motion_Command_Parameters import MC_Parameters, MC_Parameter
import struct
from abc import ABC, abstractmethod
from typing import Any

class Motion_Commmand_Interface(ABC):
    
    @property
    @abstractmethod
    def MASTER_ID(self) -> int:
        pass

    @property
    @abstractmethod
    def SUB_ID(self) -> int:
        pass

    @property
    @abstractmethod
    def DESCRIPTION(self) -> str:
        pass

    def __init__(self, *MC_parameters: tuple[MC_Parameter, Any]) -> None:
        self.MC_PARAMETERS: list[MC_Parameter] = list()
        for MC_parameter, MC_value in MC_parameters:
            MC_parameter['value'] = int(MC_value*MC_parameter['conversion_factor'])
            self.MC_PARAMETERS.append(MC_parameter)

    @property
    def format(self) -> str:
        format = "".join([MC_parameter['type']['format'] for MC_parameter in self.MC_PARAMETERS])
        return "H" + format

    def get_binary(self, MC_COUNT: int) -> bytes:
        MC_parameter_values = [MC_parameter['value'] for MC_parameter in self.MC_PARAMETERS]
        return struct.pack(self.format, 
                          (MC_COUNT        <<  0  ) |
                          (self.SUB_ID     <<  4  ) | 
                          (self.MASTER_ID  <<  8  ), 
                          *MC_parameter_values)

class VAI_go_to_pos(Motion_Commmand_Interface):
    
    @property
    def MASTER_ID(self) -> int:
        return 0x00
    
    @property
    def SUB_ID(self) -> int:
        return 0x1
    
    @property
    def DESCRIPTION(self) -> str:
        return "something"

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
            (MC_Parameters.target_position, target_position),
            (MC_Parameters.maximal_velocity, maximal_velocity), 
            (MC_Parameters.acceleration, acceleration), 
            (MC_Parameters.deceleration, deceleration)
        )