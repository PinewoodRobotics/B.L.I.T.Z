from ursina import *
from ursina.color import white
from .custom_lowlevel_rendering import get_cube_point_verts, get_cube_triangles


class BasePointCloud(Entity):
    def __init__(self, point_size: float = 0.01, color=color.white, parent=None):
        super().__init__(parent=parent)
        self.point_size = point_size
        self.color = color


class CubePointCloud(BasePointCloud):
    def __init__(
        self,
        points: list[tuple[float, float, float]],
        point_size: float = 0.01,
        color=color.white,
        parent=None,
    ):
        super().__init__(point_size, color, parent)
        self.points = points
        self._render_point_cloud()

    def _render_point_cloud(self):
        vertices = []
        tris = []
        colors = []

        for i, pos in enumerate(self.points):
            base_idx = i * 8
            x, y, z = pos
            vertices.extend(get_cube_point_verts(x, y, z, self.point_size))

            tris.extend(get_cube_triangles(base_idx))

            point_color = self.color[i] if isinstance(self.color, list) else self.color
            colors.extend([point_color] * 8)

        mesh = Mesh(vertices=vertices, triangles=tris, colors=colors, mode="triangle")
        self.model = mesh

    def extend_point_cloud(self, added_points: list[tuple[float, float, float]]):
        self.points.extend(added_points)
        self._render_point_cloud()


class NamedCubePointCloud(BasePointCloud):
    def __init__(
        self,
        points: dict[str, tuple[float, float, float]],
        point_size: float = 0.01,
        color=color.white,
        parent=None,
    ):
        super().__init__(point_size, color, parent)
        self.points_dict = points

    def _render_point_cloud(self):
        vertices = []
        tris = []
        colors = []

        for i, (name, pos) in enumerate(self.points_dict.items()):
            base_idx = i * 8
            x, y, z = pos
            vertices.extend(get_cube_point_verts(x, y, z, self.point_size))

            tris.extend(get_cube_triangles(base_idx))

            point_color = self.color[i] if isinstance(self.color, list) else self.color
            colors.extend([point_color] * 8)

        mesh = Mesh(vertices=vertices, triangles=tris, colors=colors, mode="triangle")
        self.model = mesh

    def extend_point_cloud(self, added_points: dict[str, tuple[float, float, float]]):
        self.points_dict.update(added_points)
        self._render_point_cloud()
