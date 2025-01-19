from typing import Callable
from project.common.config import Config
from project.common.config_class.filters.kalman_filter_config import MeasurementType
from project.generated.project.common.proto.AprilTag_pb2 import AprilTags
from project.generated.project.common.proto.RobotPosition_pb2 import RobotPosition
import numpy as np
import time

from project.recognition.position.pos_extrapolator.src.filter import FilterStrategy
from project.recognition.position.pos_extrapolator.src.filters.kalman import (
    KalmanFilterStrategy,
)
from project.recognition.position.pos_extrapolator.src.math_util import (
    get_rotation_matrix_deg,
    rotate_pitch_yaw,
    rotate_vector,
    translate_vector,
)
from project.recognition.position.pos_extrapolator.src.tag_pos_to_world import (
    TagPosToWorld,
)


class AprilTagSensorProcessor:
    def __init__(
        self,
        cameras_to_analyze: list[str],
        config,
        tag_pos_to_world: TagPosToWorld,
        filter_strategy: FilterStrategy,
        only_tags=False,
        get_estimated_position: Callable[[], list[float]] | None = None,
    ):
        self.only_tags = only_tags
        self.previous_positions: list[tuple[float, float]] = []
        self.current_positions: dict[str, list[RobotPosition]] = {}
        self.cameras_used: list[str] = []
        self.cameras_to_analyze = cameras_to_analyze
        self.config: Config = config
        self.tag_pos_to_world: TagPosToWorld = tag_pos_to_world
        self.filter_strategy = filter_strategy
        self.get_estimated_position = get_estimated_position
        self.last_position = None
        self.last_timestamp = None

    def on_message(
        self,
        message: AprilTags,
    ):
        camera_config = self.config.camera_parameters.camera_parameters[
            message.camera_name
        ]

        # Add camera to used cameras list if not already present
        if message.camera_name not in self.cameras_used:
            self.cameras_used.append(message.camera_name)

        rotation_matrix = get_rotation_matrix_deg(
            camera_config.rotation_vector[0], camera_config.rotation_vector[1]
        )
        translation_vector = np.array(camera_config.translation_vector)

        tmp: list[RobotPosition] = []
        for tag in message.tags:
            tag_vector = np.array(
                [
                    tag.position_x_relative,
                    tag.position_y_relative,
                    tag.position_z_relative,
                ]
            )
            print(tag_vector)

            rotated_tag_vector = rotate_vector(tag_vector, rotation_matrix)
            translated_tag_vector = translate_vector(
                rotated_tag_vector, translation_vector
            )

            tag.angle_relative_to_camera_pitch, tag.angle_relative_to_camera_yaw = (
                rotate_pitch_yaw(
                    tag.angle_relative_to_camera_pitch,
                    tag.angle_relative_to_camera_yaw,
                    camera_config.rotation_vector[0],
                    camera_config.rotation_vector[1],
                )
            )

            world_pos = self.tag_pos_to_world.get_world_pos(
                (
                    translated_tag_vector[0],
                    translated_tag_vector[1],
                    translated_tag_vector[2],
                )
            )

            tmp.append(
                RobotPosition(
                    camera_name=message.camera_name,
                    timestamp=int(time.time()),
                    confidence=0.0,
                    estimated_position=(world_pos[0], world_pos[1], 0),
                    estimated_rotation=[
                        tag.angle_relative_to_camera_pitch,
                        tag.angle_relative_to_camera_yaw,
                    ],
                )
            )

        if message.camera_name not in self.current_positions:
            self.current_positions[message.camera_name] = tmp
        else:
            self.current_positions[message.camera_name].extend(tmp)

    def is_all_cameras_available(self):
        return all(camera in self.cameras_used for camera in self.cameras_to_analyze)

    def _get_current_estimated_velocity(self):
        vx, vy = 0, 0
        if len(self.previous_positions) >= 2 and self.only_tags is True:
            current = self.previous_positions[-1]
            previous = self.previous_positions[-2]

            vx = current[0] - previous[0]
            vy = current[1] - previous[1]

        return vx, vy

    def _calculate_velocity(self, current_pos, current_time):
        if self.last_position is None or self.last_timestamp is None:
            self.last_position = current_pos
            self.last_timestamp = current_time
            return 0, 0

        dt = (current_time - self.last_timestamp) / 1000.0  # Convert to seconds
        if dt == 0:
            return 0, 0

        vx = (current_pos[0] - self.last_position[0]) / dt
        vy = (current_pos[1] - self.last_position[1]) / dt

        # Update last position and timestamp
        self.last_position = current_pos
        self.last_timestamp = current_time

        # Apply simple smoothing to avoid extreme velocities
        max_velocity = 5.0  # meters per second
        vx = max(min(vx, max_velocity), -max_velocity)
        vy = max(min(vy, max_velocity), -max_velocity)

        return vx, vy

    def dump_data(self):
        current_time = int(time.time() * 1000)  # Get current time in milliseconds

        for camera in self.cameras_to_analyze:
            if camera not in self.current_positions:
                continue

            for position in self.current_positions[camera]:
                current_pos = (
                    position.estimated_position[0],
                    position.estimated_position[1],
                )

                # Calculate velocities based on position change
                vx, vy = self._calculate_velocity(current_pos, current_time)

                self.filter_strategy.filter_data(
                    [
                        position.estimated_position[0],
                        position.estimated_position[1],
                        vx,  # calculated vx
                        vy,  # calculated vy
                        position.estimated_rotation[0],  # rotation
                    ],
                    data_type=MeasurementType.APRIL_TAG,
                )

        if self.get_estimated_position is not None and self.only_tags is True:
            position = self.get_estimated_position()
            self.previous_positions.append((position[0], position[1]))
            if len(self.previous_positions) > 2:
                self.previous_positions.pop(0)
