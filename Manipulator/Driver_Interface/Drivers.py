from . import io, Motion_Commands, Realtime_Config_Commands
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

class Monitoring_Channel_Missing_Parameter_Error(Exception):
    def __init__(self, missing_parameter_name: str) -> None:
        message = f"Monitoring channel not configured correctly. Expected '{missing_parameter_name}' " + \
                   "but was not found. Check either driver or manipulator configuration."
        super().__init__(message)

class Driver:

    def __init__(self, 
                 IP: str, 
                 name: str, 
                 datagram: io.linUDP,
                 response_timeout: float,
                 max_send_attempts: int,
                 min_pos: float,
                 max_pos: float,
                 monitoring_channel_parameters: tuple[io.CommandParameter | None] = (None, None, None, None),
                 ) -> None:
        self.min_pos = min_pos
        self.max_pos = max_pos
        self.IP = IP
        self.name = name
        self.datagram = datagram
        self.response_timeout = response_timeout
        self.max_send_attempts = max_send_attempts
        if len(monitoring_channel_parameters) != 4: raise ValueError("Length of 'monitoring_channel_parameters' must be 4.")
        self.monitoring_channel_parameters = monitoring_channel_parameters
        self._send_attempt = 1
        self.awaiting_error_acknowledgement = False
        self._method_queue: queue.Queue[tuple[Callable, tuple[Any], dict[Any], Future]] = queue.Queue()
        self._thread = threading.Thread(target=self._run_method_queue, name=name)
        self._thread.start()
        self.logger = logging.getLogger(self.name)
        self.warning_words: list[io.responses.WarnWord] = list()
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
                method_result = method(*args, **kwargs)
            except Exception as e:
                future.set_exception(e)
            else:
                future.set_result(method_result)

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

    def send(self, request: io.Request) -> io.TranslatedResponse:
        """
        Parameters
        ----------
        request : Request
            The request to send to the drive.

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
        self.logger.log(request.logging_level, f"{request}.")
        self.logger.binary(f"Request binary: {package}.")

        try:
            # Wait for response (default timeout 2 seconds).
            response_raw = self.datagram.recieve(self.IP, self.response_timeout)
            
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
            self.logger.warning(f"Response timed out ({self.response_timeout}s) at attempt {self._send_attempt}/{self.max_send_attempts}.")
            if self._send_attempt < self.max_send_attempts:
                self._send_attempt += 1
                return self.send(request)
            else:
                self.logger.critical("Unable to recieve.")
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
        return self.send(io.Request(io.Response(state_var=True))).state_var.main_state

    def get_MC_count(self) -> int:
        self.logger.debug("Requesting MC_count.")
        MC_count = self.send(io.Request(io.Response(state_var=True))).state_var.MC_count
        return MC_count if MC_count is not None else 0

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def home(self, timeout: float = 30, overwrite_already_home_check: bool = False) -> bool:
        """
        Sends a command to home the LinMot motors. The drive must be in state 8.

        Parameters
        ----------
        timeout : float, optional
            The time (s) to wait before the homing procedure is considered failed. Default is 30s.
        overwrite_already_home_check : bool, optional
            Whether or not to initiate homing procedure if it is already homed.

        Returns
        -------
        bool
            Whether or not the procedure ended succesfully.
        """
        self.logger.info("Homing procedure initiated.")

        # Checks if the driver is already homed.
        state_var = self.send(io.Request(io.Response(state_var=True))).state_var
        if state_var.homed and not overwrite_already_home_check:
            self.logger.info("Homing procedure completed (already homed).")
            return True

        # Confirms if the drive is ready to be homed.
        main_state = self.get_main_state()
        if state_var.main_state != 8:
            self.logger.error(f"Homing procedure failed: Not in correct state ({main_state} != 8).")
            return False

        # Sending home request.
        home_request = io.Request(io.Response(), io.ControlWord(switch_on=True, home=True))
        self.send(home_request)

        # Waiting for homing to finish.
        is_homing_finished_request = io.Request(io.Response(state_var=True))
        is_homing_finished = lambda: self.send(is_homing_finished_request).state_var.homing_finished
        if not self.wait_for_change(is_homing_finished, timeout, 1):
            self.logger.error(f"Homing procedure failed: Timed out ({timeout}s). Switching off drive.")
            self.send(io.Request(io.Response(), io.ControlWord()))
            return False
        
        # Finialzing.
        home_off_request = io.Request(io.Response(), io.ControlWord(switch_on=True))
        self.send(home_off_request)
        self.logger.info("Homing procedure completed.")
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
        self.logger.info("Switch on procedure initiated.")
        main_state = self.get_main_state()
        
        if main_state == 8:
            self.logger.info("Switch on procedure completed (already swicthed on).")
            return True
        if main_state != 2:
            # Requesting state 2.
            self.send(io.Request(io.Response(), io.ControlWord()))

            # Waiting for main state to go state 2.
            if not self.wait_for_change(lambda: self.get_main_state() == 2, timeout=timeout, delay=0.2):
                self.logger.error(f"Switch on procedure failed: Timed out going to state 2 ({timeout}s). Current state is {self.get_main_state()}.")
                return False

            main_state = self.get_main_state()
        
        if main_state == 2:
            # Requesting state 8.        
            self.send(io.Request(io.Response(), io.ControlWord(switch_on=True)))

            # Waiting for state 8.
            if not self.wait_for_change(lambda: self.get_main_state() == 8, timeout=timeout, delay=0.2):
                self.logger.error(f"Switch on procedure failed: Timed out going from state 2 to 8 ({timeout}s). Current state is {self.get_main_state()}.")
                return False
            
            # Finalizing.
            self.logger.info("Switch on procedure completed.")
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
    
    def _error_handler(self, translated_response: io.TranslatedResponse) -> None:
        error_code: int = translated_response.error_code
        if error_code is not None and error_code != 0:
            self.logger.error(f"Error code {error_code} raised by drive.")
            self.awaiting_error_acknowledgement = True
            raise DriveError(self, error_code)
        
    def _warning_handler(self, translated_response: io.TranslatedResponse) -> None:
        """
        Ensures that the warning list within this class is up to date with the physical drives
        warning word.

        Parameters
        ----------
        translated_response : Translated_Response
            The translated response from the drive.
        """
        # Gets the new warning word.
        warning_words: list[io.responses.WarnWord] = translated_response.warn_word

        # Exit warning handler if the resonse didn't request a warning.        
        if warning_words is None: return None

        # Gets the already present and new warning bits (to make it easier for comparison).
        already_present_warning_bits = {warning_word.bit for warning_word in self.warning_words}
        new_warning_bits = {warning_word.bit for warning_word in warning_words}
        
        # Inserts new warnings into the warnings list if present.
        for new_warning_word in warning_words:
            if new_warning_word.bit not in already_present_warning_bits:
                self.warning_words.append(new_warning_word)
                self.logger.warning(f"{new_warning_word.name}: {new_warning_word.meaning}.")
        
        # Removes lifted warnings from the list.
        for i, already_present_warning in enumerate(self.warning_words):
            if already_present_warning.bit not in new_warning_bits:
                self.logger.info(f"Warning cleared: '{already_present_warning.name}'.")
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
                self.stream_request = io.Request(
                    MC_interface=Motion_Commands.P_Stream_With_Slave_Generated_Time_Stamp_and_Configured_Period_Time(0))
            case 'PV':
                self.stream_request = io.Request(
                    MC_interface=Motion_Commands.PV_Stream_With_Slave_Generated_Time_Stamp(0, 0))
            case 'PVA':
                self.stream_request = io.Request(
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
        self.send(io.Request(MC_interface=Motion_Commands.Stop_Streaming()))

    @run_on_driver_thread
    def acknowledge_error(self) -> None:
        self.logger.info("Acknowledging error(s).")
        
        # Getting current error.
        try:
            error_code = self.send(io.Request(io.Response(error_code=True, warn_word=False))).error_code
        except DriveError as e:
            error_code = e.error_code
        if error_code is None or error_code == 0:
            self.logger.info("No errors to acknowledge.")
            return

        while error_code is not None and error_code != 0:
            # Attempting to acknowledge error.
            self.logger.info(f"Attempting to acknowledge error code {error_code}.")
            self.send(io.Request(io.Response(error_code=False, warn_word=False), control_word=io.ControlWord(Error_acknowledge=True)))
            try:
                new_error_code = self.send(io.Request(io.Response(warn_word=False), control_word=io.ControlWord())).error_code
            except DriveError as e:
                new_error_code = e.error_code

            # Checking if driver raised same error again.
            if new_error_code == error_code:
                # If yes, exit.
                self.logger.error(f"Failed to acknowledge error code {error_code}.")
                return
            
            self.logger.info(f"Error code {error_code} acknowledged.")
            error_code = new_error_code

        self.awaiting_error_acknowledgement = False

    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def get_driver_time(self) -> float:
        realtime_config_cmd = Realtime_Config_Commands.Read_RAM_Value_of_Parameter_by_UPID(0x1CAF, io.linTypes.Uint32, 'slave timer value', 'mym')
        return self.send(io.Request(realtime_config=realtime_config_cmd)).realtime_config.values[1]
    
    @ignored_if_awaiting_error_acknowledgement
    def get_realtime_config_command_count(self) -> int:
        self.logger.debug("Requesting realtime_config count.")
        realtime_config_cmd = Realtime_Config_Commands.No_Operation()
        return self.send(io.Request(realtime_config=realtime_config_cmd)).realtime_config.command_count
    
    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def get_status_word(self) -> int:
        realtime_config_cmd = Realtime_Config_Commands.Read_RAM_Value_of_Parameter_by_UPID(0x1D51, io.linTypes.Uint16, 'status word', '-')
        return self.send(io.Request(realtime_config=realtime_config_cmd)).realtime_config.values[1]
    
    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def move_with_constant_velocity(self, velocity: float, acceleration: float = 10.0) -> tuple[float, float]:

        if velocity > 0.0 and acceleration > 0.0:
            motion_CMD = Motion_Commands.AccVAI_Infinite_Motion_Positive_Direction(velocity, acceleration)
        elif velocity < 0.0 and acceleration > 0.0:
            motion_CMD = Motion_Commands.AccVAI_Infinite_Motion_Negative_Direction(-velocity, acceleration)
        elif velocity > 0.0 and acceleration < 0.0:
            motion_CMD = Motion_Commands.AccVAI_Infinite_Motion_Positive_Direction(velocity, -acceleration)
        elif velocity < 0.0 and acceleration < 0.0:
            motion_CMD = Motion_Commands.AccVAI_Infinite_Motion_Negative_Direction(-velocity, -acceleration)
        else:
            motion_CMD = Motion_Commands.VAI_Stop()

        response_def = io.Response(actual_pos=True, monitoring_channel=True)
        request = io.Request(response_def, MC_interface=motion_CMD)
        response = self.send(request)

        try:
            return response.actual_pos, response.monitoring_channel['velocity']
        except KeyError:
            raise Monitoring_Channel_Missing_Parameter_Error('velocity')
        
    @run_on_driver_thread
    @ignored_if_awaiting_error_acknowledgement
    def go_to_pos(self, position: float, velocity: float, acceleration: float) -> tuple[float, float]:
        if velocity < 0.0 or acceleration < 0.0:
            self.logger.error("go_to_pos recieved signed velocity or acceleration.")
            raise ValueError("go_to_pos recieved signed velocity or acceleration.")
        motion_CMD = Motion_Commands.VAI_go_to_pos(position, velocity, acceleration, acceleration)
        response_def = io.Response(actual_pos=True, monitoring_channel=True)
        request = io.Request(response_def, MC_interface=motion_CMD)
        response = self.send(request)

        try:
            return response.actual_pos, response.monitoring_channel['velocity']
        except KeyError:
            raise Monitoring_Channel_Missing_Parameter_Error('velocity')