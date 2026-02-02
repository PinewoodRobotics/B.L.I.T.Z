from typing import TYPE_CHECKING
from backend.deployment.util import _WeightedProcess

if TYPE_CHECKING:
    from backend.deployment.util import _Module


class ProcessType(_WeightedProcess):
    pass


def pi_name_to_process_types(pi_names: list[str]) -> dict[str, list[ProcessType]]:
    return {}


def get_modules() -> list["_Module"]:
    return []
