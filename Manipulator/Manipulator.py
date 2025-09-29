from .Stream import Stream
from . import IO
from .Driver_Interface import Driver

class Manipulator:

    def __init__(self):
        self.datagram = IO.linUDP()
        self.drivers = (
            Driver('192.168.131.251', 'drive_1', self.datagram),
            Driver('192.168.131.252', 'drive_2', self.datagram),
            Driver('192.168.131.253', 'drive_3', self.datagram)
        )

    def home_all(self) -> None:
        for driver in self.drivers:
            driver.home()

    def switch_on_all(self) -> None:
        for driver in self.drivers:
            driver.switch_on()

    def send_defined_stream(self, stream: Stream | None = None, csv_file: str | None = None):
        pass