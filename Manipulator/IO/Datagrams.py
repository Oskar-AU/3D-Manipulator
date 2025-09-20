from .Drivers import Driver
from .Requests import Request
from .Responses import Translated_Response
import socket

class linUDP:

    def __init__(self) -> None:
        main_port = 41136
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", main_port))
        self.socket.settimeout(1.0)

    def sendto(self, request: Request, driver: Driver, MC_count: int | None = None) -> Translated_Response | None:
        """
        Parameters
        ----------
        request : Request
            ...
        driver : Driver
            ...
        MC_count : int, optional
            The count of the motion command (4 bits). Must be different than the 
            previous motion command otherwise it is ignored by the drive.
        """
        # print(struct.unpack("2IH4I", request.binary))
        print(request.get_binary(MC_count))
        self.socket.sendto(request.get_binary(MC_count), (driver['IP'], driver['port']))
        try:
            response_raw, response_address = self.socket.recvfrom(64)
            response_IP, _ = response_address
            if response_IP != driver['IP']:
                raise ValueError
            return request.response.translate_response(response_raw)

        except socket.timeout:
            print("timed out")