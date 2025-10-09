def get_cube_point_verts(x, y, z, side_size):
    half_size = side_size / 2
    return [
        (x - half_size, y - half_size, z - half_size),
        (x + half_size, y - half_size, z - half_size),
        (x + half_size, y + half_size, z - half_size),
        (x - half_size, y + half_size, z - half_size),
        (x - half_size, y - half_size, z + half_size),
        (x + half_size, y - half_size, z + half_size),
        (x + half_size, y + half_size, z + half_size),
        (x - half_size, y + half_size, z + half_size),
    ]


def get_cube_triangles(base_idx):
    faces = [
        [0, 1, 2, 3],  # front
        [1, 5, 6, 2],  # right
        [5, 4, 7, 6],  # back
        [4, 0, 3, 7],  # left
        [3, 2, 6, 7],  # top
        [4, 5, 1, 0],  # bottom
    ]

    triangles = []
    for face in faces:
        triangles.append((base_idx + face[0], base_idx + face[1], base_idx + face[2]))
        triangles.append((base_idx + face[0], base_idx + face[2], base_idx + face[3]))

    return triangles
