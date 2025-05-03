import time
import numpy as np
from generated.proto.python.AprilTag_pb2 import AprilTags, RawAprilTagCorners
from render.world import World
from render.objects.apriltag import AprilTag
from .pipeline import Pipeline


class AprilTagPipeline(Pipeline, topic="apriltag/tag"):
    def __init__(self):
        super().__init__()
        self.tags = []

    async def process(self, world: World, topic_pub_data: bytes):
        try:
            raw_tags = AprilTags.FromString(topic_pub_data)
            for tag in raw_tags.tags:
                if tag.tag_id not in self.tags:
                    self.tags.append(tag.tag_id)

                if world.contains_object(f"tag_{tag.tag_id}"):
                    tag_entity = world.get_object(f"tag_{tag.tag_id}").get_entity()
                else:
                    tag_entity = AprilTag(tag.tag_id)
                    world.add_object(f"tag_{tag.tag_id}", tag_entity)

                assert isinstance(tag_entity, AprilTag)
                tag_entity.set_position((tag.pose_t[0], tag.pose_t[1], tag.pose_t[2]))
                tag_entity.set_rotation_matrix(np.array(tag.pose_R).reshape(3, 3))
        except Exception as e:
            print(f"Error processing AprilTag message: {e}")

    def tick(self, world: World):
        tags_to_remove = []
        for tag_id in self.tags:
            if world.contains_object(f"tag_{tag_id}"):
                tag_entity = world.get_object(f"tag_{tag_id}")
                if time.time() - tag_entity.get_last_update() > 2:
                    world.remove_object(f"tag_{tag_id}")
            else:
                tags_to_remove.append(tag_id)

        for tag_id in tags_to_remove:
            self.tags.remove(tag_id)
