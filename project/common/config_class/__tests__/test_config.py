from project.common.config import from_file, from_uncertainty_config, load_config
from project.common.util.tests_util import add_cur_dir


def test_load_config():
    config = load_config()
    assert config is not None


def test_from_file():
    config = from_file(add_cur_dir("fixtures/sample_config.json"))
    assert config is not None


def test_from_uncertainty_config():
    config = from_uncertainty_config(add_cur_dir("fixtures/sample_config.json"))
    assert config is not None
