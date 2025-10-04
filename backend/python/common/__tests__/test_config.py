import os
from backend.generated.thrift.config.camera.ttypes import CameraType
from backend.python.common.config import from_file, from_uncertainty_config, load_config
from backend.python.common.util.math import get_np_from_matrix, get_np_from_vector
from backend.generated.thrift.config.common.ttypes import GenericMatrix, GenericVector


def add_cur_dir(path: str):
    return os.path.join(os.path.dirname(__file__), path)


def test_load_config():
    config = load_config()
    assert config is not None


def test_from_file():
    config = from_file(add_cur_dir("fixtures/sample_config.txt"))
    assert config is not None


def test_from_uncertainty_config():
    config = from_uncertainty_config(add_cur_dir("fixtures/sample_config.txt"))
    assert config is not None


def test_generate_config():
    config = from_uncertainty_config()
    assert config is not None


def test_get_np_from_vector():
    vector = GenericVector(values=[1, 2, 3], size=3)
    assert get_np_from_vector(vector) is not None
    assert get_np_from_vector(vector).shape == (3,)
    assert get_np_from_vector(vector).tolist() == [1, 2, 3]


def test_get_np_from_matrix():
    matrix = GenericMatrix(
        values=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        rows=3,
        cols=3,
    )

    assert get_np_from_matrix(matrix) is not None
    assert get_np_from_matrix(matrix).shape == (3, 3)
    assert get_np_from_matrix(matrix).tolist() == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
