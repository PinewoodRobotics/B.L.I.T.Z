import numpy as np
from numpy.typing import NDArray

from blitz.common.util.math import from_theat_to_3x3_mat
from blitz.generated.proto.python.sensor.apriltags_pb2 import (
    AprilTagData,
    ProcessedTag,
    WorldTags,
)
from blitz.generated.thrift.config.common.ttypes import GenericMatrix, GenericVector, Point3
from blitz.pos_extrapolator.data_prep import DataPreparer
from blitz.pos_extrapolator.position_extrapolator import PositionExtrapolator
from blitz.pos_extrapolator.preparers import AprilTagPreparer
from blitz.pos_extrapolator.preparers.AprilTagPreparer import (
    AprilTagConfig,
    AprilTagDataPreparer,
    AprilTagDataPreparerConfig,
)


def from_theta_to_rotation_state(theta: float) -> NDArray[np.float64]:
    return np.array([0, 0, 0, 0, np.cos(np.radians(theta)), np.sin(np.radians(theta))])


def from_np_to_point3(pose: NDArray[np.float64], rotation: NDArray[np.float64]) -> Point3:
    """
    Convert a pose and rotation from robot coordinates to camera coordinates.
    The pose is a 3D vector in robot coordinates.
    The rotation is a 3x3 matrix in robot coordinates.
    """

    # pose = from_robot_coords_to_camera_coords(pose)
    # rotation = from_robot_rotation_to_camera_rotation(rotation)

    return Point3(
        position=GenericVector(values=[pose[0], pose[1], pose[2]], size=3),
        rotation=GenericMatrix(
            values=[[rotation[0, 0], rotation[0, 1], rotation[0, 2]], [rotation[1, 0], rotation[1, 1], rotation[1, 2]], [rotation[2, 0], rotation[2, 1], rotation[2, 2]]],
            rows=3,
            cols=3,
        ),
    )


def from_robot_coords_to_camera_coords(vector: NDArray[np.float64]) -> NDArray[np.float64]:
    return PositionExtrapolator.CAMERA_OUTPUT_TO_ROBOT_ROTATION.T @ vector


def from_robot_rotation_to_camera_rotation(rotation: NDArray[np.float64]) -> NDArray[np.float64]:
    return (
        PositionExtrapolator.CAMERA_OUTPUT_TO_ROBOT_ROTATION.T
        @ rotation
        @ PositionExtrapolator.CAMERA_OUTPUT_TO_ROBOT_ROTATION
    )


def construct_tag_world(use_imu_rotation: bool = False) -> AprilTagConfig:
    tags_in_world: dict[int, Point3] = {}
    cameras_in_robot: dict[str, Point3] = {}

    tags_in_world[0] = from_np_to_point3(
        pose=np.array([0, 0, 0]),
        rotation=from_theat_to_3x3_mat(0),
    )

    tags_in_world[1] = from_np_to_point3(
        pose=np.array([1, 0, 0]),
        rotation=from_theat_to_3x3_mat(90),
    )

    tags_in_world[2] = from_np_to_point3(
        pose=np.array([0, 1, 0]),
        rotation=from_theat_to_3x3_mat(180),
    )

    tags_in_world[3] = from_np_to_point3(
        pose=np.array([1, 1, 0]),
        rotation=from_theat_to_3x3_mat(270),
    )

    tags_in_world[4] = from_np_to_point3(
        pose=np.array([0, 1, 0]),
        rotation=from_theat_to_3x3_mat(360),
    )

    cameras_in_robot["camera_1"] = from_np_to_point3(
        pose=np.array([0, 0, 0]),
        rotation=from_theat_to_3x3_mat(0),
    )

    return AprilTagConfig(
        tags_in_world=tags_in_world,
        cameras_in_robot=cameras_in_robot,
        use_imu_rotation=use_imu_rotation,
    )


def make_april_tag_preparer(
    use_imu_rotation: bool = False,
) -> DataPreparer[AprilTagData, AprilTagDataPreparerConfig]:
    return AprilTagDataPreparer( # pyright: ignore[reportReturnType]
        AprilTagDataPreparerConfig(construct_tag_world(use_imu_rotation))
    )  # type: ignore


def test_april_tag_prep_one():
    """
    Tests the AprilTagDataPreparer with a single tag.
    The tag is at 0, 0 in the world and the camera is expected to be in the -1, 0 position.
    """

    preparer = make_april_tag_preparer()

    tag_one_R = from_robot_rotation_to_camera_rotation(from_theat_to_3x3_mat(0))
    tag_one_t = from_robot_coords_to_camera_coords(np.array([1, 0, 0]))

    tag_vision_one = AprilTagData(
        world_tags=WorldTags(
            tags=[
                ProcessedTag(
                    id=0,
                    pose_R=tag_one_R.flatten().tolist(),
                    pose_t=tag_one_t.tolist(),
                )
            ]
        )
    )

    output = preparer.prepare_input(tag_vision_one, "camera_1")

    assert output.input_list.shape == (4,)
    assert output.input_list[0] == -1
    assert output.input_list[1] == 0


def test_april_tag_prep_two():
    preparer = make_april_tag_preparer(use_imu_rotation=True)

    tag_one_R = from_robot_rotation_to_camera_rotation(
        from_theat_to_3x3_mat(10)
    )  # noisy
    tag_one_t = from_robot_coords_to_camera_coords(np.array([1, 0, 0]))

    tag_vision_one = AprilTagData(
        world_tags=WorldTags(
            tags=[
                ProcessedTag(
                    id=0,
                    pose_R=tag_one_R.flatten().tolist(),
                    pose_t=tag_one_t.tolist(),
                )
            ]
        )
    )

    output = preparer.prepare_input(
        tag_vision_one, "camera_1", from_theta_to_rotation_state(0)
    )

    assert output.input_list.shape == (4,)
    assert output.input_list[0] == -1
    assert output.input_list[1] == 0
