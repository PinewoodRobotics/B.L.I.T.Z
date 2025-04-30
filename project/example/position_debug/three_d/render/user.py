from ursina import *


class FlyController(Entity):
    def __init__(
        self, speed: float = 5, sensitivity: float = 40, fov: float = 90, **kwargs
    ):
        super().__init__(**kwargs)

        camera.parent = self
        camera.position = (0, 0, 0)
        camera.rotation = (0, 0, 0)

        camera.fov = fov
        self._locked_fov = fov

        self.speed = speed
        self.sensitivity = sensitivity

        mouse.locked = True
        mouse.visible = False

    def update(self):
        camera.fov = self._locked_fov

        self.rotation_x -= mouse.velocity[1] * self.sensitivity
        self.rotation_y += mouse.velocity[0] * self.sensitivity
        self.rotation_x = clamp(self.rotation_x, -90, 90)

        direction = Vec3(
            held_keys["d"] - held_keys["a"],
            held_keys["e"] - held_keys["q"],
            held_keys["w"] - held_keys["s"],
        )
        if direction != Vec3(0, 0, 0):
            move_vec = (
                self.forward * direction.z
                + self.right * direction.x
                + self.up * direction.y
            )
            self.position += move_vec * self.speed * time.dt

    def input(self, key):
        if key in ("scroll up", "scroll down"):
            return
