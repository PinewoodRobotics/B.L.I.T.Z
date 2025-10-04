import math
import numpy as np
from ursina import Entity, Vec3, Text, color


class AprilTag(Entity):
    def __init__(
        self,
        tag_id: int,
        *,
        position: tuple[float, float, float] = (0, 0, 0),
        direction: tuple[float, float, float] = (0, 0, 1),
        size: float = 1,
        thickness: float = 0.02,
        tag_color=color.white,
        text_color=color.black,
        text_offset: float = 0.1,
        **kwargs
    ):
        super().__init__(position=position, **kwargs)

        self.tag_id = tag_id
        self.size = size
        self.thickness = thickness
        self.tag_color = tag_color
        self.text_color = text_color
        self.text_offset = text_offset

        # create the tag “box” and the floating text
        self.box = Entity(
            parent=self,
            model="cube",
            scale=Vec3(size, size, thickness),
            color=tag_color,
            position=Vec3(0, 0, 0),
        )
        self.label = Text(
            text=str(tag_id),
            parent=self,
            world_space=True,
            billboard=True,
            origin=(0.5, 0.5),
            position=Vec3(0, 0, text_offset),
            scale=4,
            color=text_color,
        )

        # orient to initial direction
        self.set_direction(direction)

    def set_position(self, position: tuple[float, float, float]):
        """Move the tag (its children follow automatically)."""
        self.position = Vec3(*position)

    def set_direction(self, direction: tuple[float, float, float]):
        """
        Orient so the +Z face of the cube points along `direction`.
        Computes pitch (X) and yaw (Y); roll stays zero.
        """
        x, y, z = Vec3(*direction).normalized()
        # yaw: rotate around Y so Z faces toward (x,z)
        yaw = math.degrees(math.atan2(x, z))
        # pitch: rotate around X so Z lifts/drops toward y
        pitch = math.degrees(math.atan2(y, math.sqrt(x * x + z * z)))
        self.rotation = Vec3(pitch, yaw, 0)

    def set_rotation_matrix(self, R: np.ndarray):
        """
        Apply a 3×3 rotation matrix R. Assumes R transforms local→world.
        Decomposes into X(pitch), Y(yaw), Z(roll) Tait–Bryan angles.
        """
        assert R.shape == (3, 3), "rotation_matrix must be 3×3"
        # following conventions: R = Rz(roll) Ry(yaw) Rx(pitch)
        # extract pitch = atan2(-R[2,1], R[2,2])
        pitch = math.degrees(math.atan2(-R[2, 1], R[2, 2]))
        # extract yaw   = atan2(R[2,0], math.sqrt(R[2,1]**2 + R[2,2]**2))
        yaw = math.degrees(math.atan2(R[2, 0], math.sqrt(R[2, 1] ** 2 + R[2, 2] ** 2)))
        # extract roll  = atan2(-R[0,1], R[1,1])
        roll = math.degrees(math.atan2(-R[0, 1], R[1, 1]))
        self.rotation = Vec3(pitch, yaw, roll)

    def set_size(self, size: float, thickness: float = 0.02):
        """Resize the square face and optionally its thickness."""
        self.size = size
        self.thickness = thickness
        self.box.scale = Vec3(self.size, self.size, self.thickness)

    def set_tag_color(self, c):
        """Change the color of the tag’s face."""
        self.tag_color = c
        self.box.color = c

    def set_text_color(self, c):
        """Change the color of the tag’s ID text."""
        self.text_color = c
        self.label.color = c

    def set_text_offset(self, offset: float):
        """Move the text closer to or further from the face."""
        self.text_offset = offset
        self.label.position = Vec3(0, 0, self.text_offset)

    def set_tag_id(self, tag_id: int):
        """Update the numeric ID displayed."""
        self.tag_id = tag_id
        self.label.text = str(tag_id)
