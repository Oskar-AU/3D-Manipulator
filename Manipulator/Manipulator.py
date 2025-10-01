from .Stream import Stream
from . import IO
from .Driver_Interface import Driver, DriveError
from concurrent.futures import Future
import time

class Manipulator:

    def __init__(self):
        self.datagram = IO.linUDP()
        self.drivers = (
            Driver('192.168.131.251', 'DRIVE_1', self.datagram),
            Driver('192.168.131.252', 'DRIVE_2', self.datagram),
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
            next_cycle_time += stream.cycle_time
            stop_streaming, stream_values = stream.get_next_coordinate_set()
            for i, driver in enumerate(self.drivers):
                driver.stream(*stream_values[i])
            self._wait_for_response_on_all()
            time.sleep(next_cycle_time - time.time())
        
        # Stops the stream.
        for driver in self.drivers:
            driver.stop_stream()