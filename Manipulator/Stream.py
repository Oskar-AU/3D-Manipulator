from abc import ABC, abstractmethod
from typing import Literal
import math
import time

class Stream(ABC):
    
    @property
    @abstractmethod
    def type(self) -> Literal['P', 'PV', 'PVA']:
        pass

    @property
    @abstractmethod
    def cycle_time(self) -> float:
        pass

    @abstractmethod
    def get_next_coordinate_set(self) -> tuple[bool, tuple[tuple, tuple, tuple]]:
        pass

class Test_Stream(Stream):
    
    @property
    def type(self) -> str:
        return 'PV'
    
    @property
    def cycle_time(self) -> float:
        return 0.009

    def __init__(self, amplitude: float, frequency: float) -> None:
        self.amplitude = amplitude
        self.frequency = frequency
        self.calls = 0

    def get_next_coordinate_set(self) -> tuple[bool, tuple[tuple, tuple, tuple]]:
        
        if not hasattr(self, 'start_time'):
            self.start_time = time.time()

        elapsed_time = time.time() - self.start_time
        
        stop_streaming = False if elapsed_time < 1 else True

        drive_1_pos = 0
        drive_2_pos = self.amplitude*math.sin(elapsed_time*self.frequency+0.01)
        drive_3_pos = self.amplitude*math.cos(elapsed_time*self.frequency+0.01)

        drive_1_vel = 0
        drive_2_vel = 0.1
        drive_3_vel = 0.1

        return stop_streaming, ((drive_1_pos, drive_1_vel), (drive_2_pos, drive_2_vel), (drive_3_pos, drive_3_vel))