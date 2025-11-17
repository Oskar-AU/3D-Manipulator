#!/usr/bin/env python3
"""
IGES to XYZ Coordinate Converter
Converts IGES files to XYZ coordinates with specified point spacing
"""

import numpy as np
import pyiges
import pyvista as pv
import os
from tqdm import tqdm
class IgesToXyz:
    def __init__(self, iges_filename,spacing_mm=0.5):
        self.iges_filename = iges_filename
        self.spacing_mm = spacing_mm
        self.output_file = "xyz_coordinates.txt"
        self.origin = np.array([0, 0, 0])


    def convert_iges_to_xyz(self):
        """
        Convert IGES file to XYZ coordinates
        
        Args:
            iges_filename (str): Input IGES file path
            output_file (str): Output file for XYZ coordinates
            spacing_mm (float): Distance between points in mm (default: 0.1mm)
        
        Returns:
            list: List of XYZ coordinate points
        """
        print(f"Reading IGES file: {self.iges_filename}")
        
        # Load the IGES file
        iges = pyiges.read(self.iges_filename)
        print(f"Successfully loaded IGES file with {len(iges)} entities")
        
        # Convert to VTK format for point extraction
        all_points = []
        for entity in tqdm(iges, desc="Converting entities to vtk"):
            try:
                vtk_obj = entity.to_vtk()
                if vtk_obj is not None:
                    # Convert to PyVista object
                    pv_obj = pv.wrap(vtk_obj)
                    
                    # Extract points based on object type
                    if hasattr(pv_obj, 'points') and pv_obj.points is not None:
                        points = pv_obj.points
                        all_points.extend(points)
            except Exception as e:
                continue  # Skip problematic entities
        
        print(f"Extracted {len(all_points)} points from IGES")
        
        if not all_points:
            raise ValueError("No valid points found in IGES file")
        
        # Remove duplicate points (tolerance for floating point comparison)
        unique_points = []
        tolerance = 1e-6  # 1 micrometer tolerance
        
        for point in all_points:
            is_duplicate = False
            for existing_point in unique_points:
                if np.linalg.norm(np.array(point) - np.array(existing_point)) < tolerance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_points.append(point)
        
        print(f"After removing duplicates: {len(unique_points)} points")
        
        # Order points starting from the one closest to origin [0,0,0]
        ordered_points = self.order_points_from_origin(unique_points)
        
        # Extract points with specified spacing
        arc_length_points = self.extract_arc_length_points(ordered_points, self.spacing_mm)

        # Write XYZ coordinates file
        with open(self.output_file, 'w') as f:
            f.write("X\tY\tZ\n")  # Header for Excel
            for coord in arc_length_points:
                f.write(f"{coord[0]:.6f}\t{coord[1]:.6f}\t{coord[2]:.6f}\n")
        
        print(f"Successfully wrote {len(arc_length_points)} coordinates to: {self.output_file}")
        return arc_length_points

    def order_points_from_origin(self,points):
        """Order points starting from the one closest to origin"""
        if not points:
            return []
        
        # Find point closest to origin
        distances = [np.linalg.norm(np.array(point) - self.origin) for point in points]
        start_idx = np.argmin(distances)
        start_point = points[start_idx]
        
        print(f"Starting from point closest to origin: {start_point}")
        
        # Simple ordering by building a path through nearest neighbors
        ordered = [start_point]
        remaining = [p for i, p in enumerate(points) if i != start_idx]
        
        current_point = start_point
        while remaining:
            # Find nearest remaining point
            distances = [np.linalg.norm(np.array(p) - np.array(current_point)) for p in remaining]
            nearest_idx = np.argmin(distances)
            nearest_point = remaining.pop(nearest_idx)
            ordered.append(nearest_point)
            current_point = nearest_point
        
        return ordered

    def extract_arc_length_points(self,points, spacing_mm):
        """Extract points along path with specified arc-length spacing"""
        if len(points) < 2:
            return points
        
        print(f"Extracting points with {spacing_mm}mm arc-length spacing...")
        
        # Calculate cumulative distances
        points_array = np.array(points)
        distances = np.sqrt(np.sum(np.diff(points_array, axis=0)**2, axis=1))
        cumulative_distances = np.concatenate([[0], np.cumsum(distances)])
        
        total_length = cumulative_distances[-1]
        print(f"Total path length: {total_length:.2f}mm")
        
        # Generate evenly spaced distances
        num_points = int(total_length / spacing_mm) + 1
        target_distances = np.linspace(0, total_length, num_points)
        
        print(f"Generating {num_points} points with {spacing_mm}mm spacing")
        
        # Interpolate points at target distances
        interpolated_points = []
        for target_dist in target_distances:
            # Find the segment containing this distance
            segment_idx = np.searchsorted(cumulative_distances, target_dist) - 1
            segment_idx = max(0, min(segment_idx, len(points) - 2))
            
            # Interpolate within the segment
            dist_in_segment = target_dist - cumulative_distances[segment_idx]
            segment_length = cumulative_distances[segment_idx + 1] - cumulative_distances[segment_idx]
            
            if segment_length > 0:
                t = dist_in_segment / segment_length
                interpolated_point = (1 - t) * points_array[segment_idx] + t * points_array[segment_idx + 1]
            else:
                interpolated_point = points_array[segment_idx]
            
            interpolated_points.append(interpolated_point)
        
        # Verify spacing
        if len(interpolated_points) > 1:
            actual_distances = np.sqrt(np.sum(np.diff(interpolated_points, axis=0)**2, axis=1))
            avg_spacing = np.mean(actual_distances)
            print(f"Average spacing achieved: {avg_spacing:.3f}mm (target: {spacing_mm}mm)")
        
        return interpolated_points
    
    def get_vel_acc(self,max_velocity=0.1, max_acceleration=10, max_deacceleration=10):
        """Calculate velocity and acceleration profiles for the path"""
        # Placeholder for future implementation

        path_coordinates = self.extract_arc_length_points(self.order_points_from_origin(self.all_points), self.spacing_mm)

        velocities = []
        accelerations = []
        lookahead = 5  # Number of points to look ahead for velocity calculation

        for i in range(1, len(path_coordinates)):
            pass

def main():
    # Configuration
    input_file = "path3D.IGS"
    output_file = "xyz_coordinates.txt"
    spacing_mm = 0.1  # Distance between points in mm
    
    print("IGES to XYZ Converter")
    print("=" * 21)
    print(f"Point spacing: {spacing_mm}mm")
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found!")
        print("Available IGES files in current directory:")
        for file in os.listdir('.'):
            if file.lower().endswith('.igs'):
                print(f"  {file}")
        return
    
    try:
        # Convert the file
        p = IgesToXyz(input_file, spacing_mm)
        points = p.convert_iges_to_xyz()
        
        print(f"\nConversion complete!")
        print(f"File created: {output_file}")
        print(f"Total points: {len(points)}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()