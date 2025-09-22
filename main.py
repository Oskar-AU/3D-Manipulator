from Manipulator import setup_logging
from Manipulator import IO

setup_logging()

datagram = IO.linUDP()

response_def = IO.Response(state_var=True, actual_pos=True)

request_def = IO.Request(response_def)

translated_response = datagram.sendto(request_def, IO.Drivers.drive_2)