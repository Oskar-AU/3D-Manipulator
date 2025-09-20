from .Realtime_Config_Parameters import Realtime_Config_Parameters, Realtime_Config_Parameter
import struct
from abc import ABC, abstractmethod
from typing import Any

class Realtime_Config(ABC):
    
    @property
    @abstractmethod
    def COMMAND_ID(self) -> int:
        pass

    @property
    @abstractmethod
    def DESCRIPTION(self) -> str:
        pass

    def __init__(self, *realtime_config_parameters: tuple[Realtime_Config_Parameter, Any]) -> None:
        self.REALTIME_CONFIG_PARAMETERS: list[Realtime_Config_Parameter] = list()
        for realtime_config_parameter, realtime_config_value in realtime_config_parameters:
            realtime_config_parameter['value'] = realtime_config_value
            self.REALTIME_CONFIG_PARAMETERS.append(realtime_config_parameter)

    @property
    def format(self) -> str:
        return "H" + "H" * len(self.REALTIME_CONFIG_PARAMETERS)

    def get_header_decimal(self, COMMAND_COUNT: int) -> int:
        return (COMMAND_COUNT    <<  0  ) | \
               (self.COMMAND_ID  <<  8  )

    def get_binary(self, COMMAND_COUNT: int) -> bytes:
        realtime_config_parameter_values = [realtime_config_parameter['value'] for realtime_config_parameter in self.REALTIME_CONFIG_PARAMETERS]
        return struct.pack(self.format, self.get_header_decimal(COMMAND_COUNT), *realtime_config_parameter_values)

    def __repr__(self) -> str:
        header = self.DESCRIPTION
        parameters = {realtime_config_parameter['description']: realtime_config_parameter['value'] for realtime_config_parameter in self.REALTIME_CONFIG_PARAMETERS}
        return header + " with params " + f"{parameters}"

class Read_ROM_Value_of_Parameter_by_UPID(Realtime_Config):
    
    @property
    def COMMAND_ID(self) -> int:
        return 0x10
    
    @property
    def DESCRIPTION(self) -> str:
        return "Read ROM value of parameter by UPID"

    def __init__(self, parameter_UPID: int, parameter_value_low: int, parameter_value_high: int) -> None:
        super().__init__(
            (Realtime_Config_Parameters.parameter_UPID, parameter_UPID),
            (Realtime_Config_Parameters.parameter_value_low, parameter_value_low), 
            (Realtime_Config_Parameters.parameter_value_high, parameter_value_high)
        )