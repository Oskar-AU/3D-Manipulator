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

    def send(self, request: IO.Request, MC_count: int | None = None, realtime_config_command_count: int | None = None, attempt: int = 1) -> IO.Translated_Response:
        """
        Parameters
        ----------
        request : Request
            The request to send to the drive.
        MC_count : int, optional
            The count of the motion command (4 bits). Must be different than the 
            previous motion command otherwise it is ignored by the drive.
        realtime_config_command_count : int, optional
            The count of the realtime config command (4 bits). Must be different than the 
            previous command otherwise it is ignored by the drive.
        attempt : int, optional
            The attempt number for the request. Should not be used.

        Returns
        -------
        IO.Translated_Response
            A dict containing the translated response from the drive. Content depends on the request.

        raises
        ------
        TimedOutError
            If no response is recieved after 5 attempts.
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
            logger.warning(f"Response from '{self.name}' timed out (1s) at attempt {attempt}/5.")
            if attempt < 5:
                return self.send(request, MC_count, realtime_config_command_count, attempt + 1)
            else:
                logger.critical(f"Unable to recieve from '{self.name}'.")
                raise TimeoutError(f"Unable to recieve from '{self.name}'.")

    def get_main_state(self) -> int:
        """
        Gets the main state of the drive.

        Returns
        -------
        int
            The main state of the drive.
        """
        return self.send(IO.Request(IO.Response(state_var=True))).get('state_var').get('main_state')

    def home(self, timeout: float = 30) -> bool:
        """
        Sends a command to home the LinMot motors. The drive must be in state 8.

        Parameters
        ----------
        timeout : float, optional
            The time (s) to wait before the homing procedure is considered failed. Default is 30s.

        Returns
        -------
        bool
            Whether or not the procedure ended succesfully.
        """
        logger.info(f"Homing procedure for '{self.name}' initiated.")

        # Confirms if the drive is ready to be homed.
        main_state = self.get_main_state()
        if self.send(IO.Request(IO.Response(state_var=True))).get('state_var').get('main_state') != 8:
            logger.error(f"Homing procedure for '{self.name}' failed: Not in correct state ({main_state} != 8).")
            return False

        # Sending home request.
        home_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True, home=True))
        self.send(home_request)

        # Waiting for homing to finish.
        is_homing_finished_request = IO.Request(IO.Response(state_var=True))
        is_homing_finished = lambda: self.send(is_homing_finished_request).get('state_var').get('homing_finished')
        if not self.wait_for_change(is_homing_finished, timeout, 1):
            logger.error(f"Homing procedure for '{self.name}' failed: Timed out ({timeout}s). Switching off drive.")
            self.send(IO.Request(IO.Response(), IO.Control_Word()))
            return False
        
        # Finialzing.
        home_off_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True))
        self.send(home_off_request)
        logger.info(f"Homing procedure for '{self.name}' completed.")
        return True

    def switch_on(self, timeout: float = 5) -> bool:
        """
        Switches on the drive by setting the main state to 8 from either state 0 or 2.

        Parameters
        ----------
        timeout : float, optional
            The time (s) to wait before considering the switch on procedure failed.

        Returns
        -------
        bool
            Whether or not the procedure ended succesfully.
        """
        logger.info(f"Switch on procedure for '{self.name}' initiated.")
        main_state = self.get_main_state()
        
        if main_state == 8:
            logger.info(f"'{self.name}' already swicthed on. Finishing procedure.")
            return True
        if main_state != 2:
            # Requesting state 2.
            self.send(IO.Request(IO.Response(), IO.Control_Word()))

            # Waiting for main state to go state 2.
            if not self.wait_for_change(lambda: self.get_main_state() == 2, timeout=timeout, delay=0.2):
                logger.error(f"Switch on procedure for '{self.name}' failed: Timed out going to state 2 ({timeout}s). Current state is {self.get_main_state()}.")
                return False

            main_state = self.get_main_state()
        
        if main_state == 2:
            # Requesting state 8.        
            self.send(IO.Request(IO.Response(), IO.Control_Word(switch_on=True)))

            # Waiting for state 8.
            if not self.wait_for_change(lambda: self.get_main_state() == 8, timeout=timeout, delay=0.2):
                logger.error(f"Switch on procedure for '{self.name}' failed: Timed out going from state 2 to 8 ({timeout}s). Current state is {self.get_main_state()}.")
                return False
            
            # Finalizing.
            logger.info(f"Switch on procedure for '{self.name}' completed.")
            return True

    def wait_for_change(self, change_checker: Callable[[None], bool], timeout: float, delay: float = 0.0) -> bool:
        """
        Procedure that waits for a given change to happen in the drive.

        Parameters
        ----------
        change_checker : Callable[[None], bool]
            The criteria to check at 'delay' intervals.
        timeout : float
            The amount of time to wait for the change to happen before considering the change to not happen.
        delay : float, optional
            The time between checking the criteria. Default is as fast as possible.
        """
        start_time = time.time()
        current_time = time.time()
        while not change_checker():
            if current_time - start_time >= timeout:
                return False
            current_time = time.time()
            time.sleep(delay)
        return True