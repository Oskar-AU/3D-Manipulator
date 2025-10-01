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
        return 'P'
    
    @property
    def cycle_time(self) -> float:
        return 0.005

    def __init__(self, amplitude: float, frequency: float) -> None:
        self.amplitude = amplitude
        self.frequency = frequency

    def get_next_coordinate_set(self) -> tuple[bool, tuple[tuple, tuple, tuple]]:
        
        if not hasattr(self, 'start_time'):
            self.start_time = time.time()

        elapsed_time = time.time() - self.start_time
        
        stop_streaming = False if elapsed_time < 5 else True

        return stop_streaming, ((0,), (self.amplitude*math.sin(elapsed_time*self.frequency),), (self.amplitude*math.cos(elapsed_time*self.frequency),))