from Manipulator import IO

datagram = IO.linUDP()

home_on_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True, home=True))
home_off_request = IO.Request(IO.Response(), IO.Control_Word(switch_on=True))

get_state_var = IO.Request(IO.Response(state_var=True, status_word=True, warm_word=True))

move_command = IO.Request(IO.Response(), MC_interface=IO.Motion_Commands.VAI_go_to_pos(50, 0.1, 10, 10))

datagram.sendto(get_state_var, IO.Drivers.drive_3)
# connection.send(move_command, IO.Drivers.drive_2, MC_count=2)
# connection.send(home_on_request, Drivers.all)
# connection.send(home_on_request, Drivers.drive_2)
# connection.send(home_on_request, Drivers.drive_3)
# connection.send(home_off_request, Drivers.all)
# connection.send(home_off_request, Drivers.drive_3)