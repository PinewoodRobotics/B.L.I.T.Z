import argparse
import json
import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
from pydantic import BaseModel, Field

from project.common.camera.transform import unfisheye_image
from util import get_detector
from project.common.util.math import (
    make_transformation_matrix,
    get_translation_rotation_components,
)


class Vec3(BaseModel):
    x: float
    y: float
    z: float


class Position3D(BaseModel):
    position: Vec3
    direction_vector: Vec3


class CameraConfig(BaseModel):
    camera_matrix: list[list] = Field(default_factory=list[list])
    dist_coeff: list = Field(default_factory=list)


class Config(BaseModel):
    camera_params: CameraConfig = Field(default_factory=CameraConfig)
    world_pos: Position3D
    tag_size_m: float


def plot_top_down_view(tag_positions):
    """Plots a top-down view of detected AprilTags and their orientations."""
    plt.clf()
    plt.xlim(-5, 5)
    plt.ylim(-5, 5)
    plt.xlabel("X Position (m)")
    plt.ylabel("Z Position (m)")
    plt.title("Top-Down View of Detected Tags")

    for tag_id, pos in tag_positions.items():
        x, _, z = pos.position.x, pos.position.y, pos.position.z
        dx, _, dz = (
            pos.direction_vector.x,
            pos.direction_vector.y,
            pos.direction_vector.z,
        )

        plt.scatter(x, z, color="blue", label=f"Tag {tag_id}")
        plt.arrow(x, z, dx, dz, head_width=0.1, head_length=0.1, fc="red", ec="red")

    plt.pause(10)


def main():
    tag_id_estimated_position_map: dict[int, list[Position3D]] = {}
    parser = argparse.ArgumentParser(
        description="Load camera calibration config from JSON file"
    )
    parser.add_argument(
        "--config_file", help="Path to JSON config file", default="camera_config.json"
    )
    parser.add_argument(
        "--images_folder", help="Path to the file with the images", default="images"
    )
    args = parser.parse_args()

    with open(args.config_file) as f:
        config = Config.model_validate_json(f.read())

    camera_matrix = np.array(config.camera_params.camera_matrix, dtype=np.float32)
    dist_coeffs = np.array(config.camera_params.dist_coeff, dtype=np.float32)

    camera_in_world = make_transformation_matrix(
        np.array(
            [
                config.world_pos.position.x,
                config.world_pos.position.y,
                config.world_pos.position.z,
            ]
        ),
        np.array(
            [
                config.world_pos.direction_vector.x,
                config.world_pos.direction_vector.y,
                config.world_pos.direction_vector.z,
            ]
        ),
    )
    world_in_camera = np.linalg.inv(camera_in_world)

    detector = get_detector()
    plt.ion()

    for image_file in os.listdir(args.images_folder):
        if not image_file.endswith((".jpg", ".jpeg", ".png")):
            continue

        image_path = os.path.join(args.images_folder, image_file)
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        if image is None:
            print(f"Could not read image {image_file}")
            continue

        unfisheyed_image, new_mtrx = unfisheye_image(image, camera_matrix, dist_coeffs)

        # Compute new camera intrinsics
        fx, fy, cx, cy = new_mtrx[0, 0], new_mtrx[1, 1], new_mtrx[0, 2], new_mtrx[1, 2]

        tags = detector.detect(
            unfisheyed_image,
            estimate_tag_pose=True,
            camera_params=(fx, fy, cx, cy),
            tag_size=config.tag_size_m,
        )

        if len(tags) == 0:
            print("No Tags Detected!")
            continue

        for tag in tags:
            if tag.pose_R is None or tag.pose_t is None:
                print("Was not able to detect rotation / position!")
                continue

            if tag.tag_id not in tag_id_estimated_position_map:
                tag_id_estimated_position_map[tag.tag_id] = []

            tag_in_camera = make_transformation_matrix(
                np.array([tag.pose_t[0][0], tag.pose_t[1][0], tag.pose_t[2][0]]),
                np.array([tag.pose_R[2][0], tag.pose_R[2][1], tag.pose_R[2][2]]),
            )
            camera_in_tag = np.linalg.inv(tag_in_camera)
            position_rotation_transformation = world_in_camera @ camera_in_tag
            translation, rotation = get_translation_rotation_components(
                position_rotation_transformation
            )

            tag_id_estimated_position_map[tag.tag_id].append(
                Position3D(
                    position=Vec3(x=translation[0], y=translation[1], z=translation[2]),
                    direction_vector=Vec3(
                        x=rotation[2][0], y=rotation[2][1], z=rotation[2][2]
                    ),
                )
            )

    # Compute average positions
    final_out_map = {}
    for pos in tag_id_estimated_position_map.keys():
        positions = tag_id_estimated_position_map[pos]
        avg_pos = Position3D(
            position=Vec3(
                x=sum(p.position.x for p in positions) / len(positions),
                y=sum(p.position.y for p in positions) / len(positions),
                z=sum(p.position.z for p in positions) / len(positions),
            ),
            direction_vector=Vec3(
                x=-sum(p.direction_vector.x for p in positions) / len(positions),
                y=sum(p.direction_vector.y for p in positions) / len(positions),
                z=sum(p.direction_vector.z for p in positions) / len(positions),
            ),
        )
        final_out_map[pos] = avg_pos

    # Render top-down view
    plot_top_down_view(final_out_map)

    for pos, avg_position in final_out_map.items():
        print(
            json.dumps(
                {
                    pos: {
                        "x": avg_position.position.x,
                        "y": avg_position.position.y,
                        "z": avg_position.position.z,
                        "direction_vector": [
                            avg_position.direction_vector.x,
                            avg_position.direction_vector.y,
                            avg_position.direction_vector.z,
                        ],
                    }
                }
            )
        )
        print(",")


if __name__ == "__main__":
    config = main()
