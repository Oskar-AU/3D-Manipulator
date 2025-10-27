from .Stream import Stream
from . import IO
from .Driver_Interface import Driver, DriveError, Command_Parameters
from concurrent.futures import Future
import time
from typing import Any
import numpy as np
import numpy.typing as npt

class Manipulator:

    def __init__(self):
        self.datagram = IO.linUDP()
        self.drivers = (
            Driver('192.168.131.251', 'DRIVE_1', self.datagram, (Command_Parameters.velocity_signed, None, None, None)),
            Driver('192.168.131.252', 'DRIVE_2', self.datagram, (Command_Parameters.velocity_signed, None, None, None)),
            Driver('192.168.131.253', 'DRIVE_3', self.datagram, (Command_Parameters.velocity_signed, None, None, None))
        )
        self.futures: list[Future | None] = [None, None, None]

    def _wait_for_response_on_all(self) -> list[Any]:
        results = []
        for future in self.futures:
            try:
                result = future.result()
                results.append(result)
            except DriveError as e:
                print(f"Drive error occurred: {e}")
                # Return last known good position and zero velocity for failed drive
                results.append((0.0, 0.0))  # (position, velocity) placeholder
        return results

    def home(self) -> None:
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.home()
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
            cycle_time = stream.cycle_time
            next_cycle_time += cycle_time
            current_time = time.time()
            stop_streaming, stream_values = stream.get_next_coordinate_set()
            for i, driver in enumerate(self.drivers):
                driver.stream(*stream_values[i])
            self._wait_for_response_on_all()
            sleep_time = next_cycle_time - time.time()
            time.sleep(sleep_time)
            print(cycle_time, time.time()-current_time)
        
        # Stops the stream.
        for driver in self.drivers:
            driver.stop_stream()

    def move_all_with_constant_velocity(self, velocity: npt.ArrayLike) -> tuple[npt.NDArray, npt.NDArray]:
        velocity = np.asarray(velocity)
        for i, driver in enumerate(self.drivers):
            self.futures[i] = driver.move_with_constant_velocity(velocity[i])
        positions, velocities = np.array(self._wait_for_response_on_all()).T
        return positions, velocities


    def execute_path_with_velocity_tracking(self, step_function, phase_name: str = "Enhanced path execution", 
                                          max_cycles: int = 10000, debug_interval: int = 50):
        print(f"Starting {phase_name} with velocity tracking...")
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
                    print(f"Error getting position/velocity: {e}")
                    self.error_acknowledge()
                    continue
                
                # Calculate next step using both position and velocity
                next_velocity_ms, complete = step_function(current_pos_m, current_vel_ms)
                
                if complete:
                    print(f"{phase_name} completed!")
                    self.move_all_with_constant_velocity(np.zeros(3))  # Stop
                    return True
                
                # Execute velocity command and track it
                self.move_all_with_constant_velocity(next_velocity_ms)
                last_commanded_velocity_ms = next_velocity_ms.copy()
                
                if cycle_count > max_cycles:
                    print(f"Timeout in {phase_name} after {max_cycles} cycles")
                    self.move_all_with_constant_velocity(np.zeros(3))
                    return False
                
            except Exception as e:
                print(f"Error in {phase_name}: {e}")
                self.move_all_with_constant_velocity(np.zeros(3))
                return False
    
    def cleanup(self):
        """Cleanup manipulator resources."""
        try:
            # Stop all motion
            self.move_all_with_constant_velocity(np.zeros(3))
        except Exception:
            pass
        
        try:
            # Close datagram socket
            if hasattr(self, 'datagram'):
                self.datagram.close()
        except Exception:
            pass
    
    def __del__(self):
        """Cleanup when manipulator is destroyed."""
        self.cleanup()
    
   