import numpy as np
from ursina import Entity, Vec3, color, Texture
from PIL import Image
from ursina import *


class ImageObject(Entity):
    def __init__(
        self,
        image_array: np.ndarray,
        *,
        position: tuple[float, float, float] = (0, 0, 0),
        scale: float = 1,
        **kwargs
    ):
        super().__init__(position=position, **kwargs)

        self.image_array = image_array

        # Calculate aspect ratio based on image dimensions
        self.height, self.width = image_array.shape[:2]
        self.aspect_ratio = self.width / self.height

        # Set scale using the single scale parameter
        self.scale_value = scale

        self._create_plane()

    def _create_plane(self):
        self.plane = Entity(
            parent=self,
            model="quad",
            scale=Vec3(self.scale_value * self.aspect_ratio, self.scale_value, 1),
            position=Vec3(0, 0, 0),
            texture=self._create_texture(),
            color=color.white,
            double_sided=True,
        )

    def _create_texture(self) -> Texture:
        if len(self.image_array.shape) == 2:
            image = Image.fromarray(self.image_array).convert("RGBA")
        else:
            image = Image.fromarray(self.image_array).convert("RGBA")
        texture = Texture(image)
        texture.filtering = None
        return texture

    def update_image(self, new_image_array: np.ndarray):
        self.image_array = new_image_array

        # Update aspect ratio with new image
        height, width = new_image_array.shape[:2]
        aspect_ratio = width / height

        # Update plane scale
        self.plane.scale = Vec3(self.scale_value * aspect_ratio, self.scale_value, 1)
        self.plane.texture = self._create_texture()

    def set_position(self, position: tuple[float, float, float]):
        self.position = Vec3(*position)

    def set_scale(self, scale: float):
        self.scale_value = scale

        # Update with current aspect ratio
        height, width = self.image_array.shape[:2]
        aspect_ratio = width / height

        self.plane.scale = Vec3(scale * aspect_ratio, scale, 1)

    def update_texture(self, new_image_array: np.ndarray):
        self.image_array = new_image_array
        height, width = new_image_array.shape[:2]
        aspect_ratio = width / height
        self.plane.scale = Vec3(self.scale_value * aspect_ratio, self.scale_value, 1)
        self.plane.texture = self._create_texture()
