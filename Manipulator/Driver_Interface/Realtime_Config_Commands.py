from .IO import Realtime_Config, linType, Command_Parameter
from .Command_Parameters import Command_Parameters
from typing import Any

class Read_ROM_Value_of_Parameter_by_UPID(Realtime_Config):
    
    @property
    def COMMAND_ID(self) -> int:
        return 0x10
    
    @property
    def DESCRIPTION(self) -> str:
        return "Read ROM value of parameter by UPID"

    def __init__(self, parameter_UPID: int, parameter_value: Any) -> None:
        raise NotImplementedError

class Read_RAM_Value_of_Parameter_by_UPID(Realtime_Config):
    
    @property
    def COMMAND_ID(self) -> int:
        return 0x11
    
    @property
    def DESCRIPTION(self) -> str:
        return "Read RAM value of parameter by UPID"

    def __init__(self, UPID: int, UPID_type: linType, UPID_description: str = "UPID value", UPID_unit: str = "", UPID_conversion_factor: int = 1) -> None:
        DI_parameter = Command_Parameter(
            description=UPID_description,
            type=UPID_type,
            unit=UPID_unit,
            conversion_factor=UPID_conversion_factor
        )
        super().__init__((Command_Parameters.UPID,), (UPID,), (Command_Parameters.UPID, DI_parameter,))

class No_Operation(Realtime_Config):

    @property
    def COMMAND_ID(self) -> int:
        return 0x00
    
    @property
    def DESCRIPTION(self) -> str:
        return "No operation"
    
    def __init__(self) -> None:
        super().__init__()