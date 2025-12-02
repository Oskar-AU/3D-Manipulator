from abc import abstractmethod
import numpy as np
import numpy.typing as npt
import logging
from typing import Optional

logger = logging.getLogger("PATH")

class Path_Base:

    @abstractmethod
    def __call__(self, current_position: npt.ArrayLike, current_velocity: npt.ArrayLike | None = None) -> tuple[npt.NDArray, npt.NDArray, bool]:
        pass
    
def make_waypoint_follower(
    waypoints_mm: npt.ArrayLike,
    max_velocity: float = 0.02,     # m/s
    a_max: float = 0.08,            # m/s^2 - FURTHER REDUCED from 0.15 for ultra-smooth motion
    eps: float = 1.0,               # mm (was 1e-3 m, now 1.0 mm)
    dt: float = 0.02,               # s
    start_index: int = 0,
):
    try:
        waypoints_array = np.asarray(waypoints_mm, dtype=float)
        if len(waypoints_array) == 0:
            raise ValueError("Waypoints array is empty")
        if waypoints_array.ndim != 2 or waypoints_array.shape[1] != 3:
            raise ValueError(f"Waypoints must have 3 columns (X, Y, Z), got shape {waypoints_array.shape}")
        
        # Keep waypoints in mm - no conversion needed
        waypoints_mm_array = waypoints_array
        
    except Exception as e:
        raise ValueError(f"Failed to process waypoints: {e}")

    # State: current target waypoint index
    current_waypoint_idx = max(0, int(start_index))
    
    # Add velocity command history for smoothing
    prev_velocity_cmd = np.zeros(3, float)
    velocity_filter_alpha = 0.1  # MUCH MORE AGGRESSIVE smoothing (was 0.3)
    
    # Add multi-stage smoothing buffer
    velocity_history = [np.zeros(3, float) for _ in range(5)]  # 5-point moving average
    history_index = 0

    def step(current_pos_mm: np.ndarray, current_vel_ms: Optional[np.ndarray] = None):
        nonlocal current_waypoint_idx
        
        p = np.asarray(current_pos_mm, float).reshape(3)  # positions in mm
        
        # Handle optional velocity parameter (still in m/s)
        if current_vel_ms is None:
            v = np.zeros(3, float)
        else:
            v = np.asarray(current_vel_ms, float).reshape(3)
        
        # Check if we've completed all waypoints
        if current_waypoint_idx >= len(waypoints_mm_array):
            return np.zeros(3, float), True
        
        # Get current target waypoint (in mm)
        target_mm = waypoints_mm_array[current_waypoint_idx]
        
        # Calculate direction and distance to current target
        direction_vec = target_mm - p
        distance_mm = float(np.linalg.norm(direction_vec))
        
        # Check if current waypoint reached (eps is now in mm)
        if distance_mm <= eps:
            if len(waypoints_mm_array) > 1:  # Only log for multi-waypoint paths
                logger.debug(f"Reached waypoint {current_waypoint_idx + 1}/{len(waypoints_mm_array)}")
            current_waypoint_idx += 1
            
            # Check if this was the last waypoint
            if current_waypoint_idx >= len(waypoints_mm_array):
                return np.zeros(3, float), True
            
            # Move to next waypoint
            target_mm = waypoints_mm_array[current_waypoint_idx]
            direction_vec = target_mm - p
            distance_mm = float(np.linalg.norm(direction_vec))
        
        # Normalize direction
        if distance_mm > 1e-6:  # 1 micron threshold
            direction = direction_vec / distance_mm
        else:
            return np.zeros(3, float), len(waypoints_mm_array) == 1  # True if single waypoint, False if multi
        
        # Convert distance to meters for velocity calculations
        distance_m = distance_mm * 1e-3
        
        # Calculate desired speed based on distance (braking distance)
        # Slow down when approaching target: v_max = sqrt(2 * a_max * distance)
        v_braking = float(np.sqrt(max(0.0, 2.0 * a_max * distance_m)))
        v_desired = min(max_velocity, v_braking)
        
        # Current speed along direction to target
        v_current = float(v @ direction)
        
        # Apply acceleration limits with smoothing
        smooth_a_max = a_max * 0.6  # Use 60% of max acceleration for smoother motion
        dv_max = smooth_a_max * dt
        
        # Apply deadband to prevent small oscillations
        v_error = v_desired - v_current
        if abs(v_error) < 0.002:  # 2 mm/s deadband
            v_new = v_current
        else:
            v_new = np.clip(v_desired, v_current - dv_max, v_current + dv_max)
        
        # Ensure we don't overshoot by going too fast
        if distance_mm < eps * 2:  # Very close to target (eps in mm)
            v_new = min(v_new, distance_m / dt)  # Limit speed to reach target in one cycle
        
        # Apply minimum velocity threshold to prevent micro-velocity jitter
        v_new = max(0.010, v_new) if v_new > 0 else 0.010  # Minimum 10 mm/s when moving
        
        velocity_cmd = direction * v_new
        
        # FINAL SAFETY CHECK: Prevent any micro-velocity commands that cause jitter
        # If the velocity magnitude is too small, either stop completely or use minimum velocity
        velocity_magnitude = np.linalg.norm(velocity_cmd)
        if velocity_magnitude < 0.009:  # Below 9 mm/s threshold
            if distance_mm <= eps:  # Close enough to target - stop completely
                return np.zeros(3, float), True
            else:  # Not close enough - use minimum velocity
                velocity_cmd = direction * 0.010  # Force minimum 10 mm/s
        
        # Apply MULTI-STAGE smoothing to reduce jitter
        nonlocal prev_velocity_cmd, velocity_history, history_index
        
        # Stage 1: Exponential smoothing (very aggressive)
        velocity_cmd_exp = velocity_filter_alpha * velocity_cmd + (1 - velocity_filter_alpha) * prev_velocity_cmd
        prev_velocity_cmd = velocity_cmd_exp.copy()
        
        # Stage 2: Moving average smoothing
        velocity_history[history_index] = velocity_cmd_exp.copy()
        history_index = (history_index + 1) % len(velocity_history)
        velocity_cmd_smooth = np.mean(velocity_history, axis=0)
        
        # Stage 3: Additional smoothing - round to reduce micro-variations
        velocity_cmd_smooth = np.round(velocity_cmd_smooth, decimals=3)  # Round to 1 mm/s precision
        
        # Ensure smoothed command still meets minimum velocity requirement
        smoothed_magnitude = np.linalg.norm(velocity_cmd_smooth)
        if smoothed_magnitude > 0 and smoothed_magnitude < 0.008:
            velocity_cmd_smooth = velocity_cmd_smooth / smoothed_magnitude * 0.008  # Scale to minimum
        
        return velocity_cmd_smooth, False

    return step


