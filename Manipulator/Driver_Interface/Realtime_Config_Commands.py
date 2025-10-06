from .IO import Realtime_Config
from .Realtime_Config_Parameters import Realtime_Config_Parameters
import copy

class Read_ROM_Value_of_Parameter_by_UPID(Realtime_Config):
    
    @property
    def COMMAND_ID(self) -> int:
        return 0x10
    
    @property
    def DESCRIPTION(self) -> str:
        return "Read ROM value of parameter by UPID"

    def __init__(self, parameter_UPID: int, parameter_value_low: int, parameter_value_high: int) -> None:
        super().__init__(
            (copy.deepcopy(Realtime_Config_Parameters.parameter_UPID), parameter_UPID),
            (copy.deepcopy(Realtime_Config_Parameters.parameter_value_low), parameter_value_low), 
            (copy.deepcopy(Realtime_Config_Parameters.parameter_value_high), parameter_value_high)
        )