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

    def __init__(self, MC_parameters: tuple[Command_Parameter], values: tuple[int | float]) -> None:
        """
        Base class for all motion command classes. All child classes must call this constructor.

        Parameters
        ----------
        MC_parameters : tuple[Command_Parameter]
            The specifications for the parameters in the motion command.
        values : tuple[int | float]
            The values corresponding to the motion command parameters.

        Attributes
        ----------
        MC_PARAMETERS : tuple[Command_Parameter]
            The specifiactions for the parameters in the motion command.
        values : tuple[int | float]
            The values corresponding to the motion command parameters.
        format : str
            The binary format of the package to send to the drive.
        MASTER_ID : int
            The master ID of the command.
        SUB_ID : int
            The sub ID of the command.
        DESCRIPTION : str
            A description of the command for logging purposes.
        """
        if len(MC_parameters) != len(values): raise ValueError("Amount of parameters didn't match amount of values.")
        self.MC_PARAMETERS = MC_parameters
        self.values = [int(value * self.MC_PARAMETERS[i].conversion_factor) for i, value in enumerate(values)]
        self.format = "<H" + "".join([MC_parameter.type.format for MC_parameter in self.MC_PARAMETERS])

    def get_header_decimal(self, MC_COUNT: int) -> int:
        """
        Gets the header of the motion command in decimal.

        Parameters
        ----------
        MC_COUNT : int
            The current motion command count.

        returns
        -------
        int
            The header in decimal.
        """
        return (MC_COUNT        <<  0  ) | \
               (self.SUB_ID     <<  4  ) | \
               (self.MASTER_ID  <<  8  )

    def get_binary(self, MC_COUNT: int) -> bytes:
        """
        Gets the full binary send package for the motion command.

        Parameters
        ----------
        MC_COUNT : int
            The current motion command count.

        Returns
        -------
        bytes
            The full binary send package.
        """
        return struct.pack(self.format, self.get_header_decimal(MC_COUNT), *self.values)

    def set_MC_parameter_value(self, index: int, MC_value: int | float) -> None:
        """
        Changes a parameter value ensuring that the units are converted to what the drivers
        expect.

        parameters
        ----------
        index : int
            The index of the parameter to change.
        MC_value : int | float
            The value of the parameter to change with the units specified by the parameter
            specifications.
        """
        self.values[index] = int(MC_value*self.MC_PARAMETERS[index].conversion_factor)

    def __repr__(self) -> str:
        header = "'" + self.DESCRIPTION + "'"
        parameters = {parameter.description: str(self.values[i]/parameter.conversion_factor) \
                      + parameter.unit for i, parameter in enumerate(self.MC_PARAMETERS)}
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

    def __init__(self, DO_parameters: tuple[Command_Parameter] = (), DO_values: tuple[float | int] = (), 
                 DI_parameters: tuple[Command_Parameter] = ()) -> None:
        """
        Base class for all realtime config commands. All child classes must call this constructor. A real-
        time command consists of output and input parameters (relative to the master).

        Parameters
        ----------
        DO_parameters : tuple[Command_Parameter], optional
            The specifications for the output parameters.
        DO_values : tuple[float | int], optional
            The values for the corresponding ouput parameters. Default is empty.
        DI_parameters : tuple[Command_Parameter], optional
            The specifications for the input parameters from the drivers.
        """
        self.DO_parameters = DO_parameters
        self.DI_parameters = DI_parameters

        self.DO_values = [int(DO_value * DO_parameters[i].conversion_factor) for i, DO_value in enumerate(DO_values)]
        self.DO_format = "<H"  + "".join((parameter.type.format for parameter in self.DO_parameters))
        self.DI_format = "<BB" + "".join((parameter.type.format for parameter in self.DI_parameters))

    def get_header_decimal(self, COMMAND_COUNT: int) -> int:
        """
        Gets the header of the realtime config command in decimal.

        Parameters
        ----------
        COMMAND_COUNT : int
            The current realtime config command count.

        returns
        -------
        int
            The header in decimal.
        """
        return (COMMAND_COUNT    <<  0  ) | \
               (self.COMMAND_ID  <<  8  )

    def get_binary(self, COMMAND_COUNT: int) -> bytes:
        """
        Gets the full binary send package for the realtime config command.

        Parameters
        ----------
        COMMAND_COUNT : int
            The current realtime config command count.

        Returns
        -------
        bytes
            The full binary send package.
        """
        return struct.pack(self.DO_format, self.get_header_decimal(COMMAND_COUNT), *self.DO_values)

    def get_response_byte_size(self) -> int:
        """
        Gets the expected byte size of the response of the realtime config command.

        Returns
        -------
        int
            The size of the expected response.
        """
        return 2 + sum((parameter.type.byte_size for parameter in self.DI_parameters))

    def __repr__(self) -> str:
        header = "'" + self.DESCRIPTION + "'"
        parameters = {parameter.description: self.DO_values[i] for i, parameter in enumerate(self.DO_parameters)}
        return header + " with params " + f"{parameters}"