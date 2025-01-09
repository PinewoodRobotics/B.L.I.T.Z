from project.common.map.position import Pos2D, Vec2D


class Object:
    def __init__(self, width: int, height: int, pos: Pos2D):
        self.pos = pos
        self.width = width
        self.height = height


class DynamicObject(Object):
    def __init__(
        self, width: int, height: int, pos: Pos2D, velocity: Vec2D, rotation: float
    ):
        super().__init__(width, height, pos)
        self.velocity = velocity
        self.rotation = rotation
