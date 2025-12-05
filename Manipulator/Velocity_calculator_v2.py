import numpy as np
import numpy.typing as npt
from typing import Tuple
import time
from .Path_follower import Path_Base
from .Manipulator import Telemetry
from scipy.optimize import bisect


class Path_follower(Path_Base):
    def __init__(self, path_keypoints: npt.ArrayLike,
                 max_velocity: float,
                 max_acceleration: float = 10,
                 min_velocity: float = 0.001,
                 aggregation_weight: float = 1.0, 
                 future_weight: float = 0.5, 
                 off_path_weight: float = 1.0,
                 next_target_tol: float = 0.001,
                 end_vector_weight: float = 1,
                 soft_corner_weight: float = 0.2,
                 sharp_corner_weight: float = 0.2,
                 telemetry: Telemetry | None = None
                 ) -> None:
        self.aggregation_weight = aggregation_weight
        self.soft_corner_weight = soft_corner_weight
        self.sharp_corner_weight = sharp_corner_weight
        self.future_weight = future_weight
        self.off_path_weight = off_path_weight
        path_keypoints = np.asarray(path_keypoints)
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration
        self.min_velocity = min_velocity
        self.next_target_tol = next_target_tol
        self.keypoints = path_keypoints
        self.end_vector_weight = end_vector_weight
        self.demand_velocity = np.zeros(path_keypoints.shape[1])
        self.current_vel = np.zeros(path_keypoints.shape[1]) 
        self.previous_vel = np.zeros(path_keypoints.shape[1])
        self.time = 0
        self.delta_t = 0.1
        self.previous_target = np.zeros(path_keypoints.shape[1])
        self.telemetry = telemetry
        self.add_end_vector()
        self.draw_keypoint_vectors()

    def add_end_vector(self):
        second_last_row = self.keypoints[-2]
        last_row = self.keypoints[-1]
        keypoints = self.keypoints.copy()

        end_vector = second_last_row - last_row

        end_norm = np.linalg.norm(end_vector)
        end_normalized = end_vector/end_norm

        weighted_end = self.end_vector_weight*end_normalized + last_row

        self.keypoints = np.vstack([keypoints, weighted_end])
    
        

    def draw_keypoint_vectors(self) -> None:
        n = self.keypoints.shape[0]-1
        l = self.keypoints.shape[1]
        self.connecting_vectors = np.empty((n,l))
        self.dist_vectors = np.empty(n)

        for i in range(n):
            connecting_vector = self.keypoints[i+1]-self.keypoints[i]
            dist = np.linalg.norm(connecting_vector)
            self.connecting_vectors[i] = connecting_vector
            self.dist_vectors[i] = dist
    
    def projecting_vector(self,aggregated_vector: npt.ArrayLike) -> np.ndarray:
        aggregated_vector = np.asarray(aggregated_vector)

        p_k = self.target - self.current_pos

    
        a_norm = np.linalg.norm(aggregated_vector)
        p_k_norm = np.linalg.norm(p_k)

        if a_norm == 0:
            normalized_a = np.zeros(self.keypoints.shape[1])
        else:
            normalized_a = aggregated_vector/a_norm

        if p_k_norm == 0:
            normalized_p_k = np.zeros(self.keypoints.shape[1])
        else:
            normalized_p_k = p_k/p_k_norm

        var1 = normalized_a+normalized_p_k
        var1_norm = np.linalg.norm(var1)

        if var1_norm == 0:
            projection_vec = np.zeros(self.keypoints.shape[1])
        else:
            projection_vec = normalized_p_k*np.linalg.norm(a_norm*(var1/var1_norm))

        return projection_vec
    
    def full_angle_projection_vector(self, aggregated_vector: npt.ArrayLike) -> np.array:

        p_k = self.target - self.current_pos

        projected_vector = (np.dot(aggregated_vector, p_k)/np.linalg.norm(p_k)**2)*p_k

        return projected_vector



    def aggregating_vector(self):
        total_weight = self.aggregation_weight
        exponent_weight = self.future_weight
        k = self.target_number
        p_k = self.target-self.current_pos
        p_k_dist = np.linalg.norm(p_k)

        n = self.dist_vectors.shape[0]
        inner_sum = 0
        outer_sum = np.zeros(self.connecting_vectors.shape[1])
        for i in range(k+1, n):
            for j in range(k + 1, i + 1):
                if j == k+1:
                    inner_sum += p_k_dist
                else:
                    inner_sum += self.dist_vectors[j-1]
            outer_sum += self.connecting_vectors[i]*np.exp(-(1/exponent_weight)*inner_sum)
            inner_sum = 0

        a_vec = total_weight*(p_k + outer_sum)
        return a_vec
    

    def aggregating_vector_update(self):
        total_weight = self.aggregation_weight
        exponent_weight = self.future_weight
        k = self.target_number
        p_k = self.target-self.current_pos
        p_k_dist = np.linalg.norm(p_k)

        n = self.keypoints.shape[0]

        future_points_sum = 0
        for i in range(k + 1, n):
            p_i = self.connecting_vectors[i - 1]
            for j in range(k, i):
                if j == k:
                    exponent_sum = p_k_dist
                else:
                    exponent_sum += self.dist_vectors[j - 1]
            future_points_sum += p_i*np.exp(-(1/exponent_weight)*exponent_sum)
        
        a_vec = total_weight*(p_k+future_points_sum)

        return a_vec
                

    def off_path_vector(self, projected_vector: npt.ArrayLike) -> np.ndarray:
        projected_vector = np.asarray(projected_vector)
        off_path_factor = self.off_path_weight
        p1 = self.previous_target
        p2 = self.target
        p3 = self.current_pos

        #Line direction 
        d = p2 - p1

        #p1 to p3 vector
        w = p3 - p1

        #projection factor
        t = np.dot(w, d) / np.dot(d, d)

        #perpendicular point on line 

        h = p1+t*d

        # Shortest vector from current pos to path
        normal_vector = h - p3
        self.telemetry.append("normal_vector_length", np.linalg.norm(normal_vector))

        #Vector from p3 to point on line

        v = off_path_factor*normal_vector
        
        total_velocity_vector = v + projected_vector

        return total_velocity_vector, v


    def clip_vector(self,total_velocity_vector: npt.ArrayLike) -> np.ndarray:
        total_velocity_vector = np.asarray(total_velocity_vector)

        total_velocity_vector_norm = np.linalg.norm(total_velocity_vector)
        p_k = self.target-self.current_pos
        p_k_norm = np.linalg.norm(p_k)
        if p_k_norm == 0:
            p_k_normalized = np.zeros(self.keypoints.shape[1])
        else:
            p_k_normalized = p_k/p_k_norm
        
        if np.abs(total_velocity_vector).max() > self.max_velocity:
            total_normalized = total_velocity_vector/total_velocity_vector_norm
            final_velocity = self.max_velocity*total_normalized
        elif total_velocity_vector_norm < self.min_velocity:
            final_velocity = p_k_normalized*self.min_velocity
        else:
            final_velocity = total_velocity_vector
    

        return final_velocity 
    
    def clip_vector_full_angle(self, total_velocity_vector: npt.ArrayLike) -> np.ndarray:
        total_velocity_vector = np.asarray(total_velocity_vector)

        p_k = self.target-self.current_pos
        p_k_norm = np.linalg.norm(p_k)
        p_k_normalized = p_k/p_k_norm

        dot_product = np.dot(total_velocity_vector, p_k)

        velocity_projected_on_path = dot_product / p_k_norm**2 * p_k

        if np.linalg.norm(velocity_projected_on_path) < self.min_velocity or dot_product < 0:
            final_velocity = self.min_velocity*p_k_normalized
        elif np.abs(total_velocity_vector).max() > self.max_velocity:
            final_velocity = self.max_velocity * total_velocity_vector / np.linalg.norm(total_velocity_vector)
        else:
            final_velocity = total_velocity_vector

        return final_velocity
      

    def send_to_manipulator(self,v: npt.ArrayLike) -> None:
        v = np.asarray(v)
        self.previous_vel = self.current_vel.copy()
        self.demand_velocity = v
        #print(v)
        #print(self.current_pos)

    def get_current_values(self):
        
        delta_v = self.demand_velocity-self.current_vel

        t_inter = delta_v/self.max_acceleration
        sign_vec = np.sign(t_inter)

        t_clipped = np.clip(abs(t_inter),None,self.delta_t)
        t_vec = np.ones(self.current_vel.shape)*self.delta_t
        t_rest = t_vec-t_clipped

        p_inter = self.current_pos+self.current_vel*t_clipped+0.5*sign_vec*self.max_acceleration*t_clipped**2
        self.current_pos = p_inter + self.demand_velocity*t_rest
        self.current_vel += sign_vec*self.max_acceleration*t_clipped

        self.time += self.delta_t


    def follow_path(self):
     
        complete = False
        self.current_pos = np.array(self.keypoints[0], dtype=np.float64) + np.random.normal(0, 1e-6, self.keypoints.shape[1])
        while not complete:
            final_v, complete = self(self.current_pos, None)
            self.send_to_manipulator(final_v)
            self.get_current_values()
            print(self.current_pos)
            time.sleep(0.1)

    def get_demand_accelerations(self, demand_velocity: npt.NDArray, current_velocity: npt.NDArray) -> npt.NDArray:
        difference_in_velocities = current_velocity - demand_velocity
        return difference_in_velocities / np.linalg.norm(difference_in_velocities) * self.max_acceleration

    def non_linearize_angle(self, normalized_angle: float) -> float:
        a = 1.0 - self.soft_corner_weight
        b = 1.0 - self.sharp_corner_weight
        f = lambda t: 3*(a-b+1/3)*t**3 + 3*(b-2*a)*t**2 + 3*a*t - normalized_angle
        t = bisect(f, 0, 1)
        return 3 * t**2 - 2*t**3

    def angle_dependant_velocity(self):
        total_weight = self.aggregation_weight
        exponent_weight = self.future_weight
        k = self.target_number
        p_k = self.target - self.current_pos
        p_k_dist = np.linalg.norm(p_k)
        p_k_normalized = p_k / p_k_dist

        n = self.keypoints.shape[0]

        future_points_sum = 0
        for i in range(k, n - 1):
            p_k = self.target-self.current_pos if i == k else self.connecting_vectors[i - 1]
            p_k1 = self.connecting_vectors[i]
            vector_angle_cos = np.clip(np.dot(p_k, p_k1) / (np.linalg.norm(p_k) * np.linalg.norm(p_k1)), -0.9999999, 0.999999)
            p_i = self.non_linearize_angle(np.arccos(vector_angle_cos) / np.pi)
            
            for j in range(k, i + 1):
                if j == k:
                    exponent_sum = p_k_dist
                else:
                    exponent_sum += self.dist_vectors[j - 1]
            future_points_sum += p_i*np.exp(-(1/exponent_weight)*exponent_sum)
        
        aggregation = total_weight*future_points_sum

        aggregation = 1 - np.minimum(aggregation, 1)

        self.telemetry.append('aggregation_factor', aggregation)

        return aggregation * p_k_normalized * self.max_velocity
    
    def clip_vector_angle(self, a_vec, off_path):

        p_k = self.target-self.current_pos
        p_k_normalized = p_k / np.linalg.norm(p_k)

        v_final = off_path + a_vec

        v_final_normalized = v_final / np.linalg.norm(v_final)
        
        
        if np.abs(v_final).max() > self.max_velocity:
            v_final = v_final_normalized * self.max_velocity
        elif np.linalg.norm(a_vec) < self.min_velocity:
            v_final = p_k_normalized * self.min_velocity
        
        return v_final

    def __call__(self, current_position: npt.ArrayLike, current_velocity: npt.ArrayLike) -> Tuple[npt.NDArray, npt.NDArray, bool]:
        current_position = np.asarray(current_position)
        current_velocity = np.asarray(current_velocity)
        complete = False
        if not hasattr(self, 'target'):
            self.i = 0
            self.target_number = self.i
            self.previous_target = current_position
            self.target = self.keypoints[self.i,:]
        
        self.current_pos = current_position

        #a_vec = self.aggregating_vector_update()
        #projected_vector = self.full_angle_projection_vector(a_vec)
        #total_velocity_vector, _ = self.off_path_vector(projected_vector)
        _, off_path = self.off_path_vector([1, 1])
        a_vec = self.angle_dependant_velocity()

        
        #final_v = self.clip_vector_full_angle(total_velocity_vector)
        final_v = self.clip_vector_angle(a_vec, off_path)

        demand_acceleration = self.get_demand_accelerations(final_v, current_velocity)
        self.previous_vel = final_v
        
        if self.telemetry is not None:
            self.telemetry.append('aggregating_vector', a_vec)
            #self.telemetry.append('projected_vector', projected_vector)
            #self.telemetry.append('total_velocity_vector', total_velocity_vector)
            self.telemetry.append('target_pos', self.target)
            self.telemetry.append('previous_target_pos', self.previous_target)
            self.telemetry.append('future_weight', self.future_weight)
            self.telemetry.append('aggregation_weight', self.aggregation_weight)
            self.telemetry.append('off_path_weight', self.off_path_weight)
            self.telemetry.append('next_target_tolerance', self.next_target_tol)
            self.telemetry.append('max_velocity', self.max_velocity)
            self.telemetry.append('max_acceleration', self.max_acceleration)
            self.telemetry.append('min_velocity', self.min_velocity)
            self.telemetry.append('end_vector_weight', self.end_vector_weight)
            self.telemetry.append('soft_corner_weight', self.soft_corner_weight)
            self.telemetry.append('sharp_corner_weight', self.sharp_corner_weight)

        while True:
            p1 = self.previous_target
            p2 = self.target
            p3 = self.current_pos

            #line distance
            previous_to_target = p2 - p1

            #p1 to p3 vector
            previous_to_current_vector = p3 - p1

            #projection factor
            relative_dis_to_target = np.dot(previous_to_current_vector, previous_to_target) / np.dot(previous_to_target, previous_to_target)

            if relative_dis_to_target >= 1 or np.linalg.norm(p2 - p3) <= self.next_target_tol:
                self.i += 1
                if self.i + 1>= self.keypoints.shape[0]:
                    complete = True
                    break
                else:
                    self.target = self.keypoints[self.i]
                    self.previous_target = self.keypoints[self.i-1]
                    self.target_number = self.i
            else:
                break

        return final_v, demand_acceleration, complete
    
    
            
                
            





            



