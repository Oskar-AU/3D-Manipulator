import socket
import logging
import threading
import queue
from .Logger import logger

class linUDP:

    def __init__(self) -> None:
        main_port = 41136
        self.driver_port = 49360
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(("", main_port))

        self.response_queue: dict[str, queue.Queue] = dict()
        self._thread = threading.Thread(target=self.listen, name='listener_thread', daemon=True)
        self._thread.start()

    def listen(self) -> None:
        while True:
            response, addr = self.socket.recvfrom(256)
            try:
                self.response_queue[addr[0]].put(response)
            except KeyError:
                logger.warning(f"Unexpected package recieved from {addr[0]}:{addr[1]}.")

    def send(self, request: bytes, IP_address: str) -> None:
        self.socket.sendto(request, (IP_address, self.driver_port))
        if self.response_queue.get(IP_address) is None:
            self.response_queue.update({IP_address: queue.Queue()})

    def recieve(self, IP_address: str, timeout: float = 2.0) -> bytes:
        try:
            return self.response_queue[IP_address].get(timeout=timeout)
        except KeyError:
            logger.error(f"An interface tried to recieve from {IP_address} but no request has been sent to this address yet.")