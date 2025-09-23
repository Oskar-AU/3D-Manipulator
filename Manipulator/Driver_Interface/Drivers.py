from . import IO
from socket import timeout
from typing import Callable
import logging
import time

logger = logging.getLogger(__name__)

class Driver:

    def __init__(self, IP: str, name: str, datagram: IO.linUDP) -> None:
        self.IP = IP
        self.port = 49360
        self.name = name
        self.datagram = datagram

    def send(self, request: IO.Request, MC_count: int | None = None, realtime_config_command_count: int | None = None) -> IO.Translated_Response | None:
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

    def home(self, timeout: float = 30, delay: float = 1) -> bool:
        """
        Sends a command to home the LinMot motors.
        """
        # Sending home request.
        home_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True, home=True))
        self.send(home_request)
        logger.info(f"Homing procedure for '{self.name}' initiated.")

        # Waiting for homing to finish.
        is_homing_finished_request = IO.Request(IO.Response(state_var=True))
        is_homing_finished = lambda: self.send(is_homing_finished_request).get('state_var').get('homing_finished')
        if not self.wait_for_change(is_homing_finished, timeout, delay):
            logger.error(f"Homing of '{self.name}' failed to complete within timeout ({timeout}s). Switchinf off drive.")
            self.send(IO.Request(IO.Response(), IO.Control_Word()))
            return False
        
        # Finialzing.
        home_off_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True))
        self.send(home_off_request)
        logger.info(f"Homing procedure for '{self.name}' completed.")
        return True

    def wait_for_change(self, change_checker: Callable[[None], bool], timeout: float, delay: float = 0.0) -> bool:
        """
        
        """
        start_time = time.time()
        current_time = time.time()
        while not change_checker():
            if current_time - start_time >= timeout:
                return False
            current_time = time.time()
            time.sleep(delay)
        return True