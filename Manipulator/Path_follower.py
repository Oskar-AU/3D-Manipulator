import numpy as np
import numpy.typing as npt
import logging
from typing import Optional

logger = logging.getLogger("PATH")


def make_waypoint_follower(
    waypoints_mm: npt.ArrayLike,
    max_velocity: float = 0.02,     # m/s
    a_max: float = 0.30,            # m/s^2
    eps: float = 1e-3,              # m
    dt: float = 0.02,               # s
    start_index: int = 0,
):
    try:
        waypoints_array = np.asarray(waypoints_mm, dtype=float)
        if len(waypoints_array) == 0:
            raise ValueError("Waypoints array is empty")
        if waypoints_array.ndim != 2 or waypoints_array.shape[1] != 3:
            raise ValueError(f"Waypoints must have 3 columns (X, Y, Z), got shape {waypoints_array.shape}")
        
        # Convert to meters
        waypoints_m = waypoints_array * 1e-3
        
    except Exception as e:
        raise ValueError(f"Failed to process waypoints: {e}")

    # State: current target waypoint index
    current_waypoint_idx = max(0, int(start_index))

    def step(current_pos_m: np.ndarray, current_vel_mps: Optional[np.ndarray] = None):
        nonlocal current_waypoint_idx
        
        p = np.asarray(current_pos_m, float).reshape(3)
        
        # Handle optional velocity parameter
        if current_vel_mps is None:
            v = np.zeros(3, float)
        else:
            v = np.asarray(current_vel_mps, float).reshape(3)
        
        # Check if we've completed all waypoints
        if current_waypoint_idx >= len(waypoints_m):
            return np.zeros(3, float), True
        
        # Get current target waypoint
        target_m = waypoints_m[current_waypoint_idx]
        
        # Calculate direction and distance to current target
        direction_vec = target_m - p
        distance = float(np.linalg.norm(direction_vec))
        
        # Check if current waypoint reached
        if distance <= eps:
            if len(waypoints_m) > 1:  # Only log for multi-waypoint paths
                logger.debug(f"Reached waypoint {current_waypoint_idx + 1}/{len(waypoints_m)}")
            current_waypoint_idx += 1
            
            # Check if this was the last waypoint
            if current_waypoint_idx >= len(waypoints_m):
                return np.zeros(3, float), True
            
            # Move to next waypoint
            target_m = waypoints_m[current_waypoint_idx]
            direction_vec = target_m - p
            distance = float(np.linalg.norm(direction_vec))
        
        # Normalize direction
        if distance > 1e-9:
            direction = direction_vec / distance
        else:
            return np.zeros(3, float), len(waypoints_m) == 1  # True if single waypoint, False if multi
        
        # Calculate desired speed based on distance (braking distance)
        # Slow down when approaching target: v_max = sqrt(2 * a_max * distance)
        v_braking = float(np.sqrt(max(0.0, 2.0 * a_max * distance)))
        v_desired = min(max_velocity, v_braking)
        
        # Current speed along direction to target
        v_current = float(v @ direction)
        
        # Apply acceleration limits
        dv_max = a_max * dt
        v_new = np.clip(v_desired, v_current - dv_max, v_current + dv_max)
        
        # Ensure we don't overshoot by going too fast
        if distance < eps * 2:  # Very close to target
            v_new = min(v_new, distance / dt)  # Limit speed to reach target in one cycle
        
        velocity_cmd = direction * v_new
        return velocity_cmd, False

    return step


def move_to_starting_position(point_cloud: npt.ArrayLike, max_velocity: float = 0.005, 
                             a_max: float = 0.20, eps: float = 1e-3):
    try:
        point_cloud_array = np.asarray(point_cloud, dtype=float)
        if len(point_cloud_array) == 0:
            raise ValueError("Point cloud is empty")
        if point_cloud_array.shape[1] != 3:
            raise ValueError(f"Point cloud must have 3 columns (X, Y, Z), got {point_cloud_array.shape[1]}")
        
        target_mm = point_cloud_array[0:1]  # Take only first waypoint as array
        logger.info(f"Target position (m): {target_mm[0] * 1e-3}")
        logger.info("Going to initial position of path")

    except Exception as e:
        raise ValueError(f"Failed to extract target position from point cloud: {e}")
    
    # Use unified algorithm with only first waypoint
    return make_waypoint_follower(target_mm, max_velocity=max_velocity, a_max=a_max, eps=eps)


def path_follower_velocity(waypoints_mm: npt.ArrayLike, max_velocity: float = 0.02, 
                          a_max: float = 0.30, eps: float = 1e-3):
    """
    Follow multiple waypoints in sequence.
    """
    # Use unified algorithm with all waypoints
    return make_waypoint_follower(waypoints_mm, max_velocity=max_velocity, a_max=a_max, eps=eps)
