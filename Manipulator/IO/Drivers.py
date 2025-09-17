from typing import TypedDict

class Driver(TypedDict):
    address: str
    port: int

class Drivers:
    drive_1 = Driver(
        address = "192.168.131.251",
        port = 49360
    )
    drive_2 = Driver(
        address = "192.168.131.252",
        port = 49360
    )
    drive_3 = Driver(
        address = "192.168.131.253",
        port = 49360
    )
    all = Driver(
        address = "192.168.131.255",
        port = 49360
    )