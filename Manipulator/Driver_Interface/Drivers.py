from IO import linUDP, Request, Translated_Response
import logging
from socket import timeout

logger = logging.getLogger(__name__)

class Driver:
    
    # Procedure methods
    # ...

    def __init__(self, IP: str, name: str, datagram: linUDP) -> None:
        self.IP = IP
        self.port = 49360
        self.name = name
        self.datagram = datagram

    def send(self, request: Request, MC_count: int | None = None, realtime_config_command_count: int | None = None) -> Translated_Response | None:
        """
        Parameters
        ----------
        request : Request
            ...
        MC_count : int, optional
            The count of the motion command (4 bits). Must be different than the 
            previous motion command otherwise it is ignored by the drive.
        realtime_config_command_count : int, optional
            The count of the realtime config command (4 bits). Must be different than the 
            previous command otherwise it is ignored by the drive.
        """
        self.datagram.socket.sendto(request.get_binary(MC_count, realtime_config_command_count), (self.IP, self.port))
        
        # Logging the send.
        logger.log(request.logging_level, f"Request sent to '{self.name}': {request}")

        try:
            response_raw, response_address = self.datagram.socket.recvfrom(64)
            
            # Checks if the response came from the same driver as the request was sent to.
            response_IP, _ = response_address
            if response_IP != self.IP:
                logger.warning(f"Recieved response from {response_IP} but expected {self.IP}")
            
            # Translating the response.
            translated_response = request.response.translate_response(response_raw)
            
            #Logging the recieve.
            logger.log(request.logging_level, f"Response recieved from '{self.name}': {translated_response}")

            return translated_response
        except timeout:
            logger.warning(f"Response from '{self.name}' timed out (1s).")

class Drivers:
    drive_1 = Driver(
        IP = "192.168.131.251",
        port = 49360,
        name = "drive_1"
    )
    drive_2 = Driver(
        IP = "192.168.131.252",
        port = 49360,
        name = "drive_2"
    )
    drive_3 = Driver(
        IP = "192.168.131.253",
        port = 49360,
        name = "drive_3"
    )
    all = Driver(
        IP = "192.168.131.255",
        port = 49360,
        name = "all"
    )