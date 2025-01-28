import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Rotation Matrix (example from earlier code)
rotation_vector = np.array([0.0, -1.0, 0.0])  # Direction the tag points
rotation_vector = rotation_vector / np.linalg.norm(rotation_vector)  # Normalize

# Reference frame vectors
reference_vector = np.array([1.0, 0.0, 0.0])
if np.allclose(rotation_vector, reference_vector):
    reference_vector = np.array([0.0, 1.0, 0.0])  # Handle parallel case

v1 = np.cross(reference_vector, rotation_vector)
v1 = v1 / np.linalg.norm(v1)

v2 = np.cross(rotation_vector, v1)
v2 = v2 / np.linalg.norm(v2)

# Rotation matrix
rotation_matrix = np.column_stack((v1, v2, rotation_vector))

# Create vertices for a square plate (AprilTag-like marker)
tag_size = 0.5
vertices = np.array(
    [
        [-tag_size, -tag_size, 0],  # Bottom-left
        [tag_size, -tag_size, 0],  # Bottom-right
        [tag_size, tag_size, 0],  # Top-right
        [-tag_size, tag_size, 0],  # Top-left
    ]
)

# Rotate the vertices
rotated_vertices = vertices @ rotation_matrix.T

# Create the figure
fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111, projection="3d")

# Plot world frame axes
ax.quiver(0, 0, 0, 1, 0, 0, color="r", label="World X", length=1)
ax.quiver(0, 0, 0, 0, 1, 0, color="g", label="World Y", length=1)
ax.quiver(0, 0, 0, 0, 0, 1, color="b", label="World Z", length=1)

# Plot rotated frame axes
origin = np.array([0, 0, 0])
rotated_x = rotation_matrix[:, 0]  # Rotated X-axis
rotated_y = rotation_matrix[:, 1]  # Rotated Y-axis
rotated_z = rotation_matrix[:, 2]  # Rotated Z-axis

ax.quiver(
    0, 0, 0, *rotated_x, color="r", linestyle="dashed", label="Rotated X", length=1
)
ax.quiver(
    0, 0, 0, *rotated_y, color="g", linestyle="dashed", label="Rotated Y", length=1
)
ax.quiver(
    0, 0, 0, *rotated_z, color="b", linestyle="dashed", label="Rotated Z", length=1
)

# Plot the AprilTag square
ax.plot_surface(
    rotated_vertices[[0, 1, 2, 3, 0], 0].reshape((5, 1)),
    rotated_vertices[[0, 1, 2, 3, 0], 1].reshape((5, 1)),
    rotated_vertices[[0, 1, 2, 3, 0], 2].reshape((5, 1)),
    color="gray",
    alpha=0.5,
)

# Add a pattern on the tag (X pattern)
pattern_vertices = np.array(
    [
        [-tag_size, -tag_size, 0],  # Bottom-left to top-right
        [tag_size, tag_size, 0],
        [-tag_size, tag_size, 0],  # Top-left to bottom-right
        [tag_size, -tag_size, 0],
    ]
)
rotated_pattern = pattern_vertices @ rotation_matrix.T

ax.plot(
    rotated_pattern[[0, 1], 0],
    rotated_pattern[[0, 1], 1],
    rotated_pattern[[0, 1], 2],
    "k-",
    linewidth=2,
)
ax.plot(
    rotated_pattern[[2, 3], 0],
    rotated_pattern[[2, 3], 1],
    rotated_pattern[[2, 3], 2],
    "k-",
    linewidth=2,
)

# Add normal vector from center of tag
center = np.array([0, 0, 0])
normal = rotation_vector * tag_size
ax.quiver(
    center[0],
    center[1],
    center[2],
    normal[0],
    normal[1],
    normal[2],
    color="purple",
    arrow_length_ratio=0.2,
    label="Tag Normal",
)

# Add labels and adjust
ax.set_xlim([-1, 1])
ax.set_ylim([-1, 1])
ax.set_zlim([-1, 1])
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.legend()
plt.title("World Axes vs Rotated Axes")
plt.show()
