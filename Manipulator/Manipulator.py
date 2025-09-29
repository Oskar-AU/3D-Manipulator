from . import IO, Stream
from .Driver_Interface import Driver

class Manipulator:

    def __init__(self):
        self.datagram = IO.linUDP()
        self.driver_1 = Driver('192.168.131.251', 'drive_1', self.datagram)
        self.driver_2 = Driver('192.168.131.252', 'drive_2', self.datagram)
        self.driver_3 = Driver('192.168.131.253', 'drive_3', self.datagram)

    def home_all(self) -> None:
        self.driver_1.home()
        self.driver_2.home()
        self.driver_3.home()

    def send_defined_stream(self, stream: Stream | None = None, csv_file: str | None = None):
        pass