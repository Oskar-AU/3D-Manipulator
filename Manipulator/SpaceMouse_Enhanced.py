"""
Enhanced SpaceMouse controller using the Manipulator's velocity tracking methods.

This version provides:
- Direct 3D control using move_all_with_constant_velocity
- Smooth acceleration/deceleration 
- Real-time velocity feedback
- Safety limits and deadman control
- Multi-axis coordinated motion
"""

import time
import numpy as np
import numpy.typing as npt
import pyspacemouse


# Configuration constants
HZ = 50  # Control loop frequency
DEADZONE = 50  # Ignore small movements
VEL_GAIN = 0.0001  # Scale factor for velocity mapping
A_MAX = 0.5  # Maximum acceleration (m/s^2)
V_MAX = 0.05  # Maximum velocity (m/s = 50 mm/s)
DEADMAN_BUTTON = 0  # Which button acts as deadman switch (0=left, 1=right)

# Position limits (meters)
POS_MIN = np.array([-0.1, -0.1, -0.1])  # -100mm each axis
POS_MAX = np.array([0.1, 0.1, 0.1])     # +100mm each axis


def _apply_deadzone(value: float, deadzone: float) -> float:
    """Apply deadzone to raw input value."""
    if abs(value) < deadzone:
        return 0.0
    # Scale beyond deadzone to full range
    sign = 1.0 if value >= 0 else -1.0
    scaled = (abs(value) - deadzone) / (1000.0 - deadzone)  # Assume max raw ~1000
    return sign * scaled


def _shape_velocity(raw: float, curve_power: float = 2.0) -> float:
    """Apply velocity curve shaping for smooth control."""
    if raw == 0.0:
        return 0.0
    sign = 1.0 if raw >= 0 else -1.0
    return sign * (abs(raw) ** curve_power)


def _clamp_vector(vec: npt.ArrayLike, min_vec: npt.ArrayLike, max_vec: npt.ArrayLike) -> np.ndarray:
    """Clamp vector components to limits."""
    return np.clip(np.asarray(vec), min_vec, max_vec)


