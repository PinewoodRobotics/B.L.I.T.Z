from dataclasses import dataclass


@dataclass
class Vec2D:
    x: float
    y: float


@dataclass
class Vec2DInt(Vec2D):
    x: int
    y: int


@dataclass
class Vec2DI(Vec2D):
    x: float
    y: float
    i: int
