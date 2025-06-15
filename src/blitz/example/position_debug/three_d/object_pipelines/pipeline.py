from typing import Any, Dict, Type
from render.world import World


class Pipeline:
    _registry: Dict[str, Type["Pipeline"]] = {}

    def __init_subclass__(cls, topic: str, **kwargs):
        super().__init_subclass__(**kwargs)
        if topic is not None:
            Pipeline._registry[topic] = cls

    @classmethod
    def get_registry(cls) -> Dict[str, Type["Pipeline"]]:
        return cls._registry

    async def process(self, world: World, topic_pub_data: bytes):
        raise NotImplementedError

    def tick(self, world: World):
        pass
