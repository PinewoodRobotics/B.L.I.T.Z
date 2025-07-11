import os
from blitz.generated.thrift.config.camera.ttypes import CameraType
from blitz.generated.thrift.config.common.ttypes import Matrix3x3, Vector3D
from blitz.common.config import from_file, from_uncertainty_config, load_config
from blitz.common.util.math import get_np_from_matrix, get_np_from_vector


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def test_load_config():
    config = load_config()
    assert config is not None


def test_from_file():
    config = from_file(add_cur_dir("fixtures/sample_config.txt"))
    assert config is not None
    assert config.autobahn is not None
    assert config.autobahn.port == 8080
    assert config.cameras is not None
    assert len(config.cameras) == 1
    assert config.cameras[0].name == "one"
    assert config.cameras[0].camera_path == "/dev/video0"
    assert config.cameras[0].flags == 0
    assert config.cameras[0].width == 800
    assert config.cameras[0].height == 600
    assert config.cameras[0].camera_type == CameraType.OV2311
    assert config.cameras[0].camera_matrix is not None
    assert config.cameras[0].camera_matrix.r1.k1 is not None
    assert config.cameras[0].camera_matrix.r2.k1 is not None
    assert config.cameras[0].camera_matrix.r3.k1 is not None


def test_from_uncertainty_config():
    config = from_uncertainty_config(add_cur_dir("fixtures/sample_config.txt"))
    assert config is not None


def test_generate_config():
    config = from_uncertainty_config()
    assert config is not None


def test_get_np_from_vector():
    vector = Vector3D(k1=1, k2=2, k3=3)
    assert get_np_from_vector(vector) is not None
    assert get_np_from_vector(vector).shape == (3, 1)
    assert get_np_from_vector(vector).tolist() == [[1], [2], [3]]


def test_get_np_from_matrix():
    matrix = Matrix3x3(
        r1=Vector3D(k1=1, k2=2, k3=3),
        r2=Vector3D(k1=4, k2=5, k3=6),
        r3=Vector3D(k1=7, k2=8, k3=9),
    )

    assert get_np_from_matrix(matrix) is not None
    assert get_np_from_matrix(matrix).shape == (3, 3)
    assert get_np_from_matrix(matrix).tolist() == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
