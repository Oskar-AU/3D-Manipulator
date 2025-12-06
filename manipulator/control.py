from .Stream import Stream
from . import io
from .hardware import Driver, DriveError, CommandParameters
from concurrent.futures import Future
import time
from typing import Any
import numpy as np
import numpy.typing as npt
import logging
from dataclasses import dataclass, field
from .Path_follower import Path_Base
from pathlib import Path
import pandas as pd

path_logger = logging.getLogger("PATH")


@dataclass
class Telemetry:
    """
    Telemetry data recording for 3D manipulator motion analysis.
    
    Data alignment: All arrays are temporally aligned at sample time t[i]:
    - positions_mm[i]: Current position at time t[i]
    - next_velocity_ms[i]: Velocity command that will be executed at time t[i]
    - actual_velocities_ms[i]: Measured velocity at time t[i]
    
    This ensures proper alignment for velocity tracking analysis.
    """
    data: dict[str, list[Any]] = field(default_factory=dict)
    # t: list = field(default_factory=list)                        # seconds
    # positions_mm: list = field(default_factory=list)             # (3,)
    # next_velocity_ms: list = field(default_factory=list)         # (3,)
    # actual_velocities_ms: list = field(default_factory=list)     # (3,)
    enabled: bool = True                                         # Recording enable flag

    def start_recording(self):
        """Enable telemetry logging."""
        self.enabled = True

    def stop_recording(self):
        """Disable telemetry logging."""
        self.enabled = False

    def append(self, key: str, value: Any) -> None:
        """
        Append one telemetry sample (only if enabled).
        
        """
        if not self.enabled:
            return  # skip logging if disabled
        if self.data.get(key) is None:
            self.data.update({key: [value]})
        else:
            self.data[key].append(value)

    def export_to_csv(self, path: Path | str) -> None:
        df = pd.DataFrame()
        for key, value in self.data.items():
            value = np.asarray(value)
            if value.ndim == 1:
                df[key] = value
            elif value.ndim == 2:
                for i, column in enumerate(value.T):
                    df[f"{key}_{i}"] = column
            else:
                raise ValueError(f"Cannot export data structure with dim {value.ndim}.")
        df.to_csv(path, index=False)

