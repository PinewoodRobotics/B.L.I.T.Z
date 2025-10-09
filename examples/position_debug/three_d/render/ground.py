from ursina import Entity, Mesh, color
from ursina.vec3 import Vec3


class GroundGrid(Entity):
    def __init__(
        self,
        *,
        size: int = 10,  # number of cells per side
        spacing: float = 1.0,  # world-units between lines
        thickness: float = 0.01,  # line thickness
        line_color=color.gray,
        **kwargs
    ):
        super().__init__(**kwargs)

        verts = []
        lines = []
        half = size * spacing / 2

        # vertical lines (parallel to Z)
        for i in range(size + 1):
            x = -half + i * spacing
            start = Vec3(x, 0, -half)
            end = Vec3(x, 0, half)
            verts.extend([start, end])
            idx = len(verts)
            lines.append((idx - 2, idx - 1))

        # horizontal lines (parallel to X)
        for j in range(size + 1):
            z = -half + j * spacing
            start = Vec3(-half, 0, z)
            end = Vec3(half, 0, z)
            verts.extend([start, end])
            idx = len(verts)
            lines.append((idx - 2, idx - 1))

        mesh = Mesh(vertices=verts, triangles=lines, mode="line", thickness=thickness)  # type: ignore
        self.model = mesh
        self.color = line_color
