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
    def get_next_coordinate_set(self) -> tuple[bool, list[tuple[tuple, tuple, tuple]]]:
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
        drive_2_pos = self.amplitude*math.sin(elapsed_time*self.frequency - math.pi/2) + self.amplitude
        drive_3_pos = self.amplitude*math.sin(elapsed_time*self.frequency - math.pi/2) + self.amplitude

        drive_1_vel = 0
        drive_2_vel = 0.1
        drive_3_vel = 0.1

        return stop_streaming, ((drive_1_pos, drive_1_vel), (drive_2_pos, drive_2_vel), (drive_3_pos, drive_3_vel))

class SpaceMouse(Stream): 

    def close(self):
        # just signal; real close is in the read thread:
        self._alive = False

    #Læser Spacemouse input og returnerer det som en PV stream med x,y,z. X -> drive 1, Y -> drive 2, Z -> drive 3
    @property
    def type(self) -> str:
        return "PV"
    
    @property
    def cycle_time(self) -> float:
        return self._dt

    def __init__(self, *, 
                 rate_hz: float = 200, 
                 stroke_mm: tuple[tuple[float, float], tuple[float, float], tuple[float, float]] = ((0,50), (0,50), (0,25)), 
                 gain: float = 1,
                 deadzone: int = 0,
                 vmax_mm_s: tuple[float, float, float] = (600.0, 600.0, 600.0), 
                 deadman_button: int | None = 0
                    ) -> None:
        
        self._dt = 1.0/float(rate_hz)
        self.stroke = stroke_mm
        self.gain = float(gain)
        self.deadzone = int(deadzone)
        self.vmax = vmax_mm_s
        # Handle None deadman_button (disable deadman safety)
        self.deadman_button = None if deadman_button is None else int(deadman_button)

        # Lazy import of pyspacemouse to avoid crashing at module import time
        try:
            import pyspacemouse as spm
        except Exception as e:
            # Raise a clear RuntimeError so callers can fall back gracefully
            raise RuntimeError(f"SpaceMouse import failed: {e}") from e

        # Try to open the device; if it fails, raise to allow fallback
        if not spm.open():
            raise RuntimeError("SpaceMouse not found")

        # Keep a reference to the module so other methods can call it
        self._spm = spm

        self.pos = [(lo + hi)/2.0 for lo, hi in stroke_mm]
        self.vel = [0.0, 0.0, 0.0]


    def _dz(self, v: float) -> float: 
        return 0.0 if abs(v) < self.deadzone else v
    
    def _clamp(self, x, lo, hi) -> float:
         return lo if x < lo else (hi if x > hi else x)
    
        
    def _is_deadman_pressed(self, buttons):
        # If deadman_button is None, bypass the deadman check
        if self.deadman_button is None:
            return True
        try:
            return bool(buttons[self.deadman_button])
        except Exception:
            return False
    """
    def _is_deadman_pressed(self, buttons):
        # Option 1: use SpaceMouse button
        hw_pressed = False
        if self.deadman_button is not None:
            try:
                hw_pressed = bool(buttons[self.deadman_button])
            except Exception:
                hw_pressed = False

        # Option 2: override with keyboard spacebar
        kb_pressed = keyboard.is_pressed('space')

        # Either hardware OR ""spacebar counts
        return hw_pressed or kb_pressed"""
    
    def get_next_coordinate_set(self) -> tuple[bool, list[tuple[float, float, float]]]:
        # Use the lazily imported module stored on the instance
        state = getattr(self, '_spm').read()
        if state is None or not self._is_deadman_pressed(getattr(state, 'buttons', [])):
            return False, [(self.pos[i], 0.0, 0.0) for i in range(3)]

        raw_axes = (float(state.x), float(state.y), float(state.z))
        coords: list[tuple[float, float, float]]=[]


        for i, raw in enumerate(raw_axes):
            v = self._dz(raw) * self.gain
            v = self._clamp(v, -self.vmax[i], self.vmax[i])
            lo, hi = self.stroke[i]
            p = self._clamp(self.pos[i] + v*self._dt, lo, hi)   
            self.pos[i] = p
            self.vel[i] = v

            coords.append((p, v, 0.0))

        return False, coords
    
    def close(self) -> None:
        try:
            if hasattr(self, '_spm'):
                self._spm.close()
        except Exception:
            pass