from .Realtime_Config_Parameter_Base import Realtime_Config_Parameter
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