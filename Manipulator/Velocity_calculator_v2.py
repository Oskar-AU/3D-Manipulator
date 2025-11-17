import numpy as np
from typing import Tuple
import time
import matplotlib.animation as ani
import matplotlib.pyplot as plt

class Path_initializer:
    def __init__(self,path_keypoints,max_velocity: float,max_acceleration: float,min_velocity: float) -> None:
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration
        self.min_velocity = min_velocity
        self.keypoints = path_keypoints
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
        
    


class Path_follower():
    def __init__(self, path_class: Path_initializer) -> None:
        self.max_velocity = path_class.max_velocity
        self.max_acceleration = path_class.max_acceleration
        self.min_velocity = path_class.min_velocity
        self.keypoints = path_class.keypoints
        self.connecting_vectors = path_class.connecting_vectors
        self.dist_vectors = path_class.dist_vectors
        self.current_pos = np.array(path_class.keypoints[0], dtype=np.float64)
        self.demand_velocity = np.zeros(3)
        self.current_vel = np.zeros(3) 
        self.previous_vel = np.zeros(3)
        self.time = 0
        self.delta_t = 0.1
        self.previous_target = np.zeros(3)
        
    def get_max_velocity_vector(self,vector_number):
        connecting_vector = self.connecting_vectors[vector_number,:]
        normalized_vector = connecting_vector/np.linalg.norm(connecting_vector)
        v_max_vector = self.max_velocity*normalized_vector
        return v_max_vector
    
    def projecting_vector(self,a):

        p_k = self.target - self.current_pos

    
        a_norm = np.linalg.norm(a)
        p_k_norm = np.linalg.norm(p_k)

        if a_norm == 0:
            normalized_a = np.zeros(3)
        else:
            normalized_a = a/a_norm

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
        total_weight = 1
        exponent_weight = 0.5
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
                

    def off_path_vector(self,projected_vector):
        off_path_factor = 1
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


    def clip_vector(self,total_velocity_vector):


        total_velocity_vector_norm = np.linalg.norm(total_velocity_vector)
        p_k = self.target-self.current_pos
        p_k_norm = np.linalg.norm(p_k)
        if p_k_norm == 0:
            p_k_normalized == np.zeros(3)
        else:
            p_k_normalized = p_k/p_k_norm

        if abs(total_velocity_vector).max() > self.max_velocity:
            total_normalized = total_velocity_vector/total_velocity_vector_norm
            final_velocity = self.max_velocity*total_normalized
        elif total_velocity_vector_norm == 0:
            final_velocity = p_k_normalized*self.min_velocity

        return final_velocity 

            
    
        
        

    def adjust_velocity(self,v1):

        ortho_dist_factor = 10
        target_dist_factor = 1
        next_vel_factor = 2
        
        target_path = np.array([self.previous_target,self.target])
        current_pos = self.current_pos

        
        #Distance to target line
        line = target_path[1]-target_path[0]
        line2 = current_pos-target_path[0]

        t = np.dot(line2,line)/np.dot(line,line)

        p_closest = target_path[0]+t*line
        ortho_vec = (p_closest - current_pos)*ortho_dist_factor

        target_vec = (self.target-current_pos)*target_dist_factor

        

        v_tot_vec = ortho_vec+target_vec

        v_tot_norm = v_tot_vec/np.linalg.norm(v_tot_vec)

        v_desired = self.max_velocity*v_tot_norm
        #print(self.aggregating_vector())


        return v_desired
            



    def send_to_manipulator(self,v):
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
    
        while complete == False:
            final_v,complete = self(self.current_pos)
            self.send_to_manipulator(final_v)
            self.get_current_values()
            time.sleep(0.1)
            print(self.current_vel)

    def __call__(self, current_position):
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
    
    
            
                
                
                


path_keypoints = np.array(([0,0,0],[0,0,1],[0,1,1],[1,1,1],[1,0,1],[1,0,0],[1,1,0],[0,1,0]))

path = Path_initializer(path_keypoints,0.1,10,0.01)

pf = Path_follower(path)
pf.follow_path()
            


            



