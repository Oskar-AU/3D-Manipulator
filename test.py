import socket
import struct

main_address = "192.168.131.1"
driver_address = "192.168.131.252"
driver_port = 49360
main_port = 41136

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind((main_address, main_port))
sock.settimeout(1.0)

request_def = 0b00000000000000000000000000000001
response_def = 0b00000000000000000000000000000111
control_word = 0b0000000001000000
motion_command = bytes(32)
realtime_configuration = bytes(8)
data = struct.pack('<IIH', request_def, response_def, control_word)

sock.sendto(data, (driver_address, driver_port))

try:
    data, addr = sock.recvfrom(64)
    request_def, response_def, rest = struct.unpack("<4s4s8s", data)
    # request_def, response_def, status_word, state_var, actual_pos, demand_position, current, warn_word, error_code, monitoring_channel, realtime_configuration = struct.unpack("2s2s4s4s2s2s2s16s8s22s", data)
    print(addr)
    print(request_def)
    print(response_def)
    print(rest)
    print(len(data))
    # print(status_word)
    # print(state_var)
    # print(actual_pos)
    # print(demand_position)
    # print(current)
    # print(warn_word)
    # print(error_code)
    # print(monitoring_channel)
    # print(realtime_configuration)

except socket.timeout:
    print("timed out")