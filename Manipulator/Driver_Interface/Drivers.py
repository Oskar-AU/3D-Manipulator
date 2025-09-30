from . import IO
from typing import Callable, Self, Any, TypeVar, ParamSpec
import logging
import time
import queue
import threading
import functools
from concurrent.futures import Future

return_type = TypeVar("R")
parameter_types = ParamSpec("T")

class DriveError(Exception):
    def __init__(self, drive: "Driver", error_code: int, post_message: str = "") -> None:
        message = f"Error code {error_code} raised by '{drive.name}'." + post_message
        self.error_code = error_code
        self.drive = drive
        super().__init__(message)

class Driver:

    def __init__(self, IP: str, name: str, datagram: IO.linUDP) -> None:
        self.IP = IP
        self.name = name
        self.datagram = datagram
        self._send_attempt = 1
        self.awaiting_error_acknowledgement = False
        self._method_queue: queue.Queue[tuple[Callable, tuple[Any], dict[Any], Future]] = queue.Queue()
        self._thread = threading.Thread(target=self._run_method_queue, name=name)
        self._thread.start()
        self.logger = logging.getLogger(self.name)
        self.warning_words: list[IO.Responses.Warn_Word] = list()

    def _run_method_queue(self) -> None:
        """
        The method targeted by the class thread which runs methods waiting in queue be run on the
        class thread.
        """
        while threading.main_thread().is_alive() or self._method_queue.qsize() != 0:
            try:
                method, args, kwargs, future = self._method_queue.get(timeout=1)
            except queue.Empty:
                # Ensures that the driver thread is not blocked forever if the main thread is killed while waiting.
                continue
            
            # Runs the method.
            try:
                future.set_result(method(*args, **kwargs))
            except DriveError as e:
                future.set_exception(e)

    @staticmethod
    def run_on_driver_thread(method: Callable[parameter_types, return_type]) -> Callable[parameter_types, Future]:
        """
        The decorator method which methods will be put into the class thread queue.
        """
        @functools.wraps(method)
        def wrapper(self: Self, *args, **kwargs) -> Future:
            future = Future()
            self._method_queue.put((method.__get__(self, type(self)), args, kwargs, future))
            return future
        return wrapper

    @staticmethod
    def ignored_if_awaiting_error_acknowledgement(method: Callable[parameter_types, return_type]) -> Callable[parameter_types, return_type | None]:
        @functools.wraps(method)
        def wrapper(self: Self, *args, **kwargs) -> return_type | None:
            if not self.awaiting_error_acknowledgement:
                return method(self, *args, **kwargs)
        return wrapper

    def send(self, request: IO.Request, MC_count: int | None = None, realtime_config_command_count: int | None = None, max_attemps: int = 5) -> IO.Translated_Response:
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
        self.datagram.send(request.get_binary(MC_count, realtime_config_command_count), self.IP)
        
        # Logging the send.
        self.logger.log(request.logging_level, f"Request sent: {request}.")

        try:
            # Wait for response (default timeout 2 seconds).
            response_raw = self.datagram.recieve(self.IP)
            
            # Reset attempt counter.
            self._send_attempt = 1

            # Translating the response.
            translated_response = request.response.translate_response(response_raw)
            
            # Logging the recieve.
            self.logger.log(request.logging_level, f"Response recieved: {translated_response}.")

            # Error handling.
            self._error_handler(translated_response)

            # Warning handling.
            self._warning_handler(translated_response)

            return translated_response
        except queue.Empty:
            self.logger.warning(f"Response timed out (2s) at attempt {self._send_attempt}/5.")
            if self._send_attempt < max_attemps:
                self._send_attempt += 1
                return self.send(request, MC_count, realtime_config_command_count, max_attemps)
            else:
                self.logger.critical(f"Unable to recieve.")
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

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
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
        self.logger.info(f"Homing procedure initiated.")

        # Confirms if the drive is ready to be homed.
        main_state = self.get_main_state()
        if self.send(IO.Request(IO.Response(state_var=True))).get('state_var').get('main_state') != 8:
            self.logger.error(f"Homing procedure failed: Not in correct state ({main_state} != 8).")
            return False

        # Sending home request.
        home_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True, home=True))
        self.send(home_request)

        # Waiting for homing to finish.
        is_homing_finished_request = IO.Request(IO.Response(state_var=True))
        is_homing_finished = lambda: self.send(is_homing_finished_request).get('state_var').get('homing_finished')
        if not self.wait_for_change(is_homing_finished, timeout, 1):
            self.logger.error(f"Homing procedure failed: Timed out ({timeout}s). Switching off drive.")
            self.send(IO.Request(IO.Response(), IO.Control_Word()))
            return False
        
        # Finialzing.
        home_off_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True))
        self.send(home_off_request)
        self.logger.info(f"Homing procedure completed.")
        return True

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
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
        self.logger.info(f"Switch on procedure initiated.")
        main_state = self.get_main_state()
        
        if main_state == 8:
            self.logger.info(f"Switch on procedure completed (already swicthed on).")
            return True
        if main_state != 2:
            # Requesting state 2.
            self.send(IO.Request(IO.Response(), IO.Control_Word()))

            # Waiting for main state to go state 2.
            if not self.wait_for_change(lambda: self.get_main_state() == 2, timeout=timeout, delay=0.2):
                self.logger.error(f"Switch on procedure failed: Timed out going to state 2 ({timeout}s). Current state is {self.get_main_state()}.")
                return False

            main_state = self.get_main_state()
        
        if main_state == 2:
            # Requesting state 8.        
            self.send(IO.Request(IO.Response(), IO.Control_Word(switch_on=True)))

            # Waiting for state 8.
            if not self.wait_for_change(lambda: self.get_main_state() == 8, timeout=timeout, delay=0.2):
                self.logger.error(f"Switch on procedure failed: Timed out going from state 2 to 8 ({timeout}s). Current state is {self.get_main_state()}.")
                return False
            
            # Finalizing.
            self.logger.info(f"Switch on procedure for completed.")
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
    
    def _error_handler(self, translated_response: IO.Translated_Response) -> None:
        error_code: int = translated_response.get('error_code')
        if error_code is not None and error_code != 0:
            self.logger.error(f"Error code {error_code} raised by drive. Drive awaiting error acknowledgement.")
            self.awaiting_error_acknowledgement = True
            raise DriveError(self, error_code)
        
    def _warning_handler(self, translated_response: IO.Translated_Response) -> None:
        """
        Ensures that the warning list within this class is up to date with the physical drives
        warning word.

        Parameters
        ----------
        translated_response : Translated_Response
            The translated response from the drive.
        """
        # Gets the new warning word.
        warning_words: list[IO.Responses.Warn_Word] = translated_response.get('warn_word')
        
        # Gets the already present and new warning bits (to make it easier for comparison).
        already_present_warning_bits = {warning_word['bit'] for warning_word in self.warning_words}
        new_warning_bits = {warning_word['bit'] for warning_word in warning_words}
        
        # Inserts new warnings into the warnings list if present.
        for new_warning_word in warning_words:
            if new_warning_word['bit'] not in already_present_warning_bits:
                self.warning_words.append(new_warning_word)
                self.logger.warning(f"{new_warning_word['name']}: {new_warning_word['meaning']}.")
        
        # Removes lifted warnings from the list.
        for i, already_present_warning in enumerate(self.warning_words):
            if already_present_warning['bit'] not in new_warning_bits:
                self.logger.info(f"Warning cleared: '{already_present_warning['name']}'.")
                self.warning_words.pop(i)