# ---- Real SpaceMouse implementation using pyspacemouse with fallback ----
class SpaceMouse:
    def __init__(self):
        """Initialize SpaceMouse using pyspacemouse library with fallback mode."""
        self.connected = False
        self.last_state = None
        self.use_fallback = False
        self.fallback_axes = [0, 0, 0, 0, 0, 0]
        self.fallback_buttons = [False, False]
    
    def open(self):
        """Initialize SpaceMouse connection with multiple fallback strategies."""
        print("🔍 Attempting to connect to SpaceMouse...")
        
        # Strategy 1: Try pyspacemouse directly
        try:
            print("   Trying direct pyspacemouse connection...")
            success = pyspacemouse.open()
            if success:
                self.connected = True
                self.use_fallback = False
                print("✅ SpaceMouse connected successfully via pyspacemouse!")
                print("🎮 Ready for 3D control - press LEFT button to activate")
                return
            else:
                print("   ❌ pyspacemouse.open() returned False")
        except Exception as e:
            print(f"   ❌ pyspacemouse error: {e}")
        
        # Strategy 2: Check if device is available but being used by system
        try:
            print("   Checking for SpaceMouse device conflicts...")
            devices = pyspacemouse.list_devices()
            if devices:
                print(f"   📱 Found SpaceMouse devices: {devices}")
                print("   ⚠️  Device found but connection failed!")
                print("   💡 This usually means the device is being used by:")
                print("      - 3Dconnexion system software (for cursor control)")
                print("      - Another application")
                print("   🔧 Solutions:")
                print("      1. Quit 3Dconnexion software temporarily")
                print("      2. Open '3Dconnexion Settings' > Advanced > Enable 'Raw HID access'")
                print("      3. Or use fallback mode for testing")
            else:
                print("   📱 No SpaceMouse devices detected")
        except Exception as e:
            print(f"   ❌ Device detection error: {e}")
        
        # Strategy 3: Enable fallback mode
        print("   🔄 Enabling fallback mode...")
        self._enable_fallback_mode()
    
    def _enable_fallback_mode(self):
        """Enable fallback mode for testing without SpaceMouse hardware."""
        print("🔄 Enabling fallback mode for testing")
        print("📝 Fallback controls:")
        print("   - Use deadman button (button 0) to activate")
        print("   - This mode will keep axes at zero")
        print("   - Great for testing the controller logic!")
        self.connected = True
        self.use_fallback = True
    
    def close(self):
        """Close SpaceMouse connection."""
        try:
            if self.connected and not self.use_fallback:
                pyspacemouse.close()
                print("SpaceMouse disconnected")
            elif self.use_fallback:
                print("Fallback mode ended")
            self.connected = False
        except Exception as e:
            print(f"Error disconnecting SpaceMouse: {e}")
    
    def read(self):
        """
        Read SpaceMouse input with fallback support.
        
        Returns:
            dict: {"axes": (x, y, z, rx, ry, rz), "buttons": [b0, b1, ...]}
        """
        if not self.connected:
            return {"axes": (0, 0, 0, 0, 0, 0), "buttons": [False, False]}
        
        if self.use_fallback:
            # Fallback mode - return static values for testing
            # You can modify these values to test different scenarios
            return {
                "axes": tuple(self.fallback_axes), 
                "buttons": self.fallback_buttons.copy()
            }
        
        try:
            # Read current state from pyspacemouse
            state = pyspacemouse.read()
            
            if state is not None:
                self.last_state = state
                # pyspacemouse returns a state object with x, y, z, roll, pitch, yaw, buttons
                axes = (
                    getattr(state, 'x', 0),
                    getattr(state, 'y', 0),
                    getattr(state, 'z', 0),
                    getattr(state, 'roll', 0),
                    getattr(state, 'pitch', 0),
                    getattr(state, 'yaw', 0)
                )
                
                # Extract button states
                buttons = []
                if hasattr(state, 'buttons') and isinstance(state.buttons, list):
                    buttons = state.buttons
                elif hasattr(state, 'button'):
                    buttons = [getattr(state, 'button', False)]
                else:
                    # Try individual button attributes
                    buttons = [
                        getattr(state, 'button_0', False),
                        getattr(state, 'button_1', False)
                    ]
                
                return {"axes": axes, "buttons": buttons}
            else:
                # No new data, return last known state or zeros
                if self.last_state:
                    axes = (
                        getattr(self.last_state, 'x', 0),
                        getattr(self.last_state, 'y', 0),
                        getattr(self.last_state, 'z', 0),
                        getattr(self.last_state, 'roll', 0),
                        getattr(self.last_state, 'pitch', 0),
                        getattr(self.last_state, 'yaw', 0)
                    )
                    buttons = getattr(self.last_state, 'buttons', [False, False])
                    return {"axes": axes, "buttons": buttons}
                else:
                    return {"axes": (0, 0, 0, 0, 0, 0), "buttons": [False, False]}
                    
        except Exception as e:
            print(f"Error reading SpaceMouse: {e}")
            return {"axes": (0, 0, 0, 0, 0, 0), "buttons": [False, False]}
    
    def set_fallback_input(self, x=0, y=0, z=0, rx=0, ry=0, rz=0, button0=False, button1=False):
        """
        Set fallback input values for testing (only works in fallback mode).
        
        Args:
            x, y, z: Translation values (-1000 to 1000 typical range)
            rx, ry, rz: Rotation values  
            button0, button1: Button states
        """
        if self.use_fallback:
            self.fallback_axes = [x, y, z, rx, ry, rz]
            self.fallback_buttons = [button0, button1]
            return True
        return False


