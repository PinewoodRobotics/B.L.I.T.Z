from ursina import *
from render.ground import GroundGrid
from render.axes import Axes


class Object:
    def __init__(self, name: str, entity: Entity, last_update: float):
        self._name = name
        self._entity = entity
        self._last_update = last_update

    def get_entity(self) -> Entity:
        self._last_update = time.time()
        return self._entity

    def get_last_update(self) -> float:
        return self._last_update

    def get_name(self) -> str:
        return self._name


class World:
    def __init__(self, add_base_objects: bool = True):
        self.objects: dict[str, Object] = {}

        self.camera = EditorCamera(move_speed=0.5)
        self.camera.rotation = (90, 0, 0)

        if add_base_objects:
            self.add_object(
                "ground",
                GroundGrid(
                    size=30, spacing=1.0, thickness=0.01, line_color=color.light_gray
                ),
            )

            self.add_object(
                "axes",
                Axes(length=1, thickness=0.02),
            )

    def contains_object(self, name: str) -> bool:
        return name in self.objects

    def add_object(self, name: str, entity: Entity):
        self.objects[name] = Object(name, entity, time.time())

    def get_object(self, name: str) -> Object:
        return self.objects[name]

    def get_all_objects(self) -> list[Object]:
        return list(self.objects.values())

    def remove_object(self, name: str):
        destroy(self.objects[name].get_entity())
        del self.objects[name]
