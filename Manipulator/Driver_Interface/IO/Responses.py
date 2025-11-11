import struct
from typing import Any
from .Commands import Realtime_Config
from .Commands import Command_Parameter
from dataclasses import dataclass, fields

class Response_Base:
    def __repr__(self) -> str:
        initialized_fields = []
        for field in fields(self):
            field_value = getattr(self, field.name)
            if field_value is not None:
                initialized_fields.append(f"{field.name}={field_value}")
        return "(" + ", ".join(initialized_fields) + ")"

@dataclass(repr=False)
class Status_Word(Response_Base):
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

@dataclass(repr=False)
class State_Var(Response_Base):
    main_state:                         int
    error_code:                         int | None = None
    MC_count:                           int | None = None
    event_handler_active:               bool | None = None
    motion_active:                      bool | None = None
    in_target_position:                 bool | None = None
    homed:                              bool | None = None
    homing_finished:                    bool | None = None
    clerance_check_finished:            bool | None = None
    going_to_initial_position_finished: bool | None = None
    going_to_position_finished:         bool | None = None
    moving_positive:                    bool | None = None
    jogging_plus_finished:              bool | None = None
    moving_negative:                    bool | None = None
    jogging_negative_finished:          bool | None = None

@dataclass(repr=False)
class Warn_Word(Response_Base):
    bit:        int
    name:       str
    meaning:    str

@dataclass(repr=False)
class Realtime_Config_Response(Response_Base):
    status_number: int
    status_description: str
    details: tuple[Command_Parameter]
    values: tuple[int]
    command_count: int

@dataclass(repr=False)
class Translated_Response(Response_Base):
    status_word: Status_Word | None = None
    state_var: State_Var | None = None
    actual_pos: float | None = None
    demand_pos: float | None = None
    current: float | None = None
    warn_word: list[Warn_Word] | None = None
    error_code: int | None = None
    monitoring_channel: dict[str, Any] | None = None
    realtime_config: Realtime_Config_Response | None = None