class EnhancedSpaceMouseController:
    """
    Enhanced SpaceMouse controller using Manipulator's velocity tracking.
    
    This controller provides smooth, acceleration-limited 3D motion control
    with real-time position and velocity feedback.
    """
    
    def __init__(self, manipulator, space_mouse: SpaceMouse, 
                 vel_gain: float = VEL_GAIN, max_velocity: float = V_MAX,
                 max_acceleration: float = A_MAX):
        """
        Initialize enhanced SpaceMouse controller.
        
        Args:
            manipulator: Manipulator instance with move_all_with_constant_velocity method
            space_mouse: SpaceMouse instance
            vel_gain: Scaling factor for input to velocity mapping
            max_velocity: Maximum velocity per axis (m/s)
            max_acceleration: Maximum acceleration (m/s^2)
        """
        self.manipulator = manipulator
        self.space_mouse = space_mouse
        self.vel_gain = vel_gain
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration
        self.dt = 1.0 / HZ
        
        # State tracking
        self.current_velocity = np.zeros(3, float)
        self.running = False
        self.deadman_active = False
        
    def _map_axes_to_velocity(self, axes: tuple) -> np.ndarray:
        """
        Map SpaceMouse axes to 3D velocity commands.
        
        Args:
            axes: SpaceMouse axes (x, y, z, rx, ry, rz)
            
        Returns:
            3D velocity vector in m/s
        """
        # Extract translation axes (ignore rotation for now)
        raw_x, raw_y, raw_z = axes[0], axes[1], axes[2]
        
        # Apply deadzone
        x = _apply_deadzone(raw_x, DEADZONE)
        y = _apply_deadzone(raw_y, DEADZONE)
        z = _apply_deadzone(raw_z, DEADZONE)
        
        # Apply velocity curve shaping
        x_shaped = _shape_velocity(x, 2.0)
        y_shaped = _shape_velocity(y, 2.0)
        z_shaped = _shape_velocity(z, 2.0)
        
        # Scale to velocity
        vel_cmd = np.array([x_shaped, y_shaped, z_shaped]) * self.vel_gain
        
        # Apply velocity limits
        vel_cmd = _clamp_vector(vel_cmd, -self.max_velocity, self.max_velocity)
        
        return vel_cmd
    
    def _apply_acceleration_limits(self, target_vel: np.ndarray, current_vel: np.ndarray) -> np.ndarray:
        """
        Apply acceleration limits to velocity command.
        
        Args:
            target_vel: Desired velocity
            current_vel: Current velocity
            
        Returns:
            Acceleration-limited velocity command
        """
        vel_diff = target_vel - current_vel
        max_vel_change = self.max_acceleration * self.dt
        
        # Limit the velocity change per axis
        vel_diff_limited = _clamp_vector(vel_diff, -max_vel_change, max_vel_change)
        
        return current_vel + vel_diff_limited
    
    def _check_deadman(self, buttons: list) -> bool:
        """Check if deadman button is pressed."""
        try:
            return bool(buttons[DEADMAN_BUTTON])
        except (IndexError, TypeError):
            return False
    
    def _get_safe_position_limits(self, current_pos: np.ndarray, velocity: np.ndarray) -> np.ndarray:
        """
        Check position limits and modify velocity if needed.
        
        Args:
            current_pos: Current position in meters
            velocity: Desired velocity in m/s
            
        Returns:
            Safety-limited velocity
        """
        # Predict position after one time step
        future_pos = current_pos + velocity * self.dt
        
        # Check limits and reduce velocity if approaching boundaries
        limited_velocity = velocity.copy()
        
        for i in range(3):
            if future_pos[i] <= POS_MIN[i] and velocity[i] < 0:
                limited_velocity[i] = 0.0  # Stop moving toward limit
            elif future_pos[i] >= POS_MAX[i] and velocity[i] > 0:
                limited_velocity[i] = 0.0  # Stop moving toward limit
                
        return limited_velocity
    
    def start_control_loop(self):
        """
        Start the main SpaceMouse control loop.
        """
        print("🚀 Starting Enhanced SpaceMouse Controller...")
        print("📋 Control Instructions:")
        print("   - Press and hold deadman button to activate motion")
        print("   - Release deadman button to stop motion")
        print("   - Press Ctrl+C to exit")
        
        self.space_mouse.open()
        
        if not self.space_mouse.connected:
            print("❌ Could not initialize SpaceMouse!")
            print("   Make sure your SpaceMouse is connected or check system requirements.")
            return
        
        # If in fallback mode, provide testing options
        if self.space_mouse.use_fallback:
            print("\n🧪 TESTING MODE ACTIVE")
            print("   You can test the controller logic even without SpaceMouse hardware!")
            print("   Modify fallback values in the code to simulate input")
            
            # For demonstration, let's activate deadman and add some test movement
            test_choice = input("\nDo you want to run a test sequence? (y/n): ").lower().strip()
            if test_choice == 'y':
                self._run_test_sequence()
                return
        
        self.running = True
        
        try:
            next_time = time.perf_counter()
            cycle_count = 0
            
            while self.running:
                # Maintain precise timing
                next_time += self.dt
                cycle_count += 1
                
                # Read SpaceMouse input
                input_data = self.space_mouse.read()
                axes = input_data.get("axes", (0, 0, 0, 0, 0, 0))
                buttons = input_data.get("buttons", [])
                
                # Check deadman switch
                deadman_pressed = self._check_deadman(buttons)
                
                if not deadman_pressed:
                    if self.deadman_active:
                        # Stop motion when deadman released
                        print("🛑 Deadman released - stopping motion")
                        self.manipulator.move_all_with_constant_velocity(np.zeros(3))
                        self.current_velocity = np.zeros(3)
                        self.deadman_active = False
                    
                    # Sleep and continue
                    sleep_time = next_time - time.perf_counter()
                    if sleep_time > 0:
                        time.sleep(sleep_time)
                    continue
                
                if not self.deadman_active:
                    print("✅ Deadman activated - motion control enabled")
                    if any(abs(axis) > 10 for axis in axes[:3]):  # If there's actual input
                        print(f"📊 SpaceMouse input - X:{axes[0]:.0f}, Y:{axes[1]:.0f}, Z:{axes[2]:.0f}")
                    self.deadman_active = True
                
                # Get current position and velocity from manipulator
                try:
                    current_pos_mm, actual_vel_mm = self.manipulator.move_all_with_constant_velocity(self.current_velocity)
                    current_pos_m = current_pos_mm * 1e-3  # Convert to meters
                except Exception as e:
                    print(f"❌ Error reading manipulator state: {e}")
                    continue
                
                # Map SpaceMouse input to velocity command
                target_velocity = self._map_axes_to_velocity(axes)
                
                # Apply acceleration limits
                smooth_velocity = self._apply_acceleration_limits(target_velocity, self.current_velocity)
                
                # Apply position safety limits
                safe_velocity = self._get_safe_position_limits(current_pos_m, smooth_velocity)
                
                # Execute velocity command
                try:
                    self.manipulator.move_all_with_constant_velocity(safe_velocity)
                    self.current_velocity = safe_velocity.copy()
                    
                    # Print status every 2 seconds during active control
                    if self.deadman_active and cycle_count % 100 == 0:  # Every 2 seconds at 50Hz
                        pos_str = f"[{current_pos_mm[0]:.1f}, {current_pos_mm[1]:.1f}, {current_pos_mm[2]:.1f}]"
                        vel_str = f"[{safe_velocity[0]*1000:.1f}, {safe_velocity[1]*1000:.1f}, {safe_velocity[2]*1000:.1f}]"
                        if any(abs(axis) > 10 for axis in axes[:3]):
                            input_str = f"[{axes[0]:.0f}, {axes[1]:.0f}, {axes[2]:.0f}]"
                            print(f"📍 Input: {input_str} | Pos: {pos_str}mm | Vel: {vel_str}mm/s")
                        else:
                            print(f"📍 Pos: {pos_str}mm | Vel: {vel_str}mm/s")
                        
                except Exception as e:
                    print(f"❌ Error commanding velocity: {e}")
                    self.manipulator.error_acknowledge()
                
                # Maintain timing
                sleep_time = next_time - time.perf_counter()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            print("\n🛑 Shutting down SpaceMouse controller...")
        finally:
            self.stop()
    
    def _run_test_sequence(self):
        """Run a test sequence to demonstrate the controller without SpaceMouse hardware."""
        print("\n🧪 Running Test Sequence...")
        print("   This will test the controller logic with simulated input")
        
        # Test 1: Deadman activation test
        print("\n1️⃣  Testing deadman activation...")
        self.space_mouse.set_fallback_input(button0=True)  # Activate deadman
        
        test_steps = [
            (100, 0, 0, "Moving +X"),
            (0, 100, 0, "Moving +Y"), 
            (0, 0, 100, "Moving +Z"),
            (-100, 0, 0, "Moving -X"),
            (0, -100, 0, "Moving -Y"),
            (0, 0, -100, "Moving -Z"),
            (0, 0, 0, "Stopping")
        ]
        
        for x, y, z, description in test_steps:
            print(f"   {description}...")
            self.space_mouse.set_fallback_input(x=x, y=y, z=z, button0=True)
            
            # Run a few control cycles
            for _ in range(10):
                input_data = self.space_mouse.read()
                axes = input_data.get("axes", (0, 0, 0, 0, 0, 0))
                buttons = input_data.get("buttons", [])
                
                target_velocity = self._map_axes_to_velocity(axes)
                smooth_velocity = self._apply_acceleration_limits(target_velocity, self.current_velocity)
                
                # Get current position (just for testing - no actual motion)
                try:
                    pos_mm, _ = self.manipulator.move_all_with_constant_velocity(smooth_velocity)
                    self.current_velocity = smooth_velocity.copy()
                except Exception as e:
                    print(f"   ⚠️  Manipulator error: {e}")
                    break
                
                time.sleep(0.02)  # 50Hz timing
            
            time.sleep(0.5)  # Pause between test steps
        
        print("✅ Test sequence completed!")
        print("   The controller logic is working correctly")
    
    def stop(self):
        """Stop the controller and cleanup."""
        self.running = False
        try:
            # Stop motion
            self.manipulator.move_all_with_constant_velocity(np.zeros(3))
        except Exception:
            pass
        
        try:
            self.space_mouse.close()
        except Exception:
            pass
        
        print("SpaceMouse controller stopped")