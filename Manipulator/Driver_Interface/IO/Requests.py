from .Responses import Response
from .Control_Words import ControlWord
from .Commands import MotionCommmandInterface
from .Commands import RealtimeConfig
import struct
import logging

class Request:
    
    def __init__(self, 
                 response: Response = Response(),
                 control_word: ControlWord | None = None, 
                 MC_interface: MotionCommmandInterface | None = None,
                 realtime_config: RealtimeConfig | None = None,
                 logging_level: int = logging.DEBUG) -> None:
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
        logging_level : int, optional
            The logging level of the request and the corresponding response.
        """
        self.response = response
        self.control_word = control_word
        self.MC_interface = MC_interface
        self.realtime_config = realtime_config
        self.logging_level = logging_level

    def get_binary(self, MC_count: int, realtime_config_command_count: int) -> bytes:
        request_def = struct.pack("<I", 
            ((self.control_word     is not None) << 0) | 
            ((self.MC_interface     is not None) << 1) |
            ((self.realtime_config  is not None) << 2)
        )

        MC_interface_binary = self.MC_interface.get_binary(MC_count) if self.MC_interface is not None else bytes(0)
        control_word_binary = self.control_word.get_binary() if self.control_word is not None else bytes(0)
        realtime_config_binary = self.realtime_config.get_binary(realtime_config_command_count) if self.realtime_config is not None else bytes(0)
        request_header = request_def + self.response.response_def
        data = control_word_binary + MC_interface_binary + realtime_config_binary
        return request_header + data
    
    def __repr__(self) -> str:
        commands = []
        if self.control_word is not None: commands.append(f"control_word: {self.control_word}")
        if self.MC_interface is not None: commands.append(f"MC_command: {self.MC_interface}")
        if self.realtime_config is not None: commands.append(f"realtime_config: {self.realtime_config}")
        return f"Requesting: ({self.response}) w/ cmds: (" + ", ".join(commands) + ")" if len(commands) != 0 else f"Requesting: ({self.response})"