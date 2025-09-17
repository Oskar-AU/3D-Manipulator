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
    status_word=False,
    state_var=False,
    actual_pos=False,
    demand_pos=False,
    current=False,
    warm_word=False,
    error_code=False,
    monitoring_channel=False,
    realtime_config=False
)

control_word = 0b0000_1000_0000_0001

MC_MASTER_ID = 0x00
MC_SUB_ID = 0x1
MC_COUNT = 0x1
MC_HEADER = struct.pack("H", 0x010d)
MC_PAR1 = 130_0000
MC_PAR2 = 1_00000
MC_PAR3 = 1_000_000
MC_PAR4 = 1_000_000
MC_PARS = struct.pack("4I", MC_PAR1, MC_PAR2, MC_PAR3, MC_PAR4)
# MC_PARS = struct.pack("I", MC_PAR1)
MC = MC_HEADER + MC_PARS# + bytes(14)

request_package = request_def + response_def + struct.pack('H', control_word)
# request_package = request_def + response_def + struct.pack('H', control_word)

print(len(MC))
print(request_package)

sock.sendto(request_package, (driver_address, driver_port))

""" try:
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
# print(realtime_configuration) """

