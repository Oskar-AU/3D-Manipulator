import IO
from Motion_Commands import *
from Drivers import Drivers

connection = IO.Connection()

home_on_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True, home=True))
home_off_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True))

move_command = IO.Request(IO.Response(), MC_interface=VAI_go_to_pos(0, 0.1, 10, 10))

connection.send(move_command, Drivers.drive_2)
# connection.send(home_on_request, Drivers.drive_2)
# connection.send(home_on_request, Drivers.drive_3)
# connection.send(home_off_request, Drivers.drive_2)
# connection.send(home_off_request, Drivers.drive_3)