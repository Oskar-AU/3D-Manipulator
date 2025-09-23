from .Drivers import Driver
from .Requests import Request
from .Responses import Translated_Response
import socket
import logging

logger = logging.getLogger(__name__)

class linUDP:

    def __init__(self) -> None:
        main_port = 41136
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", main_port))
        self.socket.settimeout(1.0)