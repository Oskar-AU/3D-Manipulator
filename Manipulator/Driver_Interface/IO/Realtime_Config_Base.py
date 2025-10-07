from .Command_Parameter_Base import Command_Parameter
from abc import ABC, abstractmethod
import struct

class Realtime_Config(ABC):
    
    @property
    @abstractmethod
    def COMMAND_ID(self) -> int:
        pass

    @property
    @abstractmethod
    def DESCRIPTION(self) -> str:
        pass

    def __init__(self, DO_parameters: tuple[Command_Parameter] = (), DO_values: tuple[float | int] = (), DI_parameters: tuple[Command_Parameter] = ()) -> None:
        self.DO_parameters = DO_parameters
        self.DI_parameters = DI_parameters

        self.DO_values = [int(DO_value * DO_parameters[i].get('conversion_factor')) for i, DO_value in enumerate(DO_values)]
        self.DO_format = "<H"  + "".join((parameter.get('type').get('format') for parameter in self.DO_parameters))
        self.DI_format = "<BB" + "".join((parameter.get('type').get('format') for parameter in self.DI_parameters))

    def get_header_decimal(self, COMMAND_COUNT: int) -> int:
        return (COMMAND_COUNT    <<  0  ) | \
               (self.COMMAND_ID  <<  8  )

    def get_binary(self, COMMAND_COUNT: int) -> bytes:
        return struct.pack(self.DO_format, self.get_header_decimal(COMMAND_COUNT), *self.DO_values)

    def get_response_byte_size(self) -> int:
        return 2 + sum((parameter.get('type').get('byte_size') for parameter in self.DI_parameters))

    def __repr__(self) -> str:
        header = "'" + self.DESCRIPTION + "'"
        parameters = {parameter['description']: self.DO_values[i] for i, parameter in enumerate(self.DO_parameters)}
        return header + " with params " + f"{parameters}"