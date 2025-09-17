import struct
from typing import TypedDict

class Status_Word(TypedDict):
    operation_enabled:     bool
    switch_on_active:      bool
    enable_operation:      bool
    error:                 bool
    voltage_enable:        bool
    quick_stop:            bool
    switch_on_locked:      bool
    warning:               bool
    event_handler_active:  bool
    special_motion_active: bool
    in_target_position:    bool
    homed:                 bool
    fatal_error:           bool
    motion_active:         bool
    range_indicator_1:     bool
    range_indicator_2:     bool

class State_Var(TypedDict):
    pass

class Response:
    def __init__(self, status_word: bool = False, state_var: bool = False, actual_pos: bool = False, demand_pos: bool = False,
                 current: bool = False, warm_word: bool = False, error_code: bool = False, monitoring_channel: bool = False,
                 realtime_config: bool = False) -> bytes:
        """
        Defines a response by selecting which options the response should include.

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
        self.included = {
            "status_word": status_word,
            "state_var": state_var,
            "actual_pos": actual_pos,
            "demand_pos": demand_pos,
            "current": current,
            "warm_word": warm_word,
            "error_code": error_code,
            "monitoring_channel": monitoring_channel,
            "realtime_configreal": realtime_config
        }

    def translate_response(self, response_raw: bytes) -> dict:
        response_unpacked = struct.unpack("LL" + self.format, response_raw)[2:]
        i = 0
        response_dict = dict()
        for response_name, response_included in self.included.items():
            if response_included:
                match response_name:
                    case "status_word":
                        response_value = Status_Word(
                            operation_enabled     = bool(response_unpacked[i] & 0b0000000000000001),
                            switch_on_active      = bool(response_unpacked[i] & 0b0000000000000010),
                            enable_operation      = bool(response_unpacked[i] & 0b0000000000000100),
                            error                 = bool(response_unpacked[i] & 0b0000000000001000),
                            voltage_enable        = bool(response_unpacked[i] & 0b0000000000010000),
                            quick_stop            = bool(response_unpacked[i] & 0b0000000000100000),
                            switch_on_locked      = bool(response_unpacked[i] & 0b0000000001000000),
                            warning               = bool(response_unpacked[i] & 0b0000000010000000),
                            event_handler_active  = bool(response_unpacked[i] & 0b0000000100000000),
                            special_motion_active = bool(response_unpacked[i] & 0b0000001000000000),
                            in_target_position    = bool(response_unpacked[i] & 0b0000010000000000),
                            homed                 = bool(response_unpacked[i] & 0b0000100000000000),
                            fatal_error           = bool(response_unpacked[i] & 0b0001000000000000),
                            motion_active         = bool(response_unpacked[i] & 0b0010000000000000),
                            range_indicator_1     = bool(response_unpacked[i] & 0b0100000000000000),
                            range_indicator_2     = bool(response_unpacked[i] & 0b1000000000000000)
                        )
                    case "state_var":
                        pass
                response_dict.update({response_name: response_unpacked[i]}) 

    @property
    def format(self) -> str:
        format = "".join([
            "H"   if self.included['status_word'        ] else "",
            "H"   if self.included['state_var'          ] else "",
            "I"   if self.included['actual_pos'         ] else "",
            "I"   if self.included['demand_pos'         ] else "",
            "H"   if self.included['current'            ] else "",
            "H"   if self.included['warm_word'          ] else "",
            "H"   if self.included['error_code'         ] else "",
            "16c" if self.included['monitoring_channel' ] else "",
            "Q"   if self.included['realtime_config'    ] else ""
        ])
        size = struct.calcsize(format)
        if size < 6:
            format += f"{6-size}x"
        return format

    @property
    def response_def(self) -> bytes:
        return struct.pack("I",
            (self.included['status_word'        ]  <<      0       ) |
            (self.included['state_var'          ]  <<      1       ) |
            (self.included['actual_pos'         ]  <<      2       ) |
            (self.included['demand_pos'         ]  <<      3       ) |
            (self.included['current'            ]  <<      4       ) |
            (self.included['warm_word'          ]  <<      5       ) |
            (self.included['error_code'         ]  <<      6       ) |
            (self.included['monitoring_channel' ]  <<      7       ) |
            (self.included['realtime_config'    ]  <<      8       )
        )