def make_waypoint_follower_2(
    waypoints_mm: npt.ArrayLike,
    velocity: float = 0.002,    # m/s - Slow speed to avoid jitter problems  
    acceleration: float = 0.03,  # m/s^2 - VERY LOW acceleration for ultra-smooth motion
    decel_time: float = 1.0,     # s - Extended decel time for smooth stops
    eps: float = 2.0,            # mm
    dt: float = 0.02,            # s
    start_index: int = 0,
):
    try:
        waypoints_array = np.asarray(waypoints_mm, dtype=float)
        if len(waypoints_array) == 0:
            raise ValueError("Waypoints array is empty")
        if waypoints_array.ndim != 2 or waypoints_array.shape[1] != 3:
            raise ValueError(f"Waypoints must have 3 columns (X, Y, Z), got shape {waypoints_array.shape}")
        
        # Keep waypoints in mm - no conversion needed
        waypoints_mm_array = waypoints_array
        
    except Exception as e:
        raise ValueError(f"Failed to process waypoints: {e}")

    # State: current target waypoint index
    current_waypoint_idx = max(0, int(start_index))
    
    # Add velocity command history for smoothing
    prev_velocity_cmd = np.zeros(3, float)
    velocity_filter_alpha = 0.1  # MUCH MORE AGGRESSIVE smoothing (was 0.3)
    
    # Add multi-stage smoothing buffer
    velocity_history = [np.zeros(3, float) for _ in range(5)]  # 5-point moving average
    history_index = 0

    # Calculate a characteristic deceleration distance (based on time constant)
    # This defines the start of the smooth slow-down zone.
    # We want v_desired to ramp down over this distance.
    decel_dist_m = velocity * decel_time  # in meters

    def step(current_pos_mm: np.ndarray, current_vel_ms: Optional[np.ndarray] = None):
        nonlocal current_waypoint_idx
        
        p = np.asarray(current_pos_mm, float).reshape(3)  # positions in mm
        
        # Handle optional velocity parameter (still in m/s)
        if current_vel_ms is None:
            v = np.zeros(3, float)
        else:
            v = np.asarray(current_vel_ms, float).reshape(3)
        
        # Check if we've completed all waypoints
        if current_waypoint_idx >= len(waypoints_mm_array):
            return np.zeros(3, float), True
        
        # Get current target waypoint (in mm)
        target_mm = waypoints_mm_array[current_waypoint_idx]
        
        # Calculate direction and distance to current target
        direction_vec = target_mm - p
        distance_mm = float(np.linalg.norm(direction_vec))
        
        # Check if current waypoint reached (using eps in mm for stability)
        # Use a slightly larger threshold to ensure reliable waypoint transitions
        waypoint_threshold = max(eps, 3.0)  # At least 3mm threshold
        if distance_mm <= waypoint_threshold:
            if len(waypoints_mm_array) > 1:
                logger.debug(f"Reached waypoint {current_waypoint_idx + 1}/{len(waypoints_mm_array)}")
            current_waypoint_idx += 1
            
            # Check if this was the last waypoint
            if current_waypoint_idx >= len(waypoints_mm_array):
                return np.zeros(3, float), True
            
            # Move to next waypoint
            target_mm = waypoints_mm_array[current_waypoint_idx]
            direction_vec = target_mm - p
            distance_mm = float(np.linalg.norm(direction_vec))
        
        # Normalize direction
        if distance_mm > 1e-6:  # 1 micron threshold
            direction = direction_vec / distance_mm
        else:
            # If we are exactly on the waypoint (or within 1 micron), stop
            return np.zeros(3, float), len(waypoints_mm_array) == 1
        
        # Convert distance to meters for velocity calculations
        distance_m = distance_mm * 1e-3
        eps_m = eps * 1e-3  # Convert eps to meters for calculations
        
        # 1. Calculate DESIRED Speed (Improved Deceleration)
        
        # Use a more robust deceleration algorithm with higher minimum velocities
        # When very close to target, use simple proportional control
        if distance_m < eps_m * 2:  # Within 2x epsilon - use proportional control (10mm for eps=5mm)
            # Simple proportional control when very close
            k_prop = 5.0  # Increased proportional gain
            v_desired = min(velocity, k_prop * distance_m)
            # Set much higher minimum velocity to prevent micro-velocity jitter
            if v_desired > 0:
                v_desired = max(v_desired, 0.015)  # Minimum 15 mm/s when moving (increased)
        else:
            # Far from target - use smooth ramp-down
            distance_in_decel_zone = max(0.0, distance_m - eps_m)
            
            # Prevent division by zero and ensure reasonable deceleration distance
            safe_decel_dist = max(decel_dist_m, 0.010)  # At least 10mm deceleration distance
            
            # Linear ramp-down from max_velocity to minimum velocity
            min_velocity = 0.020  # 20 mm/s minimum when in deceleration zone (even higher to avoid stalling)
            v_decel_ramp = velocity * (distance_in_decel_zone / safe_decel_dist)
            
            # Ensure we don't go below minimum or above maximum
            v_desired = max(min_velocity, min(velocity, v_decel_ramp))
        
        # 2. Apply Acceleration Limits (Ramp-up/Ramp-down) with reduced aggressiveness
        
        # Current speed along direction to target
        v_current = float(v @ direction)
        
        # Calculate maximum change in velocity based on acceleration limit and time step
        # Reduce acceleration limit to make motion smoother and reduce jitter
        smooth_a_max = acceleration * 0.6  # Use 60% of max acceleration for smoother motion
        dv_max = smooth_a_max * dt
        
        # Apply acceleration limits with deadband to prevent small oscillations
        v_error = v_desired - v_current
        if abs(v_error) < 0.002:  # 2 mm/s deadband - don't change if close enough
            v_new = v_current
        else:
            # Apply gradual acceleration limiting
            v_new = np.clip(v_desired, v_current - dv_max, v_current + dv_max)
        
        # 3. Final Safety Checks with higher minimum velocities
        # Ensure we don't overshoot by going too fast when extremely close
        if distance_m < 0.005:  # Very close (5mm) - use more conservative limit
            v_safe = distance_m / dt  # Reach target in 1 cycle, but not too slow
            v_new = min(v_new, max(v_safe, 0.008))  # At least 8 mm/s minimum
        
        # Prevent negative velocities and ensure substantial minimum velocity
        v_new = max(0.010, v_new)  # Increase minimum to 10 mm/s to avoid micro-velocity jitter

        velocity_cmd = direction * v_new
        
        # ADVANCED JITTER REDUCTION: Apply velocity command smoothing
        # If the velocity magnitude is too small, either stop completely or use minimum velocity
        velocity_magnitude = np.linalg.norm(velocity_cmd)
        if velocity_magnitude < 0.009:  # Below 9 mm/s threshold (increased)
            if distance_mm <= eps:  # Close enough to target - stop completely
                return np.zeros(3, float), True
            else:  # Not close enough - use minimum velocity
                velocity_cmd = direction * 0.010  # Force minimum 10 mm/s (increased)
        
        # Apply MULTI-STAGE smoothing to reduce jitter
        nonlocal prev_velocity_cmd, velocity_history, history_index
        
        # Stage 1: Exponential smoothing (very aggressive)
        velocity_cmd_exp = velocity_filter_alpha * velocity_cmd + (1 - velocity_filter_alpha) * prev_velocity_cmd
        prev_velocity_cmd = velocity_cmd_exp.copy()
        
        # Stage 2: Moving average smoothing
        velocity_history[history_index] = velocity_cmd_exp.copy()
        history_index = (history_index + 1) % len(velocity_history)
        velocity_cmd_smooth = np.mean(velocity_history, axis=0)
        
        # Stage 3: Additional smoothing - round to reduce micro-variations
        velocity_cmd_smooth = np.round(velocity_cmd_smooth, decimals=3)  # Round to 1 mm/s precision
        
        # Ensure smoothed command still meets minimum velocity requirement
        smoothed_magnitude = np.linalg.norm(velocity_cmd_smooth)
        if smoothed_magnitude > 0 and smoothed_magnitude < 0.008:
            velocity_cmd_smooth = velocity_cmd_smooth / smoothed_magnitude * 0.008  # Scale to minimum
        
        return velocity_cmd_smooth, False

    return step



