from .Motion_Command_Parameter_Base import MC_Parameter
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
        parameter_format = "".join([MC_parameter['type']['format'] for MC_parameter in self.MC_PARAMETERS])
        return "H" + parameter_format

    def get_header_decimal(self, MC_COUNT: int) -> int:
        return (MC_COUNT        <<  0  ) | \
               (self.SUB_ID     <<  4  ) | \
               (self.MASTER_ID  <<  8  )

    def get_binary(self, MC_COUNT: int) -> bytes:
        MC_parameter_values = [MC_parameter['value'] for MC_parameter in self.MC_PARAMETERS]
        return struct.pack(self.format, self.get_header_decimal(MC_COUNT), *MC_parameter_values)
    
    def __repr__(self) -> str:
        header = self.DESCRIPTION
        parameters = {MC_parameter['description']: str(MC_parameter['value']/MC_parameter['conversion_factor']) + MC_parameter['unit'] for MC_parameter in self.MC_PARAMETERS}
        return header + " with params " + f"{parameters}"