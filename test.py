import socket
import struct
import IO_utils

driver_address = "192.168.131.252"
driver_port = 49360
main_port = 41136

sock = IO_utils.get_socket()
sock.settimeout(1.0)

request_def = IO_utils.get_request_def(
    control_word=True, 
    MC_interface=False, 
    realtime_config=False
)

response_def = IO_utils.get_response_def(
    status_word=True,
    state_var=False,
    actual_pos=False,
    demand_pos=False,
    current=False,
    warm_word=False,
    error_code=True,
    monitoring_channel=False,
    realtime_config=False
)

control_word = 0b0000000001000000
motion_command = bytes(32)
realtime_configuration = bytes(8)
request_package = request_def + response_def + struct.pack('H', control_word)

sock.sendto(request_package, (driver_address, driver_port))

try:
    response_package, addr = sock.recvfrom(64)
except socket.timeout:
    print("timed out")

print(len(response_package))
request_def, response_def, rest = struct.unpack("<4s4s6s", response_package)
# request_def, response_def, status_word, state_var, actual_pos, demand_position, current, warn_word, error_code, monitoring_channel, realtime_configuration = struct.unpack("2s2s4s4s2s2s2s16s8s22s", data)
print(addr)
print(request_def)
print(response_def)
print(rest)
# print(status_word)
# print(state_var)
# print(actual_pos)
# print(demand_position)
# print(current)
# print(warn_word)
# print(error_code)
# print(monitoring_channel)
# print(realtime_configuration)

