from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.deployment.util import _Module


def get_modules() -> list["_Module"]:
    return []