class Response:
    def __init__(self, status_word: bool = False, state_var: bool = False, actual_pos: bool = False, demand_pos: bool = False,
                 current: bool = False, warn_word: bool = True, error_code: bool = True, monitoring_channel: bool = False,
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
            If true the warm word as 2 bytes is requested in the response (Default true).
        error_code : bool, optional
            If true the error code as 2 bytes is requested in the response (Default true).
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

    def translate_response(self, response_raw: bytes, realtime_config_command: Realtime_Config | None, monitoring_channel_parameters: tuple[Command_Parameter | None]) -> Translated_Response:
        # Sets the realtime_config as included if the request included a realtime config command.
        self.response_types_included['realtime_config'] = True if realtime_config_command is not None else False
        
        response_raw_format = "<LL" + self.get_format(realtime_config_command)
        response_raw_length = struct.calcsize(response_raw_format)
        # Only unpacking the expected length of the raw response, which is usually the same as the length of the raw response
        # but realtime config commands can apparently respond with bytes from the previous response, giving more values than
        # expected. Might be problematic for debugging when a response is wrongly translated.
        response_unpacked: tuple[int] = struct.unpack(response_raw_format, response_raw[:response_raw_length])[2:]
        translated_response = Translated_Response()
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
                        response_type_translated_value = response_type_value / 10000000  # Converts from 0.1 mym to 1.0 m.

                    case "demand_pos":
                        response_type_translated_value = response_type_value / 10000000  # Converts from 0.1 mym to 1.0 m.

                    case "current":
                        response_type_translated_value = response_type_value / 1000      # Converts from mA to A.

                    case "warn_word":
                        response_type_translated_value = list()
                        if   response_type_value & (1 << 0 ): 
                            response_type_translated_value.append(Warn_Word(
                                bit     =   0,
                                name    =   "Motor hot sensor", 
                                meaning =   "Motor temperature sensor on"
                            ))
                        if response_type_value & (1 << 1 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   1,
                                name    =   "Motor short time overload I^2t", 
                                meaning =   "Calculated motor temperature reached warn limit"
                            ))
                        if response_type_value & (1 << 2 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   2,
                                name    =   "Motor supply voltage low", 
                                meaning =   "Motor supply voltage reached low warn limit"
                            ))
                        if response_type_value & (1 << 3 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   3,
                                name    =   "Motor supply voltage high", 
                                meaning =   "Motor supplt voltage reached high warn limit"
                            ))
                        if response_type_value & (1 << 4 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   4,
                                name    =   "Position lag always", 
                                meaning =   "Position error during moving reached warn limit"
                            ))
                        if response_type_value & (1 << 6 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   6,
                                name    =   "Drive hot", 
                                meaning =   "Temperature on servo drive high"
                            ))
                        if response_type_value & (1 << 7 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   7,
                                name    =   "Motor not homed", 
                                meaning =   "Motor not homed yet"
                            ))
                        if response_type_value & (1 << 8 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   8,
                                name    =   "PTC sensor 1 hot", 
                                meaning =   "PTC temperature sensor 1 on"
                            ))
                        if response_type_value & (1 << 9 ):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   9,
                                name    =   "Reserved PTC 2", 
                                meaning =   "PTC temperature sensor 2 on"
                            ))
                        if response_type_value & (1 << 10):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   10,
                                name    =   "RR hot calculated", 
                                meaning =   "Regenerative resistor temperature hot calculated"
                            ))
                        if response_type_value & (1 << 11):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   11,
                                name    =   "Speed lag always", 
                                meaning =   "Speed lag is above warn limit"
                            ))
                        if response_type_value & (1 << 12):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   12,
                                name    =   "Position sensor", 
                                meaning =   "Position is in warn condition"
                            ))
                        if response_type_value & (1 << 14):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   14,
                                name    =   "Interface warn flag", 
                                meaning =   "Warn flag of interface SW layer"
                            ))
                        if response_type_value & (1 << 15):
                            response_type_translated_value.append(Warn_Word(
                                bit     =   15,
                                name    =   "Application warn flag", 
                                meaning =   "Warn flag of application SW layer"
                            ))

                    case "error_code":
                        response_type_translated_value = response_type_value

                    case "monitoring_channel":
                        format = ""
                        for parameter in monitoring_channel_parameters:
                            if parameter is not None:
                                format += parameter.type.format
                            else:
                                format += "4x"
                        monitoring_channel_values = struct.unpack(format, response_type_value)
                        response_type_translated_value = dict()
                        for i, monitoring_channel_parameter in enumerate(monitoring_channel_parameters):
                            if monitoring_channel_parameter is not None:
                                response_type_translated_value.update({
                                    monitoring_channel_parameter.description: monitoring_channel_values[i] / monitoring_channel_parameter.conversion_factor
                                })

                    case "realtime_config":
                        if realtime_config_command is None: raise ValueError(f"realtime_config is flagged for the response but is not in the request.")
                        command_count, parameter_channel_status, *DI_values = struct.unpack(realtime_config_command.DI_format, response_type_value)
                        match parameter_channel_status:
                            case 0x00:
                                parameter_status_description = "OK, done"
                            case 0x02:
                                parameter_status_description = "Command running / busy"
                            case 0x04:
                                parameter_status_description = "Block not finished (curve selection)"
                            case 0x05:
                                parameter_status_description = "Busy"
                            case 0xC0:
                                parameter_status_description = "UPID Error"
                            case 0xC1:
                                parameter_status_description = "Parameter type error"
                            case 0xC2:
                                parameter_status_description = "Range error"
                            case 0xC3:
                                parameter_status_description = "Address usage error"
                            case 0xC5:
                                parameter_status_description = "Error: Command 21h “Get next UPID List item” was executed without prior execution of “Start Getting UPID List”"
                            case 0xC6:
                                parameter_status_description = "End of UPID list reached (no next UPID list item found)"
                            case 0xD0:
                                parameter_status_description = "Odd address"
                            case 0xD1:
                                parameter_status_description = "Size error (curve selection)"
                            case 0xD4:
                                parameter_status_description = "Curve already defined / curve not present (curve selection)"
                            case _:
                                parameter_status_description = "__UNKNOWN__"

                        response_type_translated_value = Realtime_Config_Response(
                            status_number=parameter_channel_status,
                            status_description=parameter_status_description,
                            details=realtime_config_command.DI_parameters,
                            values=[DI_values[i] / realtime_config_command.DI_parameters[i].conversion_factor for i in range(len(DI_values))],
                            command_count=command_count
                        )
                    case _:
                        raise ValueError(f"")

                setattr(translated_response, response_name, response_type_translated_value)
                i += 1

        return translated_response

    def get_format(self, realtime_config_command: Realtime_Config | None) -> str:
        format = "".join([
            "H"   if self.response_types_included['status_word'        ] else "",
            "2s"  if self.response_types_included['state_var'          ] else "",
            "i"   if self.response_types_included['actual_pos'         ] else "",
            "i"   if self.response_types_included['demand_pos'         ] else "",
            "h"   if self.response_types_included['current'            ] else "",   # Is current signed?
            "H"   if self.response_types_included['warn_word'          ] else "",
            "H"   if self.response_types_included['error_code'         ] else "",
            "16s" if self.response_types_included['monitoring_channel' ] else ""    # Format of monitoring channel depends on what the type of the selected UPID is.
        ])
        
        # Realtime config format depends on the parameter command ID and is added to the response if the request 
        # contains a realtime config, regardless of self.response_types_included['realtime_config']. Therefore it
        # is needed as an argument for this method.
        if realtime_config_command is not None:
            format += f"{realtime_config_command.get_response_byte_size()}s"

        # If the size of the response is less than 14 bytes (including request and response defs) 
        # padding is appended up till 14 bytes. Documentation says pappending is appended up till 64 bytes 
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
    
    def __repr__(self) -> str:
        return ", ".join([response_type for response_type, included in self.response_types_included.items() if included])