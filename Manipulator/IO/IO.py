from .Motion_Commands import Motion_Commmand_Interface
from .Control_Words import Control_Word
from .Realtime_Configs import Realtime_Config
from .Drivers import Driver
import socket
import struct

class Response:
    def __init__(self, status_word: bool = False, state_var: bool = False, actual_pos: bool = False, demand_pos: bool = False,
                 current: bool = False, warm_word: bool = False, error_code: bool = False, monitoring_channel: bool = False,
                 realtime_config: bool = False) -> bytes:
        """
        Defines a response by selecting which options the response should include.

        Parameters
        ----------
        status_word : bool, optional
            If true a 2 byte status word is requested in the response.
        state_var : bool, optional
            If true a 2 byte state variable is requested in the response.
        actual_pos : bool, optional
            If true the actual position as 4 bytes of the motor is requested in the response.
        demand_pos : bool, optional
            If true the demand position of the motor as 4 bytes is requested in the response.
        current : bool, optional
            If true the set current as 2 bytes is requested in the response.
        warm_word : bool, optional
            If true the warm word as 2 bytes is requested in the response.
        error_code : bool, optional
            If true the error code as 2 bytes is requested in the response.
        monitoring_channel : bool, optional
            If true the value of the monitored UPID set in the parameters of the drive is requested in the response.
        realtime_config : bool, optional
            If true the requested realtime parameter is returned.
        """
        self.include_status_word = status_word
        self.include_state_var = state_var
        self.include_actual_pos = actual_pos
        self.include_demand_pos = demand_pos
        self.include_current = current
        self.include_warm_word = warm_word
        self.include_error_code = error_code
        self.include_monitoring_channel = monitoring_channel
        self.include_realtime_config = realtime_config

    @property
    def format(self) -> str:
        return "".join([
            self.include_status_word,
            self.include_state_var,
            self.include_actual_pos,
            self.include_demand_pos,
            self.include_current,
            self.include_warm_word,
            self.include_error_code,
            self.include_monitoring_channel,
            self.include_realtime_config
        ])

    @property
    def response_def(self) -> bytes:
        return struct.pack("I",
            (self.include_status_word         <<      0       ) |
            (self.include_state_var           <<      1       ) |
            (self.include_actual_pos          <<      2       ) |
            (self.include_demand_pos          <<      3       ) |
            (self.include_current             <<      4       ) |
            (self.include_warm_word           <<      5       ) |
            (self.include_error_code          <<      6       ) |
            (self.include_monitoring_channel  <<      7       ) |
            (self.include_realtime_config     <<      8       )
        )

class Request:
    
    def __init__(self, 
                 response: Response,
                 control_word: Control_Word | None = None, 
                 MC_interface: Motion_Commmand_Interface | None = None) -> None:
                #  realtime_config: Realtime_Config | None = None) -> None:
        """
        Parameters
        ----------
        response : Response
            The response to be expected.
        control_word : bool, optional
            If true the main state machine of the drive can be accessed.
        MC_interface : bool, optional
            If true a motion command can be sent.
        realtime_config : bool, optional
            If true parameters, variables, curves, error log, and command tables can be accessed. Also restart, start, stop
            of the drive can be initiated.
        """
        self.response = response
        self.control_word = control_word
        self.MC_interface = MC_interface
        # self.realtime_config = realtime_config

    @property
    def binary(self) -> bytes:
        request_def = struct.pack("I", 
            ((self.control_word is not None) << 0) | 
            ((self.MC_interface is not None) << 1) #|
            # ((self.realtime_config is None) << 2)
        )

        MC_interface_binary = self.MC_interface.binary if self.MC_interface is not None else bytes(0)
        control_word_binary = self.control_word.binary if self.control_word is not None else bytes(0)
        # realtime_config_binary = self.realtime_config.binary if self.realtime_config is not None else bytes(0)
        request_header = request_def + self.response.response_def
        data = control_word_binary + MC_interface_binary# + self.realtime_config.binary
        return request_header + data

class Connection:

    def __init__(self) -> None:
        main_port = 41136
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", main_port))
        self.socket.settimeout(1.0)

    def send(self, request: Request, driver: Driver) -> None:
        
        # print(struct.unpack("2IH4I", request.binary))
        print(request.binary)
        self.socket.sendto(request.binary, (driver['address'], driver['port']))
        try:
            response_package, addr = self.socket.recvfrom(64)
            print(response_package)
        except socket.timeout:
            print("timed out")