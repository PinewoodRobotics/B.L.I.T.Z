import numpy as np
from generated.proto.python.AprilTag_pb2 import AprilTags, RawAprilTagCorners
from render.world import World
from render.objects.apriltag import AprilTag
from .pipeline import Pipeline


class AprilTagPipeline(Pipeline):
    def __init__(self):
        self.world = World()

    def process(self, world: World, topic_pub_data: bytes):
        raw_tags = AprilTags.FromString(topic_pub_data)
        for tag in raw_tags.tags:
            if world.contains_object(f"tag_{tag.tag_id}"):
                tag_entity = world.get_object(f"tag_{tag.tag_id}").get_entity()
            else:
                tag_entity = AprilTag(tag.tag_id)
                world.add_object(f"tag_{tag.tag_id}", tag_entity)

            assert isinstance(tag_entity, AprilTag)
            tag_entity.set_position(
                (
                    tag.position_x_relative,
                    tag.position_y_relative,
                    tag.position_z_relative,
                )
            )
            tag_entity.set_rotation_matrix(np.array(tag.pose_R).reshape(3, 3))
            tag_entity.set_size(tag.tag_size)

    def get_topic(self) -> str:
        return "april_tag"
