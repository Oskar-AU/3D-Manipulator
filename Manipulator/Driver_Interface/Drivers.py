from . import IO, Motion_Commands, Realtime_Config_Commands
from typing import Callable, Self, Any, TypeVar, ParamSpec, Literal
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

    def __init__(self, IP: str, name: str, datagram: IO.linUDP, monitoring_channel_parameters: tuple[IO.Command_Parameter | None] = (None, None, None, None)) -> None:
        self.IP = IP
        self.name = name
        self.datagram = datagram
        if len(monitoring_channel_parameters) != 4: raise ValueError(f"Length of 'monitoring_channel_parameters' must be 4.")
        self.monitoring_channel_parameters = monitoring_channel_parameters
        self._send_attempt = 1
        self.awaiting_error_acknowledgement = False
        self._method_queue: queue.Queue[tuple[Callable, tuple[Any], dict[Any], Future]] = queue.Queue()
        self._thread = threading.Thread(target=self._run_method_queue, name=name)
        self._thread.start()
        self.logger = logging.getLogger(self.name)
        self.warning_words: list[IO.Responses.Warn_Word] = list()
        self.MC_count = 0
        self.realtime_config_command_count = 0
        self.MC_count_up_to_date = False
        self.realtime_config_count_up_to_date = False

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

    def send(self, request: IO.Request, max_attemps: int = 5) -> IO.Translated_Response:
        """
        Parameters
        ----------
        request : Request
            The request to send to the drive.
        MC_count : int, optional
            The count of the motion command. Must be different than the 
            previous motion command otherwise it is ignored by the drive.
        realtime_config_command_count : int, optional
            The count of the realtime config command. Must be different than the 
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
        # If the request is a motion command, ensure that the count is incremented and up to date.
        if request.MC_interface is not None:
            if not self.MC_count_up_to_date:
                self.MC_count = self.get_MC_count()
                self.MC_count_up_to_date = True
            self.MC_count += 1

        if request.realtime_config is not None:
            if not self.realtime_config_count_up_to_date:
                self.realtime_config_count_up_to_date = True
                self.realtime_config_command_count = self.get_realtime_config_command_count()
            self.realtime_config_command_count += 1

        # Maps the counts from 'python int' to Uint4 with overflow.
        mapped_MC_count = self.MC_count & 0xF
        mapped_realtime_config_command_count = self.realtime_config_command_count & 0xF

        # Sends the request.
        package = request.get_binary(mapped_MC_count, mapped_realtime_config_command_count)
        
        self.datagram.send(package, self.IP)

        # Logging the send.
        self.logger.log(request.logging_level, f"Request sent: {request}.")
        self.logger.binary(f"Request binary: {package}.")

        try:
            # Wait for response (default timeout 2 seconds).
            response_raw = self.datagram.recieve(self.IP)
            
            # Translating the response.
            translated_response = request.response.translate_response(response_raw, request.realtime_config, self.monitoring_channel_parameters)
            
            # Logging the recieve.
            self.logger.log(request.logging_level, f"Response recieved: {translated_response}.")
            self.logger.binary(f"Response binary: {response_raw}")
            
            # Warning handling.
            self._warning_handler(translated_response)

            # Error handling.
            self._error_handler(translated_response)
            
            # Reset attempt counter.
            self._send_attempt = 1

            return translated_response
        except queue.Empty:
            self.logger.warning(f"Response timed out (2s) at attempt {self._send_attempt}/5.")
            if self._send_attempt < max_attemps:
                self._send_attempt += 1
                return self.send(request, max_attemps)
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
        self.logger.debug("Requesting main state.")
        return self.send(IO.Request(IO.Response(state_var=True))).get('state_var').get('main_state')

    def get_MC_count(self) -> int:
        self.logger.debug("Requesting MC_count.")
        MC_count = self.send(IO.Request(IO.Response(state_var=True))).get('state_var').get('MC_count')
        return MC_count if MC_count is not None else 0

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
            self.logger.info(f"Switch on procedure completed.")
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

        # Exit warning handler if the resonse didn't request a warning.        
        if warning_words is None: return None

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

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def initialize_stream(self, stream_type: Literal['P', 'PV', 'PVA']) -> None:
        self.logger.info('Initializing stream.')

        # Ensuring that the drive is in an opereational state.
        main_state = self.get_main_state()
        if main_state != 8:
            self.logger.error(f"Drive not in correct state for streaming ({main_state != 8}).")

        self.stream_type: Literal['P', 'PV', 'PVA'] = stream_type
        match stream_type:
            case 'P':
                self.stream_request = IO.Request(
                    MC_interface=Motion_Commands.P_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(0))
            case 'PV':
                self.stream_request = IO.Request(
                    MC_interface=Motion_Commands.PV_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(0, 0))
            case 'PVA':
                self.stream_request = IO.Request(
                    MC_interface=Motion_Commands.PVA_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(0, 0, 0))
            case _:
                raise ValueError(f"Parameter 'stream_type' expected eiter 'P', 'PV', or 'PVA' but got {stream_type}.")

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def stream(self, target_position: float, target_velocity: float | None = None, target_acceleration: float | None = None) -> None:
        # Structure is for speed.
        match self.stream_type:
            case 'P':
                self.stream_request.MC_interface.set_MC_parameter_value(0, target_position)
            case 'PV':
                self.stream_request.MC_interface.set_MC_parameter_value(0, target_position)
                self.stream_request.MC_interface.set_MC_parameter_value(1, target_velocity)
            case 'PVA':
                self.stream_request.MC_interface.set_MC_parameter_value(0, target_position)
                self.stream_request.MC_interface.set_MC_parameter_value(1, target_velocity)
                self.stream_request.MC_interface.set_MC_parameter_value(2, target_acceleration)
            case _:
                raise ValueError
        self.send(self.stream_request)

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def stop_stream(self) -> None:
        self.send(IO.Request(MC_interface=Motion_Commands.Stop_Streaming()))

    @run_on_driver_thread
    def acknowledge_error(self) -> None:
        self.logger.info("Acknowledging error.")
        self.send(IO.Request(IO.Response(error_code=False, warn_word=False), control_word=IO.Control_Word(Error_acknowledge=True)))
        self.send(IO.Request(IO.Response(error_code=False, warn_word=False), control_word=IO.Control_Word()))
        self.awaiting_error_acknowledgement = False

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def get_driver_time(self) -> float:
        realtime_config_cmd = Realtime_Config_Commands.Read_RAM_Value_of_Parameter_by_UPID(0x1CAF, IO.linTypes.Uint32, 'slave timer value', 'mym')
        return self.send(IO.Request(realtime_config=realtime_config_cmd)).get('realtime_config').get('values')[1]
    
    @ignored_if_awaiting_error_acknowledgement
    def get_realtime_config_command_count(self) -> int:
        self.logger.debug("Requesting realtime_config count.")
        realtime_config_cmd = Realtime_Config_Commands.No_Operation()
        return self.send(IO.Request(realtime_config=realtime_config_cmd)).get('realtime_config').get('command_count')
    
    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def get_status_word(self) -> int:
        realtime_config_cmd = Realtime_Config_Commands.Read_RAM_Value_of_Parameter_by_UPID(0x1D51, IO.linTypes.Uint16, 'status word', '-')
        return self.send(IO.Request(realtime_config=realtime_config_cmd)).get('realtime_config').get('values')[1]
    
    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def move_with_constant_velocity(self, velocity: float) -> tuple[float, float]:
        
        RT_config_cmd = Realtime_Config_Commands.Read_RAM_Value_of_Parameter_by_UPID(
            UPID=0x1B8E,
            UPID_unit="mm/s",
            UPID_conversion_factor=1e-3,
            UPID_type=IO.linTypes.Sint32,
            UPID_description="Demand_velocty"
        )

        if velocity > 0.0:
            motion_CMD = Motion_Commands.AccVAI_Infinite_Motion_Positive_Direction(velocity)
        elif velocity < 0.0:
            motion_CMD = Motion_Commands.AccVAI_Infinite_Motion_Negative_Direction(-velocity)
        else:
            motion_CMD = Motion_Commands.VAI_Stop()

        response_def = IO.Response(realtime_config=True, actual_pos=True)
        request = IO.Request(response_def, MC_interface=motion_CMD, realtime_config=RT_config_cmd)
        response = self.send(request)
        
        return response.get('actual_pos'), response.get('realtime_config').get('values')[1]