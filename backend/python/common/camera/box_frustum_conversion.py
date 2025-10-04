import numpy as np


def bbox_to_frustum(K, bbox, depth):
    """
    Converts a bounding box and depth into a frustum in 3D space.

    :param K: Intrinsic camera matrix (3x3).
    :param bbox: Bounding box as (x_min, y_min, x_max, y_max).
    :param depth: The length of the frustum point vectors.
    :return: Frustum points as a list of tuples (x, y, z).
    """
    fx, fy = K[0][0], K[1][1]
    cx, cy = K[0][2], K[1][2]

    x_min, y_min, x_max, y_max = bbox

    # Compute normalized image plane coordinates
    corners = np.array(
        [
            [-(x_min - cx) / fx, -(y_min - cy) / fy],  # Upper left
            [-(x_max - cx) / fx, -(y_min - cy) / fy],  # Upper right
            [-(x_max - cx) / fx, -(y_max - cy) / fy],  # Lower right
            [-(x_min - cx) / fx, -(y_max - cy) / fy],  # Lower left
        ]
    )

    # Map corners to 3D frustum points with correct vector length (depth)
    frustum_points: list[tuple[float, float, float]] = []
    for x, y in corners:
        # Compute the direction vector
        direction = np.array([x, y, 1.0])  # z=1 is used for the canonical optical axis
        # Scale the direction vector to the desired depth
        scaled_vector = direction * (depth / np.linalg.norm(direction))
        frustum_points.append(tuple(scaled_vector))

    return frustum_points


def transform_frustum(
    frustum_list: list[tuple[float, float, float]],
    *args,
    rotation: tuple[float, float],
    linear: tuple[float, float, float],
) -> list[tuple[float, float, float]]:
    cos_theta, sin_theta = rotation
    tx, ty, tz = linear

    rotation_matrix = np.array(
        [[cos_theta, -sin_theta, 0], [sin_theta, cos_theta, 0], [0, 0, 1]]
    )

    transformed_frustum = []
    for point in frustum_list:
        x, y, z = point

        rotated_point = rotation_matrix @ np.array([x, y, z])

        transformed_point = rotated_point + np.array([tx, ty, tz])

        transformed_frustum.append(tuple(transformed_point))

    return transformed_frustum
