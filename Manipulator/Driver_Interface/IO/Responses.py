import struct
from typing import TypedDict, Literal

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
    main_state:                         int
    error_code:                         int
    MC_count:                           int
    event_handler_active:               bool
    motion_active:                      bool
    in_target_position:                 bool
    homed:                              bool
    homing_finished:                    bool
    clerance_check_finished:            bool
    going_to_initial_position_finished: bool
    going_to_position_finished:         bool
    moving_positive:                    bool
    jogging_plus_finished:              bool
    moving_negative:                    bool
    jogging_negative_finished:          bool

class Warn_Word(TypedDict):
    bit:        int
    name:       str
    meaning:    str

Translated_Response = dict[Literal['status_word', 
                                   'state_var', 
                                   'actual_pos', 
                                   'demand_pos', 
                                   'current', 
                                   'warn_word', 
                                   'error_code', 
                                   'monitoring_channel', 
                                   'realtime_config'], Status_Word | State_Var | Warn_Word | float | int]

class Response:
    def __init__(self, status_word: bool = False, state_var: bool = False, actual_pos: bool = False, demand_pos: bool = False,
                 current: bool = False, warn_word: bool = False, error_code: bool = False, monitoring_channel: bool = False,
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
        warn_word : bool, optional
            If true the warm word as 2 bytes is requested in the response.
        error_code : bool, optional
            If true the error code as 2 bytes is requested in the response.
        monitoring_channel : bool, optional
            If true the value of the monitored UPID set in the parameters of the drive is requested in the response.
        realtime_config : bool, optional
            If true the requested realtime parameter is returned.
        """
        self.response_types_included: dict[str, bool] = {
            "status_word": status_word,
            "state_var": state_var,
            "actual_pos": actual_pos,
            "demand_pos": demand_pos,
            "current": current,
            "warn_word": warn_word,
            "error_code": error_code,
            "monitoring_channel": monitoring_channel,
            "realtime_config": realtime_config
        }

    def translate_response(self, response_raw: bytes) -> Translated_Response:
        response_unpacked: tuple[int] = struct.unpack("<LL" + self.format, response_raw)[2:]
        response_dict = dict()
        i = 0
        for response_name, response_type_included in self.response_types_included.items():
            if response_type_included:
                response_type_value = response_unpacked[i]
                match response_name:

                    case "status_word":
                        response_type_translated_value = Status_Word(
                            operation_enabled     = bool(response_type_value & (1 << 0 ) ),
                            switch_on_active      = bool(response_type_value & (1 << 1 ) ),
                            enable_operation      = bool(response_type_value & (1 << 2 ) ),
                            error                 = bool(response_type_value & (1 << 3 ) ),
                            voltage_enable        = bool(response_type_value & (1 << 4 ) ),
                            quick_stop            = bool(response_type_value & (1 << 5 ) ),
                            switch_on_locked      = bool(response_type_value & (1 << 6 ) ),
                            warning               = bool(response_type_value & (1 << 7 ) ),
                            event_handler_active  = bool(response_type_value & (1 << 8 ) ),
                            special_motion_active = bool(response_type_value & (1 << 9 ) ),
                            in_target_position    = bool(response_type_value & (1 << 10) ),
                            homed                 = bool(response_type_value & (1 << 11) ),
                            fatal_error           = bool(response_type_value & (1 << 12) ),
                            motion_active         = bool(response_type_value & (1 << 13) ),
                            range_indicator_1     = bool(response_type_value & (1 << 14) ),
                            range_indicator_2     = bool(response_type_value & (1 << 15) )
                        )

                    case "state_var":
                        sub_state, main_state = struct.unpack('BB', response_type_value)
                        match main_state:
                            case 3:     # Setup error.
                                response_type_translated_value = State_Var(main_state=main_state, 
                                    error_code                          =       sub_state
                                )
                            case 4:     # Error.
                                response_type_translated_value = State_Var(main_state=main_state, 
                                    error_code                          =       sub_state
                                )
                            case 8:     # Operation enabled.
                                response_type_translated_value = State_Var(main_state=main_state,
                                    MC_count                            =       sub_state & 0xf, 
                                    event_handler_active                = bool( sub_state & (1 << 4)), 
                                    motion_active                       = bool( sub_state & (1 << 5)),
                                    in_target_position                  = bool( sub_state & (1 << 6)),
                                    homed                               = bool( sub_state & (1 << 7))
                                )
                            case 9:     # Homing.
                                response_type_translated_value = State_Var(main_state=main_state,
                                    homing_finished                     =       sub_state == 0x0f
                                )
                            case 10:    # Clearance check.
                                response_type_translated_value = State_Var(main_state=main_state,
                                    clerance_check_finished             =       sub_state == 0x0f
                                )
                            case 11:    # Going to initial position.
                                response_type_translated_value = State_Var(main_state=main_state, 
                                    going_to_initial_position_finished  =       sub_state == 0x0f
                                )
                            case 15:    # Going to position.
                                response_type_translated_value = State_Var(main_state=main_state, 
                                    going_to_position_finished          =       sub_state == 0x0f
                                )
                            case 16:    # Jogging +.
                                response_type_translated_value = State_Var(main_state=main_state,
                                    moving_positive                     =       sub_state == 0x01, 
                                    jogging_plus_finished               =       sub_state == 0x0f
                                )
                            case 17:    # Jogging -.
                                response_type_translated_value = State_Var(main_state=main_state,
                                    moving_negative                     =       sub_state == 0x01, 
                                    jogging_negative_finished           =       sub_state == 0x0f
                                )
                            case _:     # Not ready to switch on (0)    | Switch on disabled (1)        | Ready to switch on (2)    | 
                                        # HW tests (5)                  | Ready to operate (6)          | Brake release delay (7)   | 
                                        # Aborting (12)                 | Freezing (13)                 | Quick stop (14)           | 
                                        # Linearizing (18)              | Phase search (19)             | Special mode (20)         | 
                                        # Brake delay (21).
                                response_type_translated_value = State_Var(main_state=main_state)
                    
                    case "actual_pos":
                        response_type_translated_value = response_type_value / 10000   # Converts from mym to mm.

                    case "demand_pos":
                        response_type_translated_value = response_type_value / 10000   # Converts from mym to mm.

                    case "current":
                        response_type_translated_value = response_type_value / 1000     # Converts from mA to A.

                    case "warn_word":
                        if   response_type_value & (1 << 0 ): 
                            response_type_translated_value = Warn_Word(
                                bit     =   0,
                                name    =   "Motor hot sensor", 
                                meaning =   "Motor temperature sensor on"
                            )
                        elif response_type_value & (1 << 1 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   1,
                                name    =   "Motor short time overload I^2t", 
                                meaning =   "Calculated motor temperature reached warn limit"
                            )
                        elif response_type_value & (1 << 2 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   2,
                                name    =   "Motor supply voltage low", 
                                meaning =   "Motor supply voltage reached low warn limit"
                            )
                        elif response_type_value & (1 << 3 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   3,
                                name    =   "Motor supply voltage high", 
                                meaning =   "Motor supplt voltage reached high warn limit"
                            )
                        elif response_type_value & (1 << 4 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   4,
                                name    =   "Position lag always", 
                                meaning =   "Position error during moving reached warn limit"
                            )
                        elif response_type_value & (1 << 6 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   6,
                                name    =   "Drive hot", 
                                meaning =   "Temperature on servo drive high"
                            )
                        elif response_type_value & (1 << 7 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   7,
                                name    =   "Motor not homed", 
                                meaning =   "Motor not homed yet"
                            )
                        elif response_type_value & (1 << 8 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   8,
                                name    =   "PTC sensor 1 hot", 
                                meaning =   "PTC temperature sensor 1 on"
                            )
                        elif response_type_value & (1 << 9 ):
                            response_type_translated_value = Warn_Word(
                                bit     =   9,
                                name    =   "Reserved PTC 2", 
                                meaning =   "PTC temperature sensor 2 on"
                            )
                        elif response_type_value & (1 << 10):
                            response_type_translated_value = Warn_Word(
                                bit     =   10,
                                name    =   "RR hot calculated", 
                                meaning =   "Regenerative resistor temperature hot calculated"
                            )
                        elif response_type_value & (1 << 11):
                            response_type_translated_value = Warn_Word(
                                bit     =   11,
                                name    =   "Speed lag always", 
                                meaning =   "Speed lag is above warn limit"
                            )
                        elif response_type_value & (1 << 12):
                            response_type_translated_value = Warn_Word(
                                bit     =   12,
                                name    =   "Position sensor", 
                                meaning =   "Position is in warn condition"
                            )
                        elif response_type_value & (1 << 14):
                            response_type_translated_value = Warn_Word(
                                bit     =   14,
                                name    =   "Interface warn flag", 
                                meaning =   "Warn flag of interface SW layer"
                            )
                        elif response_type_value & (1 << 15):
                            response_type_translated_value = Warn_Word(
                                bit     =   15,
                                name    =   "Application warn flag", 
                                meaning =   "Warn flag of application SW layer"
                            )

                    case "error_code":
                        response_type_translated_value = response_type_value

                    case "monitoring_channel":
                        raise NotImplementedError("Translating monitoring channel from response is not supported yet.")

                    case "realtime_config":
                        raise NotImplementedError("Translating realtime config from response is not supported yet.")

                response_dict.update({response_name: response_type_translated_value})
                i += 1

        return response_dict

    @property
    def format(self) -> str:
        format = "".join([
            "H"   if self.response_types_included['status_word'        ] else "",
            "2s"  if self.response_types_included['state_var'          ] else "",
            "i"   if self.response_types_included['actual_pos'         ] else "",
            "i"   if self.response_types_included['demand_pos'         ] else "",
            "h"   if self.response_types_included['current'            ] else "",   # Is current signed?
            "H"   if self.response_types_included['warn_word'          ] else "",
            "H"   if self.response_types_included['error_code'         ] else "",
            "16s" if self.response_types_included['monitoring_channel' ] else "",   # Format of monitoring channel depends on what the type of the selected UPID is.
            "8s"  if self.response_types_included['realtime_config'    ] else ""    # Format of realtime config arguments depend on the parameter command ID.
        ])
        
        # If the size of the response is less than 14 bytes (including request and response defs) 
        # padding is added up till 14 bytes. Documentation says padding is added up till 64 bytes 
        # but that is not the case.
        size = struct.calcsize(format)
        if size < 6:
            format += f"{6-size}x"
        return format

    @property
    def response_def(self) -> bytes:
        return struct.pack("<I",
            (self.response_types_included['status_word'        ]  <<      0       ) |
            (self.response_types_included['state_var'          ]  <<      1       ) |
            (self.response_types_included['actual_pos'         ]  <<      2       ) |
            (self.response_types_included['demand_pos'         ]  <<      3       ) |
            (self.response_types_included['current'            ]  <<      4       ) |
            (self.response_types_included['warn_word'          ]  <<      5       ) |
            (self.response_types_included['error_code'         ]  <<      6       ) |
            (self.response_types_included['monitoring_channel' ]  <<      7       ) |
            (self.response_types_included['realtime_config'    ]  <<      8       )
        )