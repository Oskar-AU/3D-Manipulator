import struct
from abc import ABC, abstractmethod
from typing import Any
from typing import TypedDict

class linType(TypedDict):
    format: str
    byte_size: int

class linTypes:
    Sint16 = linType(format="h", byte_size=2)
    Uint16 = linType(format="H", byte_size=2)
    Uint32 = linType(format="I", byte_size=4)
    Sint32 = linType(format="i", byte_size=4)

class Command_Parameter(TypedDict):
    description: str
    type: linType
    unit: str
    conversion_factor: int
    value: int

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

    def __init__(self, *MC_parameters: tuple[Command_Parameter, Any]) -> None:
        self.MC_PARAMETERS: list[Command_Parameter] = list()
        for MC_parameter, MC_value in MC_parameters:
            MC_parameter['value'] = int(MC_value*MC_parameter['conversion_factor'])
            self.MC_PARAMETERS.append(MC_parameter)

    @property
    def format(self) -> str:
        parameter_format = "".join([MC_parameter['type']['format'] for MC_parameter in self.MC_PARAMETERS])
        return "<H" + parameter_format

    def get_header_decimal(self, MC_COUNT: int) -> int:
        return (MC_COUNT        <<  0  ) | \
               (self.SUB_ID     <<  4  ) | \
               (self.MASTER_ID  <<  8  )

    def get_binary(self, MC_COUNT: int) -> bytes:
        MC_parameter_values = [MC_parameter['value'] for MC_parameter in self.MC_PARAMETERS]
        return struct.pack(self.format, self.get_header_decimal(MC_COUNT), *MC_parameter_values)

    def set_MC_parameter_value(self, index: int, MC_value: Any) -> None:
        self.MC_PARAMETERS[index]['value'] = int(MC_value*self.MC_PARAMETERS[index]['conversion_factor'])

    def __repr__(self) -> str:
        header = "'" + self.DESCRIPTION + "'"
        parameters = {MC_parameter['description']: str(MC_parameter['value']/MC_parameter['conversion_factor']) + MC_parameter['unit'] for MC_parameter in self.MC_PARAMETERS}
        return header + " w/ params " + f"{parameters}"

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