class Controller:

    def __init__(self, driver_response_timeout: float = 2, driver_max_send_attempts: int = 5, enable_drive_1: bool = True, enable_drive_2: bool = True, enable_drive_3: bool = True):
        """
        Controller for the 3D manipulator. Handles any high-level commands sent to the linMot drivers that depends on feedback between drivers. 
        Some methods are however just wrappers from the Driver class such as 'home' and 'switch_on' to allow the same command to be sent to all
        drivers.

        Parameters
        ----------
        driver_response_timeout : float, optional
            The response timeout for all drivers.
        driver_max_send_attempts : int, optional
            The maximum number of send attempts before communication is considered lost.
        enable_drive_1 : bool, optional
            Whether or not to enable driver 1. Default True.
        enable_drive_2 : bool, optional
            Whether or not to enable driver 2. Default True.
        enable_drive_3 : bool, optional
            Whether or not to enable driver 3. Default True.

        Attributes
        ----------
        datagram : io.linUDP
            The datagram used for communication to all drivers.
        drivers : list[Driver]
            All the drivers controlled by this controller.
        futures : list[Future | None]
            List with the same size as the number of enabled drivers that contains the Future
            objects from the results of the latest command sent to all drivers. Used when
            calling multithreaded Driver-class methods.

        """
        self.datagram = io.linUDP()
        self.drivers: list[Driver] = []
        if enable_drive_1:
            self.drivers.append(
                Driver('192.168.131.251', 
                    'DRIVE_1', 
                    datagram=self.datagram, 
                    response_timeout=driver_response_timeout, 
                    max_send_attempts=driver_max_send_attempts, 
                    min_pos=0,
                    max_pos=0.185,
                    monitoring_channel_parameters=(CommandParameters.velocity_signed, None, None, None),
                )
            )
        if enable_drive_2:
            self.drivers.append(
                Driver('192.168.131.252', 
                    'DRIVE_2', 
                    datagram=self.datagram, 
                    response_timeout=driver_response_timeout, 
                    max_send_attempts=driver_max_send_attempts, 
                    min_pos=0,
                    max_pos=0.18,
                    monitoring_channel_parameters=(CommandParameters.velocity_signed, None, None, None),
                )
            )
        if enable_drive_3:
            self.drivers.append(
                Driver('192.168.131.253', 
                    'DRIVE_3', 
                    datagram=self.datagram, 
                    response_timeout=driver_response_timeout, 
                    max_send_attempts=driver_max_send_attempts, 
                    min_pos=None,
                    max_pos=None,
                    monitoring_channel_parameters=(CommandParameters.velocity_signed, None, None, None),
                )
            )
        self.futures: list[Future | None] = [None]*len(self.drivers)
        
    def _wait_for_response_on_all(self) -> None:
        for future in self.futures:
            try:
                future.result()
            except DriveError:
                continue

    def _read_from_futures(self) -> list[Any]:
        return [future.result() for future in self.futures]

    def home(self, timeout: float = 30.0, overwrite_already_homed_check: bool = False) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.home(timeout, overwrite_already_homed_check)
        self._wait_for_response_on_all()

    def switch_on(self) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.switch_on()
        self._wait_for_response_on_all()

    def error_acknowledge(self) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.acknowledge_error()
        self._wait_for_response_on_all()

    def start_stream(self, stream: Stream) -> None:
    
        # Initializing the driver interfaces for stream mode.
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.initialize_stream(stream.type)
        
        self._wait_for_response_on_all()
        
        # Runs the streaming loop.
        next_cycle_time = time.time()
        stop_streaming = False
        while not stop_streaming:
            next_cycle_time += stream.cycle_time
            stop_streaming, stream_values = stream.get_next_coordinate_set()
            for i, driver in enumerate(self.drivers):
                driver.stream(*stream_values[i])
            self._wait_for_response_on_all()
            while next_cycle_time - time.time() > 0:
                time.sleep(next_cycle_time - time.time())
        
        # Stops the stream.
        for driver in self.drivers:
            driver.stop_stream()

    def move_all_with_constant_velocity(self, velocity: npt.ArrayLike, acceleration: npt.ArrayLike | None = None) -> tuple[npt.NDArray, npt.NDArray]:
        velocity = np.asarray(velocity)
        if acceleration is None:
            acceleration = np.full_like(velocity, 10.0)
        else:
            acceleration = np.asarray(acceleration)
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.move_with_constant_velocity(velocity[i], acceleration[i])
        positions, velocities = np.array(self._read_from_futures()).T
        return positions, velocities

    def go_to_pos(self, position: npt.ArrayLike, velocity: npt.ArrayLike, acceleration: npt.ArrayLike | None = None) -> tuple[npt.NDArray, npt.NDArray]:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.go_to_pos(position[i], velocity[i], acceleration[i])
        return np.array(self._read_from_futures()).T

    def feedback_loop(self, stepper: Path_Base, max_cycles: int | None = None, debug_interval: int = 1, telemetry: Telemetry | None = None) -> None:
       
        path_logger.info("Starting feedback loop with velocity tracking...")
        
        cycle_count = 0
        last_commanded_velocity = np.zeros(len(self.drivers))
        last_commanded_acceleration = np.ones(len(self.drivers))*3
        
        # Time tracking for telemetry
        t0 = time.time()
        
        while True:
            try:
                # Get current position and velocity state
                position = np.empty(len(self.drivers))
                for i, driver in enumerate(self.drivers):
                    position[i] = driver.min_pos if last_commanded_velocity[i] < 0.0 else driver.max_pos
                positions, actual_velocities = self.go_to_pos(
                    position,
                    np.abs(last_commanded_velocity), 
                    np.abs(last_commanded_acceleration)
                )
        
                # Calculate next step
                next_velocity, next_acceleration, complete = stepper(positions, actual_velocities)
                next_acceleration = np.abs(next_acceleration)

                # Record telemetry 
                if telemetry is not None:
                    t_now = time.time() - t0
                    telemetry.append('t', t_now)
                    telemetry.append('positions', positions)
                    telemetry.append('next_demand_velocity', next_velocity)
                    telemetry.append('actual_velocity', actual_velocities)
                
                if complete:
                    path_logger.info("Path following completed!")
                    self.move_all_with_constant_velocity([0]*len(self.drivers))
                    return
                
                last_commanded_velocity = next_velocity.copy()
                last_commanded_acceleration = next_acceleration.copy()
                
                # Debug output
                if cycle_count % debug_interval == 0:
                    path_logger.debug(f"Cycle {cycle_count}: current_pos={positions}, cmd_vel={next_velocity}, actual_vel={actual_velocities}.")
                
                cycle_count += 1

                if cycle_count is not None and max_cycles is not None and cycle_count > max_cycles:
                    path_logger.info(f"Max cycles of {max_cycles} cycles reached. Stopping drivers.")
                    self.move_all_with_constant_velocity([0]*len(self.drivers))
                    return
            
            except Exception as e1:
                logger = logging.getLogger('PATH')
                logger.info("Stopping drives.")
                try:
                    # Stopping drives if possibles.
                    for _, driver in enumerate(self.drivers):
                        driver.move_with_constant_velocity([0]*len(self.drivers))
                        raise e1
                except Exception as e2:
                    logger.error("Failed to stop drives.")
                    raise e2