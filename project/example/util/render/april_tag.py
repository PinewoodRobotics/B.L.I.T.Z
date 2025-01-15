import cv2
import numpy as np
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
from project.generated.project.common.proto.Inference_pb2 import InferenceList


def render_april_tag(image: np.ndarray, tag_detection: AprilTags) -> np.ndarray:
    for tag in tag_detection.tags:
        # Draw tag center
        center = (int(tag.center[0]), int(tag.center[1]))
        cv2.circle(image, center, 5, (0, 255, 0), -1)

        # Draw tag ID
        cv2.putText(
            image,
            f"ID: {tag.tag_id}",
            (center[0] + 10, center[1] + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            2,
        )

        # Draw corners and connect them
        corners = [
            (int(tag.corners[i]), int(tag.corners[i + 1]))
            for i in range(0, len(tag.corners), 2)
        ]
        for i in range(4):
            cv2.line(image, corners[i], corners[(i + 1) % 4], (0, 255, 0), 2)
            cv2.circle(image, corners[i], 3, (0, 0, 255), -1)

        # Optionally draw distance information
        if tag.distance_to_camera > 0:
            cv2.putText(
                image,
                f"{tag.distance_to_camera:.2f}m",
                (center[0] - 10, center[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

    return image
