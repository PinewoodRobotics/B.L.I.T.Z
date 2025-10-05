from backend.python.common.util.system import get_local_hostname


def test_get_local_hostname():
    assert get_local_hostname() == "Deniss-MacBook-Pro.local"
