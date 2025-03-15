import math
import numpy as np
from project.common.util.math import make_transformation_matrix, get_world_pos


def test_camera_rotations():
    # Test different camera mounting positions
    camera_positions = {
        "backward_left": {
            "position": [0.4, 0.0, 0.4],
            "direction": [math.sqrt(2) / 2, 0, math.sqrt(2) / 2],
        },
        "backward_right": {
            "position": [-0.4, 0.0, 0.4],
            "direction": [-math.sqrt(2) / 2, 0, math.sqrt(2) / 2],
        },
        "forward_left": {
            "position": [0.4, 0.0, -0.4],
            "direction": [math.sqrt(2) / 2, 0, -math.sqrt(2) / 2],
        },
        "forward_right": {
            "position": [-0.4, 0.0, -0.4],
            "direction": [-math.sqrt(2) / 2, 0, -math.sqrt(2) / 2],
        },
    }

    # Fixed tag position in world (for simplicity)
    tag_world_pos = [1.0, 0.0, 0.0]  # 1 meter in x direction
    tag_world_dir = [1.0, 0.0, 0.0]  # facing positive x
    T_tag_world = make_transformation_matrix(
        np.array(tag_world_pos),
        np.array(tag_world_dir),
    )

    # Test rotation angles
    angles = [0, 45, 90, 135, 180]  # degrees

    for pos_name, camera_config in camera_positions.items():
        print(f"\nTesting {pos_name} camera configuration:")
        
        # Create camera-to-robot transform
        T_camera_robot = make_transformation_matrix(
            np.array(camera_config["position"]),
            np.array(camera_config["direction"]),
        )

        for angle in angles:
            # Convert angle to radians
            theta = math.radians(angle)
            
            # Create a simulated tag detection from camera's perspective
            # This simulates what the camera would see when the robot is rotated
            tag_camera_pos = [1.0, 0.0, 0.0]  # tag seen 1 meter in front of camera
            tag_camera_dir = [math.cos(theta), math.sin(theta), 0.0]  # rotate the tag's orientation
            T_tag_camera = make_transformation_matrix(
                np.array(tag_camera_pos),
                np.array(tag_camera_dir),
            )

            # Calculate robot's position in world frame
            T_robot_world = get_world_pos(T_tag_camera, T_camera_robot, T_tag_world)
            
            # Extract rotation angle from transformation matrix
            rotation_matrix = T_robot_world[:3, :3]
            robot_angle = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
            
            print(f"Input angle: {angle}°, Calculated robot angle: {robot_angle:.1f}°")


if __name__ == "__main__":
    test_camera_rotations()
