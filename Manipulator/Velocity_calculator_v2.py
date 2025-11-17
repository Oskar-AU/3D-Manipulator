import numpy as np
import numpy.typing as npt
from typing import Tuple
import time
from .Path_follower import Path_Base


class Path_follower(Path_Base):
    def __init__(self, path_keypoints: npt.ArrayLike,max_velocity: float,max_acceleration: float,min_velocity: float,projected_total_weight: float=1.0, projected_exponent_weight: float=0.5, off_path_weight: float=1.0) -> None:
        self.projected_total_weight = projected_total_weight
        self.projected_exponent_weight = projected_exponent_weight
        self.off_path_weight = off_path_weight
        path_keypoints = np.asarray(path_keypoints)
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration
        self.min_velocity = min_velocity
        self.keypoints = path_keypoints
        self.current_pos = np.array(path_keypoints[0], dtype=np.float64)
        self.demand_velocity = np.zeros(3)
        self.current_vel = np.zeros(3) 
        self.previous_vel = np.zeros(3)
        self.time = 0
        self.delta_t = 0.1
        self.previous_target = np.zeros(3)
        self.draw_keypoint_vectors()

    def draw_keypoint_vectors(self) -> None:
        n = self.keypoints.shape[0]-1
        self.connecting_vectors = np.empty((n,3))
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
            normalized_a = np.zeros(3)
        else:
            normalized_a = aggregated_vector/a_norm

        if p_k_norm == 0:
            normalized_p_k = np.zeros(3)
        else:
            normalized_p_k = p_k/p_k_norm

        var1 = normalized_a+normalized_p_k
        var1_norm = np.linalg.norm(var1)

        if var1_norm == 0:
            projection_vec = np.zeros(3)
        else:
            projection_vec = normalized_p_k*np.linalg.norm(a_norm*(var1/var1_norm))

        return projection_vec


    def aggregating_vector(self):
        total_weight = self.projected_total_weight
        exponent_weight = self.projected_exponent_weight
        k = self.target_number
        p_k = self.target-self.current_pos
        p_k_dist = np.linalg.norm(p_k)

        n = self.dist_vectors.shape[0]
        inner_sum = 0
        outer_sum = np.zeros(3)
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
                

    def off_path_vector(self,projected_vector: npt.ArrayLike) -> np.ndarray:
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

        #Vector from p3 to point on line

        v = off_path_factor*(h - p3)
        
        total_velocity_vector = v + projected_vector

        return total_velocity_vector


    def clip_vector(self,total_velocity_vector: npt.ArrayLike) -> np.ndarray:
        total_velocity_vector = np.asarray(total_velocity_vector)

        total_velocity_vector_norm = np.linalg.norm(total_velocity_vector)
        p_k = self.target-self.current_pos
        p_k_norm = np.linalg.norm(p_k)
        if p_k_norm == 0:
            p_k_normalized = np.zeros(3)
        else:
            p_k_normalized = p_k/p_k_norm

        if abs(total_velocity_vector).max() > self.max_velocity:
            total_normalized = total_velocity_vector/total_velocity_vector_norm
            final_velocity = self.max_velocity*total_normalized
        elif total_velocity_vector_norm == 0:
            final_velocity = p_k_normalized*self.min_velocity

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
        t_vec = np.ones(3)*self.delta_t
        t_rest = t_vec-t_clipped

        p_inter = self.current_pos+self.current_vel*t_clipped+0.5*sign_vec*self.max_acceleration*t_clipped**2
        self.current_pos = p_inter + self.demand_velocity*t_rest
        self.current_vel += sign_vec*self.max_acceleration*t_clipped

        self.time += self.delta_t


    def follow_path(self):
     
        complete = False
        
        while not complete:
            print(self.current_pos)
            final_v,complete = self(self.current_pos, None)
            self.send_to_manipulator(final_v)
            self.get_current_values()
            time.sleep(0.1)

    def __call__(self, current_position: npt.ArrayLike, _) -> Tuple[np.ndarray, bool]:
        current_position = np.asarray(current_position)
        complete = False
        if not hasattr(self, 'target'):
            self.i = 0
            self.target_number = self.i
            self.previous_target = self.keypoints[self.i,:]
            self.target = self.keypoints[self.i+1,:]
        
        self.current_pos = current_position

        a_vec = self.aggregating_vector()
        projected_vector = self.projecting_vector(a_vec)
        total_velocity_vector = self.off_path_vector(projected_vector)
        final_v = self.clip_vector(total_velocity_vector)
        
        p1 = self.previous_target
        p2 = self.target
        p3 = self.current_pos

        #line distance
        d = p2 - p1

        #p1 to p3 vector
        w = p3 - p1

        #projection factor
        t = np.dot(w, d) / np.dot(d, d)

        if t > 0.98:
            self.i += 1
            if self.i+1 > self.keypoints.shape[0]:
                complete = True
            else:
                self.target = self.keypoints[self.i+1]
                self.previous_target = self.keypoints[self.i]
                self.target_number = self.i

        return final_v, complete
    
    
            
                
            





            



