from .IO import Realtime_Config_Parameter

class Realtime_Config_Parameters:
    parameter_UPID = Realtime_Config_Parameter(
        description="The UPID to access", 
    )
    parameter_value_high = Realtime_Config_Parameter(
        description="The high value of the selected UPID",
    )
    parameter_value_low = Realtime_Config_Parameter(
        description="The low value of the selected UPID"
    )
    
    """
    .
    .
    .
    """