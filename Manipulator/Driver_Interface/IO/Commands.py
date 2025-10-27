import struct
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

@dataclass
class linType:
    format: str
    byte_size: int

class linTypes:
    Sint16 = linType(format="h", byte_size=2)
    Uint16 = linType(format="H", byte_size=2)
    Uint32 = linType(format="I", byte_size=4)
    Sint32 = linType(format="i", byte_size=4)

@dataclass
class Command_Parameter:
    description: str
    type: linType
    unit: str
    conversion_factor: int

class Command(ABC):

    @property
    @abstractmethod
    def DESCRIPTION(self) -> str:
        pass

class Motion_Commmand_Interface(Command):
    
    @property
    @abstractmethod
    def MASTER_ID(self) -> int:
        pass

    @property
    @abstractmethod
    def SUB_ID(self) -> int:
        pass

    def __init__(self, MC_parameters: tuple[Command_Parameter], values: tuple[int | float]) -> None:
        if len(MC_parameters) != len(values): raise ValueError("Amount of parameters didn't match amount of values.")
        self.MC_PARAMETERS = MC_parameters
        self.values = [int(value * self.MC_PARAMETERS[i].conversion_factor) for i, value in enumerate(values)]
        self.format = "<H" + "".join([MC_parameter.type.format for MC_parameter in self.MC_PARAMETERS])

    def get_header_decimal(self, MC_COUNT: int) -> int:
        return (MC_COUNT        <<  0  ) | \
               (self.SUB_ID     <<  4  ) | \
               (self.MASTER_ID  <<  8  )

    def get_binary(self, MC_COUNT: int) -> bytes:
        return struct.pack(self.format, self.get_header_decimal(MC_COUNT), *self.values)

    def set_MC_parameter_value(self, index: int, MC_value: Any) -> None:
        self.values[index] = int(MC_value*self.MC_PARAMETERS[index].conversion_factor)

    def __repr__(self) -> str:
        header = "'" + self.DESCRIPTION + "'"
        parameters = {parameter.description: str(self.values[i]/parameter.conversion_factor) + parameter.unit for i, parameter in enumerate(self.MC_PARAMETERS)}
        return header + " w/ params " + f"{parameters}"

class Realtime_Config(Command):
    
    @property
    @abstractmethod
    def COMMAND_ID(self) -> int:
        pass

    def __init__(self, DO_parameters: tuple[Command_Parameter] = (), DO_values: tuple[float | int] = (), DI_parameters: tuple[Command_Parameter] = ()) -> None:
        self.DO_parameters = DO_parameters
        self.DI_parameters = DI_parameters

        self.DO_values = [int(DO_value * DO_parameters[i].conversion_factor) for i, DO_value in enumerate(DO_values)]
        self.DO_format = "<H"  + "".join((parameter.type.format for parameter in self.DO_parameters))
        self.DI_format = "<BB" + "".join((parameter.type.format for parameter in self.DI_parameters))

    def get_header_decimal(self, COMMAND_COUNT: int) -> int:
        return (COMMAND_COUNT    <<  0  ) | \
               (self.COMMAND_ID  <<  8  )

    def get_binary(self, COMMAND_COUNT: int) -> bytes:
        return struct.pack(self.DO_format, self.get_header_decimal(COMMAND_COUNT), *self.DO_values)

    def get_response_byte_size(self) -> int:
        return 2 + sum((parameter.type.byte_size for parameter in self.DI_parameters))

    def __repr__(self) -> str:
        header = "'" + self.DESCRIPTION + "'"
        parameters = {parameter.description: self.DO_values[i] for i, parameter in enumerate(self.DO_parameters)}
        return header + " with params " + f"{parameters}"