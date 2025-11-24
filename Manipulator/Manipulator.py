from .Stream import Stream
from . import IO
from .Driver_Interface import Driver, DriveError, Command_Parameters
from concurrent.futures import Future
import time
from typing import Any
import numpy as np
import numpy.typing as npt
import logging
from dataclasses import dataclass, field
from .Path_follower import Path_Base

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
    t: list = field(default_factory=list)                        # seconds
    positions_mm: list = field(default_factory=list)             # (3,)
    next_velocity_ms: list = field(default_factory=list)         # (3,)
    actual_velocities_ms: list = field(default_factory=list)     # (3,)
    enabled: bool = True                                         # Recording enable flag

    def start_recording(self):
        """Enable telemetry logging."""
        self.enabled = True

    def stop_recording(self):
        """Disable telemetry logging."""
        self.enabled = False

    def clear(self):
        """Clear recorded data."""
        self.t.clear()
        self.positions_mm.clear()
        self.next_velocity_ms.clear()
        self.actual_velocities_ms.clear()

    def append(self, t_s, positions_mm, next_velocity_ms, actual_velocities_ms):
        """
        Append one telemetry sample (only if enabled).
        
        Args:
            t_s: Time in seconds
            positions_mm: Current position [x, y, z] in mm
            next_velocity_ms: Next velocity command [vx, vy, vz] in m/s
            actual_velocities_ms: Measured velocity [vx, vy, vz] in m/s
        """
        if not self.enabled:
            return  # skip logging if disabled
        self.t.append(float(t_s))
        self.positions_mm.append(np.asarray(positions_mm, float).copy())
        self.next_velocity_ms.append(np.asarray(next_velocity_ms, float).copy())
        self.actual_velocities_ms.append(np.asarray(actual_velocities_ms, float).copy())

    def to_arrays(self):
        return (
            np.asarray(self.t),
            np.asarray(self.positions_mm),
            np.asarray(self.next_velocity_ms),
            np.asarray(self.actual_velocities_ms),
        )

class Manipulator:

    def __init__(self, driver_response_timeout: float = 2, driver_max_send_attempts: int = 5, enable_drive_1: bool = True, enable_drive_2: bool = True, enable_drive_3: bool = True):
        self.datagram = IO.linUDP()
        self.drivers: list[Driver] = []
        if enable_drive_1:
            self.drivers.append(
                Driver('192.168.131.251', 'DRIVE_1', self.datagram, driver_response_timeout, driver_max_send_attempts, (Command_Parameters.velocity_signed, None, None, None))
            )
        if enable_drive_2:
            self.drivers.append(
                Driver('192.168.131.252', 'DRIVE_2', self.datagram, driver_response_timeout, driver_max_send_attempts, (Command_Parameters.velocity_signed, None, None, None))
            )
        if enable_drive_3:
            self.drivers.append(
                Driver('192.168.131.253', 'DRIVE_3', self.datagram, driver_response_timeout, driver_max_send_attempts, (Command_Parameters.velocity_signed, None, None, None))
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

    def home(self) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.home()
        self._wait_for_response_on_all()

    def switch_on(self) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.switch_on()
        self._wait_for_response_on_all()

    def error_acknowledge(self, cascade: bool = True) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.acknowledge_error(cascade)
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
            acceleration = np.full_like(velocity, 1.0)
        else:
            acceleration = np.asarray(acceleration)
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.move_with_constant_velocity(velocity[i])
        positions, velocities = np.array(self._read_from_futures()).T
        return positions, velocities

    def feedback_loop(self, stepper: Path_Base, max_cycles: int = 20000, debug_interval: int = 50, telemetry: Telemetry | None = None) -> None:
       
        path_logger.info("Starting feedback loop with velocity tracking...")
        
        cycle_count = 0
        last_commanded_velocity = np.zeros(len(self.drivers))
        last_commanded_acceleration = np.ones(len(self.drivers))
        
        # Time tracking for telemetry
        t0 = time.time()
        
        while True:
            try:
                # Get current position and velocity state
                positions, actual_velocities = self.move_all_with_constant_velocity(last_commanded_velocity, last_commanded_acceleration)
        
                # Calculate next step
                next_velocity, complete = stepper(positions, actual_velocities)
                next_acceleration = np.ones(len(self.drivers))

                # Record telemetry 
                if telemetry is not None:
                    t_now = time.time() - t0
                    telemetry.append(t_now, positions, next_velocity, actual_velocities)
                
                if complete:
                    path_logger.info("Path following completed!")
                    self.move_all_with_constant_velocity([0]*len(self.drivers))
                    return
                
                last_commanded_velocity = next_velocity.copy()
                last_commanded_acceleration = next_acceleration.copy()
                
                # Debug output
                if cycle_count % debug_interval == 0:
                    path_logger.debug(f"Cycle {cycle_count}: pos={positions}, vel_cmd={next_velocity}, actual_vel={actual_velocities}.")
                
                cycle_count += 1
                if cycle_count > max_cycles:
                    path_logger.info(f"Max cycles of {max_cycles} cycles reached. Stopping drivers.")
                    self.move_all_with_constant_velocity([0]*len(self.drivers))
            
            except Exception as e1:
                logger = logging.getLogger('PATH')
                logger.info("Stopping drives.")
                try:
                    # Stopping drives if possibles.
                    for _, driver in enumerate(self.drivers):
                        driver.move_with_constant_velocity([0]*len(self.drivers))
                        return
                except Exception as e2:
                    logger.error("Failed to stop drives.")
                    raise e2
                raise e1
