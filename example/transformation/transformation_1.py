import numpy as np

from blitz.common.util.math import (
    get_robot_in_world,
    make_transformation_matrix_p_d,
)


tag_in_world_position = np.array([0.0, 0.0, 1.0])
tag_in_world_direction = -1 * np.array([0.0, 0.0, -1.0])

tag_in_world_transform_matrix = make_transformation_matrix_p_d(
    tag_in_world_position, tag_in_world_direction
)

print(tag_in_world_transform_matrix)

print()

"""
[[ 0.99760187  0.01554993  0.06744438]
 [-0.01111341  0.99777991 -0.06566367]
 [-0.06831571  0.06475665  0.99555993]]
 
[[ 0.99626374 -0.01407815 -0.08520752]
 [ 0.02954412  0.98265404  0.18307988]
 [ 0.08115209 -0.18491323  0.97939849]]
"""


tag_in_camera_position = np.array([0, 0, 1])
tag_in_camera_direction = np.array([0, 0, 1])

tag_in_camera_transformation_matrix = make_transformation_matrix_p_d(
    tag_in_camera_position, tag_in_camera_direction
)

print(tag_in_camera_transformation_matrix)
print()


camera_in_world = get_robot_in_world(
    tag_in_camera_transformation_matrix, tag_in_world_transform_matrix
)

print(camera_in_world)
