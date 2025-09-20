
from .Responses import Response
from .Control_Words import Control_Word
from .Motion_Commands import Motion_Commmand_Interface
from .Realtime_Configs import Realtime_Config
import struct
import logging

class Request:
    
    def __init__(self, 
                 response: Response,
                 control_word: Control_Word | None = None, 
                 MC_interface: Motion_Commmand_Interface | None = None,
                 realtime_config: Realtime_Config | None = None,
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

    def get_binary(self, MC_count: int) -> bytes:
        request_def = struct.pack("I", 
            ((self.control_word     is not None) << 0) | 
            ((self.MC_interface     is not None) << 1) |
            ((self.realtime_config  is not None) << 2)
        )

        MC_interface_binary = self.MC_interface.get_binary(MC_count) if self.MC_interface is not None else bytes(0)
        control_word_binary = self.control_word.get_binary() if self.control_word is not None else bytes(0)
        realtime_config_binary = self.realtime_config.get_binary() if self.realtime_config is not None else bytes(0)
        request_header = request_def + self.response.response_def
        data = control_word_binary + MC_interface_binary + realtime_config_binary
        return request_header + data
    
    def __repr__(self) -> str:
        return f"Control_word = {self.control_word}, MC_command = {self.MC_interface}, realtime_config = {self.realtime_config}"