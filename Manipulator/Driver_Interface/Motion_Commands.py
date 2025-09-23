from .IO import Motion_Commmand_Interface
from .Motion_Command_Parameters import MC_Parameters

class VAI_go_to_pos(Motion_Commmand_Interface):
    
    @property
    def MASTER_ID(self) -> int:
        return 0x00
    
    @property
    def SUB_ID(self) -> int:
        return 0x1
    
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
            (MC_Parameters.target_position, target_position),
            (MC_Parameters.maximal_velocity, maximal_velocity), 
            (MC_Parameters.acceleration, acceleration), 
            (MC_Parameters.deceleration, deceleration)
        )