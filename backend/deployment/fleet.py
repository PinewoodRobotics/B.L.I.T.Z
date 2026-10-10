"""Optional fleet expectations, independent of device names and addresses."""
from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from backend.deployment.compilation.util.systems import SystemId
from backend.deployment.module.contracts import TargetRequirements


class FleetValidationError(ValueError):
    """The live fleet does not meet the project's deployment expectations."""


@dataclass(frozen=True)
class ExpectedSystemType:
    """Require a number of distinct devices matching a deployment profile."""

    name: str
    count: int
    targets: TargetRequirements

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Expected system type needs a nonempty name")
        if type(self.count) is not int or self.count < 1:
            raise ValueError("Expected system type count must be a positive integer")
        if not isinstance(self.targets, TargetRequirements):
            raise ValueError("Expected system type targets must be TargetRequirements")


def validate_fleet_configuration(
    expected_count: int | None, expected_types: Sequence[ExpectedSystemType],
) -> int | None:
    """Return the exact count, deriving it from types when count is omitted."""
    if expected_count is not None and (type(expected_count) is not int or expected_count < 1):
        raise ValueError("Expected system count must be a positive integer or None")
    if not all(isinstance(profile, ExpectedSystemType) for profile in expected_types):
        raise ValueError("Expected system types must be ExpectedSystemType values")
    names = [profile.name for profile in expected_types]
    if len(set(names)) != len(names):
        raise ValueError("Expected system type names must be unique")
    required = sum(profile.count for profile in expected_types)
    if expected_count is not None and required > expected_count:
        raise ValueError(f"Expected system types require {required} distinct devices, exceeding expected count {expected_count}")
    return expected_count if expected_count is not None else (required or None)


def validate_fleet_count(
    actual_count: int, expected_count: int | None, expected_types: Sequence[ExpectedSystemType],
) -> None:
    count = validate_fleet_configuration(expected_count, expected_types)
    if count is not None and actual_count != count:
        raise FleetValidationError(
            f"Fleet count mismatch: expected exactly {count} devices after exclusions, "
            f"found {actual_count}. No deployment will proceed."
        )


def validate_fleet_profiles(
    systems: Sequence[SystemId], expected_types: Sequence[ExpectedSystemType],
) -> None:
    """Find distinct matches even when profile requirements overlap.

    Iterative augmenting paths avoid both greedy misassignment and recursion
    limits. Matching never changes the selected destinations or process plan.
    """
    candidates = [
        [index for index, system in enumerate(systems) if not profile.targets.incompatibilities(system)]
        for profile in expected_types
    ]
    slot_types = [index for index, profile in enumerate(expected_types) for _ in range(profile.count)]
    device_slots: dict[int, int] = {}
    slot_devices: dict[int, int] = {}
    for root in sorted(range(len(slot_types)), key=lambda slot: len(candidates[slot_types[slot]])):
        queue = deque([root])
        visited_slots = {root}
        device_parents: dict[int, int] = {}
        found = False
        while queue and not found:
            slot = queue.popleft()
            for device in candidates[slot_types[slot]]:
                if device in device_parents:
                    continue
                device_parents[device] = slot
                owner = device_slots.get(device)
                if owner is None:
                    while True:
                        parent = device_parents[device]
                        previous = slot_devices.get(parent)
                        slot_devices[parent] = device
                        device_slots[device] = parent
                        if previous is None:
                            break
                        device = previous
                    found = True
                    break
                if owner not in visited_slots:
                    visited_slots.add(owner)
                    queue.append(owner)
    if len(slot_devices) != len(slot_types):
        details = []
        for index, profile in enumerate(expected_types):
            matched = sum(slot_types[slot] == index for slot in slot_devices)
            details.append(f"{profile.name}: {matched}/{profile.count} matched ({len(candidates[index])} compatible)")
        raise FleetValidationError(
            "Fleet profile mismatch: expected distinct devices for each required slot; "
            + "; ".join(details) + ". No deployment will proceed."
        )
