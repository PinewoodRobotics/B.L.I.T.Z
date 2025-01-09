from enum import Enum
from project.common.map.object import DynamicObject, Object
from project.common.map.position import Pos2D
import random


class MapType(Enum):
    EMPTY = 0
    WALL = 1
    OBJECT = 2


class PlayingMap:
    def __init__(self, map_width: int, map_height: int):
        self.static_objects: dict[int, Object] = {}
        self.dynamic_objects: dict[int, DynamicObject] = {}
        self.map_width = map_width
        self.map_height = map_height

    def add_static_object(self, object: Object) -> int:
        id = random.randint(0, 1000000)
        self.static_objects[id] = object

        return id

    def add_dynamic_object(self, object: DynamicObject) -> int:
        id = random.randint(0, 1000000)
        self.dynamic_objects[id] = object

        return id

    def remove_dynamic_object(self, id: int):
        self.dynamic_objects.pop(id)

    def update_dynamic_object(self, id: int, obj: DynamicObject):
        self.dynamic_objects[id] = obj

    def update_static_object(self, id: int, object: Object):
        self.static_objects[id] = object

    def __get_position_index(self, pos: Pos2D) -> int:
        return pos.x * self.map_width + pos.y

    def paint_object(self, map: list[int], obj: Object, type: MapType):
        for x in range(obj.pos.x, obj.pos.x + obj.width):
            for y in range(obj.pos.y, obj.pos.y + obj.height):
                map[self.__get_position_index(Pos2D(x, y))] = type.value

    def paint_map(self) -> list[int]:
        map = []
        for _ in range(self.map_width * self.map_height):
            map.append(MapType.EMPTY)

        for obj in self.static_objects.values():
            self.paint_object(map, obj, MapType.WALL)

        for obj in self.dynamic_objects.values():
            self.paint_object(map, obj, MapType.OBJECT)

        return map
