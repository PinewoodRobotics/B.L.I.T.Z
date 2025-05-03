import time
import cv2
import numpy as np
from generated.proto.python.AprilTag_pb2 import AprilTags, RawAprilTagCorners
from generated.proto.python.Image_pb2 import ImageMessage
from project.example.position_debug.three_d.render.objects.image_object import (
    ImageObject,
)
from render.world import World
from render.objects.apriltag import AprilTag
from .pipeline import Pipeline
from ursina import Vec3


class AprilTagPipeline(Pipeline, topic="apriltag/camera"):
    def __init__(self):
        super().__init__()
        self.tags = []

    async def process(self, world: World, topic_pub_data: bytes):
        try:
            raw_image = ImageMessage.FromString(topic_pub_data)
            image = np.frombuffer(raw_image.image, dtype=np.uint8)
            image = image.reshape(raw_image.height, raw_image.width, 3)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            if not world.contains_object("image"):
                img_obj = ImageObject(image, scale=10)
                img_obj.rotation = Vec3(0, 0, 0)
                img_obj.position = Vec3(0, 1, 5)
                world.add_object("image", img_obj)
            else:
                entity = world.get_object("image").get_entity()
                assert isinstance(entity, ImageObject)
                entity.update_texture(image)
        except Exception as e:
            print(f"Error processing AprilTag message: {e}")
