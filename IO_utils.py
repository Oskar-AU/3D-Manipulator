import struct
import socket

def get_socket() -> socket.socket:
    """
    Gets the socket to the driver and binds it.
    
    Returns
    -------
    socket.socket
        The socket to the driver.
    """
    main_port = 41136
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", main_port))
    return sock

def get_request_def(control_word: bool = False, MC_interface: bool = False, realtime_config: bool = False) -> bytes:
    """
    Gets the request definition bytes.

    Parameters
    ----------
    control_word : bool, optional
        If true the main state machine of the drive can be accessed.
    MC_interface : bool, optional
        If true a motion command can be sent.
    realtime_config : bool, optional
        If true parameters, variables, curves, error log, and command tables can be accessed. Also restart, start, stop
        of the drive can be initiated.
    
    Returns
    -------
    bytes
        4 byte request definition.
    """
    return struct.pack("I",
       #|Variable       |  |Bit position|
        (control_word    <<      0       ) |
        (MC_interface    <<      1       ) |
        (realtime_config <<      2       )
    )

def get_response_def(status_word: bool = False, state_var: bool = False, actual_pos: bool = False, demand_pos: bool = False,
                     current: bool = False, warm_word: bool = False, error_code: bool = False, monitoring_channel: bool = False,
                     realtime_config: bool = False) -> bytes:
    """
    Gets the response definition bytes.

    Parameters
    ----------
    status_word : bool, optional
        If true a 2 byte status word is requested in the response.
    state_var : bool, optional
        If true a 2 byte state variable is requested in the response.
    actual_pos : bool, optional
        If true the actual position as 4 bytes of the motor is requested in the response.
    demand_pos : bool, optional
        If true the demand position of the motor as 4 bytes is requested in the response.
    current : bool, optional
        If true the set current as 2 bytes is requested in the response.
    warm_word : bool, optional
        If true the warm word as 2 bytes is requested in the response.
    error_code : bool, optional
        If true the error code as 2 bytes is requested in the response.
    monitoring_channel : bool, optional
        If true the value of the monitored UPID set in the parameters of the drive is requested in the response.
    realtime_config : bool, optional
        If true the requested realtime parameter is returned.
    """
    return struct.pack("I",
       #|Variable           |  |Bit position|
        (status_word         <<      0       ) |
        (state_var           <<      1       ) |
        (actual_pos          <<      2       ) |
        (demand_pos          <<      3       ) |
        (current             <<      4       ) |
        (warm_word           <<      5       ) |
        (error_code          <<      6       ) |
        (monitoring_channel  <<      7       ) |
        (realtime_config     <<      8       )
    )
