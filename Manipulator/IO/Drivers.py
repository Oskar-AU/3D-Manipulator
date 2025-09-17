from typing import TypedDict

class Driver(TypedDict):
    IP: str
    port: int
    name: str

class Drivers:
    drive_1 = Driver(
        IP = "192.168.131.251",
        port = 49360,
        name = "drive_1"
    )
    drive_2 = Driver(
        IP = "192.168.131.252",
        port = 49360,
        name = "drive_2"
    )
    drive_3 = Driver(
        IP = "192.168.131.253",
        port = 49360,
        name = "drive_3"
    )
    all = Driver(
        IP = "192.168.131.255",
        port = 49360,
        name = "all"
    )