from .Drivers import Driver
from .Requests import Request
from .Responses import Translated_Response
import socket
import logging

logger = logging.getLogger(__name__)

class linUDP:

    def __init__(self) -> None:
        main_port = 41136
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", main_port))
        self.socket.settimeout(1.0)

    def sendto(self, request: Request, driver: Driver, MC_count: int | None = None, realtime_config_command_count: int | None = None) -> Translated_Response | None:
        """
        Parameters
        ----------
        request : Request
            ...
        driver : Driver
            ...
        MC_count : int, optional
            The count of the motion command (4 bits). Must be different than the 
            previous motion command otherwise it is ignored by the drive.
        realtime_config_command_count : int, optional
            The count of the realtime config command (4 bits). Must be different than the 
            previous command otherwise it is ignored by the drive.
        """
        self.socket.sendto(request.get_binary(MC_count, realtime_config_command_count), (driver['IP'], driver['port']))
        
        # Logging the send.
        logger.log(request.logging_level, f"Request sent to '{driver['name']}': {request}")

        try:
            response_raw, response_address = self.socket.recvfrom(64)
            
            # Checks if the response came from the same driver as the request was sent to.
            response_IP, _ = response_address
            if response_IP != driver['IP']:
                logger.warning(f"Recieved response from {response_IP} but expected {driver['IP']}")
            
            # Translating the response.
            translated_response = request.response.translate_response(response_raw)
            
            #Logging the recieve.
            logger.log(request.logging_level, f"Response recieved from '{driver['name']}': NotImplementedError")    # TODO: Finish log.

            return translated_response
        except socket.timeout:
            logger.warning(f"Response from '{driver['name']}' timed out (1s).")