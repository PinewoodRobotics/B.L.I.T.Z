from typing import Any
from render.world import World


class Pipeline:
    async def process(self, world: World, topic_pub_data: bytes):
        raise NotImplementedError

    def get_topic(self) -> str:
        raise NotImplementedError
