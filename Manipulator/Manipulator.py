from .Stream import Stream
from . import IO
from .Driver_Interface import Driver, DriveError, Command_Parameters
from concurrent.futures import Future
import time
import numpy as np
import numpy.typing as npt

class Manipulator:

    def __init__(self):
        self.datagram = IO.linUDP()
        self.drivers = (
            Driver('192.168.131.251', 'DRIVE_1', self.datagram, (Command_Parameters.velocity_signed, None, None, None)),
            Driver('192.168.131.252', 'DRIVE_2', self.datagram, (Command_Parameters.timer_value, None, None, None)),
            Driver('192.168.131.253', 'DRIVE_3', self.datagram)
        )
        self.futures: list[Future | None] = [None, None, None]

    def _wait_for_response_on_all(self) -> None:
        for future in self.futures:
            try:
                future.result()
            except DriveError:
                continue

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

    def move_with_constant_velocity(velocity: npt.ArrayLike) -> tuple[npt.NDArray, npt.NDArray]:
        velocity = np.asarray(velocity)



    def feedback(point_cloud: npt.ArrayLike, velocity: float, eps: float = 5e-4):
    
        P = np.asarray(point_cloud, float) * 1e-3  # mm -> m
        N = len(P)
        idx = 0  # next point

        def step(current_pos_m: np.ndarray):
            nonlocal idx

            # Skip already-reached points
            while idx < N and np.linalg.norm(P[idx] - current_pos_m) <= eps:
                idx += 1

            if idx >= N:
                return np.zeros(3, float), True

            target = P[idx]
            d = target - current_pos_m
            dist = float(np.linalg.norm(d))
            if dist <= eps or dist == 0.0:
                return np.zeros(3, float), (idx >= N)

            v_axis = (d / dist) * float(velocity)  # per-axis velocity in m/s
            return v_axis, False

        return step