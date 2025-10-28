from .Stream import Stream
from . import IO
from .Driver_Interface import Driver, DriveError, Command_Parameters
from concurrent.futures import Future
import time
from typing import Any
import numpy as np
import numpy.typing as npt
import logging

path_logger = logging.getLogger("PATH")


class Manipulator:

    def __init__(self, driver_response_timeout: float = 2, driver_max_send_attempts: int = 5):
        self.datagram = IO.linUDP()
        self.drivers = (
            Driver('192.168.131.251', 'DRIVE_1', self.datagram, driver_response_timeout, driver_max_send_attempts, (Command_Parameters.velocity_signed, None, None, None)),
            Driver('192.168.131.252', 'DRIVE_2', self.datagram, driver_response_timeout, driver_max_send_attempts, (Command_Parameters.velocity_signed, None, None, None)),
            Driver('192.168.131.253', 'DRIVE_3', self.datagram, driver_response_timeout, driver_max_send_attempts, (Command_Parameters.velocity_signed, None, None, None))
        )
        self.futures: list[Future | None] = [None, None, None]

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

    def move_all_with_constant_velocity(self, velocity: npt.ArrayLike, acceleration: npt.ArrayLike = None) -> tuple[npt.NDArray, npt.NDArray]:
        velocity = np.asarray(velocity)
        if acceleration is None:
            acceleration = np.full_like(velocity, 1.0)  # Use safe default acceleration of 1.0 m/s²
        else:
            acceleration = np.asarray(acceleration)
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.move_with_constant_velocity(velocity[i])
        try:
            positions, velocities = np.array(self._read_from_futures()).T
        except Exception as e1:
            logger = logging.getLogger('PATH')
            logger.info("Stopping drives.")
            try:
                # Stopping drives if possibles.
                for i, driver in enumerate(self.drivers):
                    driver.move_with_constant_velocity([0, 0, 0])
            except Exception as e2:
                logger.error("Failed to stop drives.")
                raise e2

        return positions, velocities

    def path_with_velocity_tracking(self, step_function, phase_name: str = "Path Following", max_cycles: int = 10000, debug_interval: int = 50):
        path_logger.info(f"Starting {phase_name} with velocity tracking...")
        cycle_count = 0
        last_commanded_velocity_ms = np.zeros(3, float)  # Track our commanded velocity
        
        while True:
            try:
                # Get current position and velocity state
                try:
                    # Command the last velocity to maintain motion while getting state
                    positions_mm, actual_velocities_mm = self.move_all_with_constant_velocity(last_commanded_velocity_ms)
                    current_pos_m = positions_mm * 1e-3  # Convert to meters
                    current_vel_ms = actual_velocities_mm * 1e-3  # Convert to m/s
                except Exception as e:
                    path_logger.error(f"Error getting position/velocity: {e}")
                    self.error_acknowledge()
                    continue
                
                # Calculate next step using both position and velocity
                next_velocity_ms, complete = step_function(current_pos_m, current_vel_ms)
                
                if complete:
                    path_logger.info(f"{phase_name} completed!")
                    self.move_all_with_constant_velocity(np.zeros(3))  # Stop
                    return True
                
                # Store the calculated velocity for the NEXT cycle (no immediate execution)
                last_commanded_velocity_ms = next_velocity_ms.copy()
                
                # Debug output at specified intervals
                if cycle_count % debug_interval == 0:
                    path_logger.info(f"Cycle {cycle_count}: pos={positions_mm}, vel_cmd={next_velocity_ms}")
                
                cycle_count += 1
                if cycle_count > max_cycles:
                    path_logger.info(f"Timeout in {phase_name} after {max_cycles} cycles")
                    self.move_all_with_constant_velocity(np.zeros(3))
                    return False
                
            except Exception as e:
                path_logger.error(f"Error in {phase_name}: {e}")
                self.move_all_with_constant_velocity(np.zeros(3))
                return False