import struct

class Control_Word:
    
    def __init__(self, 
                 switch_on: bool = False,
                 go_to_position: bool = False,
                 Error_acknowledge: bool = False,
                 jog_move_plus: bool = False,
                 jog_move_minus: bool = False,
                 special_mode: bool = False,
                 home: bool = False,
                 clerance_check: bool = False,
                 go_to_initial_position: bool = False,
                 linearizing: bool = False,
                 phase_search: bool = False) -> None:
        
        self.include_switch_on = switch_on
        self.include_go_to_position = go_to_position
        self.include_Error_acknowledge = Error_acknowledge
        self.include_jog_move_plus = jog_move_plus
        self.include_jog_move_minus = jog_move_minus
        self.include_special_mode = special_mode
        self.include_home = home
        self.include_clerance_check = clerance_check
        self.include_go_to_initial_position = go_to_initial_position
        self.include_linearizing = linearizing
        self.include_phase_search = phase_search

    @property
    def binary(self) -> bytes:
        return struct.pack("H",
            (self.include_switch_on              <<  0  ) |
            (self.include_go_to_position         <<  6  ) |
            (self.include_Error_acknowledge      <<  7  ) |
            (self.include_jog_move_plus          <<  8  ) |
            (self.include_jog_move_minus         <<  9  ) |
            (self.include_special_mode           <<  10 ) |
            (self.include_home                   <<  11 ) |
            (self.include_clerance_check         <<  12 ) |
            (self.include_go_to_initial_position <<  13 ) |
            (self.include_linearizing            <<  14 ) |
            (self.include_phase_search           <<  15 )
        )