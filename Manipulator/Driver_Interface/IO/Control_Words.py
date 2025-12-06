import struct

class ControlWord:
    
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
        
        self.control_words_included = {
            "switch_on":              switch_on,
            "go_to_position":         go_to_position,
            "Error_acknowledge":      Error_acknowledge,
            "jog_move_plus":          jog_move_plus,
            "jog_move_minus":         jog_move_minus,
            "special_mode":           special_mode,
            "home":                   home,
            "clerance_check":         clerance_check,
            "go_to_initial_position": go_to_initial_position,
            "linearizing":            linearizing,
            "phase_search":           phase_search
        }

    @property
    def format(self) -> str:
        return "H"
    
    @property
    def decimal(self) -> int:
        return (self.control_words_included['switch_on'             ]  <<  0  ) | \
               (self.control_words_included['go_to_position'        ]  <<  6  ) | \
               (self.control_words_included['Error_acknowledge'     ]  <<  7  ) | \
               (self.control_words_included['jog_move_plus'         ]  <<  8  ) | \
               (self.control_words_included['jog_move_minus'        ]  <<  9  ) | \
               (self.control_words_included['special_mode'          ]  <<  10 ) | \
               (self.control_words_included['home'                  ]  <<  11 ) | \
               (self.control_words_included['clerance_check'        ]  <<  12 ) | \
               (self.control_words_included['go_to_initial_position']  <<  13 ) | \
               (self.control_words_included['linearizing'           ]  <<  14 ) | \
               (self.control_words_included['phase_search'          ]  <<  15 )

    def get_binary(self) -> bytes:
        return struct.pack(self.format, self.decimal)
    
    @property
    def hex(self) -> str:
        return hex(self.decimal)
    
    def __repr__(self) -> str:
        return self.hex