# CLEANED UP FUNCTIONS - Using improved algorithms

def move_to_starting_position(point_cloud: npt.ArrayLike, 
                                max_velocity: float = 0.005, 
                                a_max: float = 0.20, 
                                eps: float = 5.0,  # eps now in mm (was 5e-3 m)
                                decel_time_const: float = 0.5): 
    """
    Move to the first waypoint (full 3D) before path following.
    Uses the improved algorithm with enhanced smoothing.
    """
    try:
        pc = np.asarray(point_cloud, dtype=float)
        if len(pc) == 0:
            raise ValueError("Point cloud is empty")
        if pc.shape[1] != 3:
            raise ValueError(f"Point cloud must have 3 columns (X,Y,Z), got {pc.shape[1]}")
        
        target_mm = pc[0:1]  # first waypoint only
        logger.info(f"Moving to start position (mm): {target_mm[0]}")
    except Exception as e:
        raise ValueError(f"Failed to extract starting position: {e}")

    # Use the improved smooth follower function
    return make_waypoint_follower_2(
        target_mm,
        velocity=max_velocity,        # renamed parameter
        acceleration=a_max,           # renamed parameter
        decel_time=decel_time_const,  # renamed parameter
        eps=eps,
        dt=0.02, # Keeping original dt
        start_index=0,
    )

def path_follower_velocity(waypoints_mm: npt.ArrayLike, 
                          max_velocity: float = 0.02, 
                          a_max: float = 0.30, 
                          eps: float = 5.0,  # eps now in mm (was 5e-3 m)
                          decel_time_const: float = 0.5): 
    """
    Follow multiple waypoints in sequence using the improved algorithm.
    Enhanced smoothing and better deceleration control.
    """
    # Use the improved algorithm with all waypoints
    return make_waypoint_follower_2(
        waypoints_mm, 
        velocity=max_velocity,        # renamed parameter
        acceleration=a_max,           # renamed parameter
        decel_time=decel_time_const,  # renamed parameter
        eps=eps,
    )