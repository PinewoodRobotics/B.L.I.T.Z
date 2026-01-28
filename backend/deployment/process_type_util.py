from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, Iterable, TypeVar

from backend.deployment.util import _WeightedProcess

TProcess = TypeVar("TProcess", bound=_WeightedProcess)


@dataclass(frozen=True, slots=True)
class ConstrainedProcess(Generic[TProcess]):
    """
    Constrains N instances of a process type to a specific Pi name.

    This mirrors the Java idea of "ConstrainedProcess(ProcessType.X, hostName)".
    Use `count` when you want multiple instances of the same type pinned to a host.
    """

    process: TProcess
    pi_name: str
    count: int = 1


@dataclass(slots=True)
class ProcessPlan(Generic[TProcess]):
    """
    A declarative, Java-like way to describe desired processes and constraints.

    Example:
      plan = (
        ProcessPlan[ProcessType]()
          .add(ProcessType.POS_EXTRAPOLATOR)
          .add(ProcessType.APRIL_SERVER, count=3)
          .pin(ProcessType.APRIL_SERVER, "nathan-hale")
      )
      mapping = plan.assign(pi_names)
    """

    desired: list[TProcess] = field(default_factory=list)
    constraints: list[ConstrainedProcess[TProcess]] = field(default_factory=list)

    def add(self, process: TProcess, *, count: int = 1) -> "ProcessPlan[TProcess]":
        if count <= 0:
            return self
        self.desired.extend([process] * count)
        return self

    def pin(
        self, process: TProcess, pi_name: str, *, count: int = 1
    ) -> "ProcessPlan[TProcess]":
        """
        Adds `process` to the desired set AND constrains those instance(s) to a host.

        This is intentionally unambiguous: calling `.pin(...)` means you are
        creating desired work, not just setting a constraint.
        """

        if count <= 0:
            return self
        self.desired.extend([process] * count)
        self.constraints.append(
            ConstrainedProcess(process=process, pi_name=pi_name, count=count)
        )
        return self

    def assign(self, pi_names: Iterable[str]) -> dict[str, list[TProcess]]:
        return assign_weighted_processes_to_pis(
            pi_names=pi_names, processes=self.desired, constrained=self.constraints
        )


def normalize_pi_name(name: str) -> str:
    """
    Normalizes typical zeroconf/hostname values into a stable Pi name key.

    Examples:
    - "pi1.local" -> "pi1"
    - "PI1" -> "pi1"
    - "pi1.local." -> "pi1"
    """

    n = (name or "").strip().lower().rstrip(".")
    if n.endswith(".local"):
        n = n[: -len(".local")]
    return n


def assign_weighted_processes_to_pis(
    *,
    pi_names: Iterable[str],
    processes: Iterable[TProcess],
    constrained: Iterable[ConstrainedProcess[TProcess]] = (),
) -> dict[str, list[TProcess]]:
    """
    Distributes weighted processes across Pis to balance total assigned weight.

    Strategy:
    - Apply constrained assignments first.
    - Then greedily assign remaining processes (heaviest-first) to the Pi with
      the lowest current total weight.
    """

    normalized_pi_names = [normalize_pi_name(p) for p in pi_names]
    if not normalized_pi_names:
        return {}
    out: dict[str, list[TProcess]] = {p: [] for p in normalized_pi_names}
    weights: dict[str, float] = {p: 0.0 for p in normalized_pi_names}

    remaining: list[TProcess] = [p for p in processes]

    # Apply constraints first.
    for c in constrained:
        pi = normalize_pi_name(c.pi_name)
        if pi not in out:
            # Pi not present; ignore the constraint rather than failing deploy.
            continue

        removed = 0
        for _ in range(max(0, int(c.count))):
            try:
                remaining.remove(c.process)
                removed += 1
            except ValueError:
                break

        if removed <= 0:
            continue

        out[pi].extend([c.process] * removed)
        weights[pi] += float(c.process.get_weight()) * removed

    # Greedy pack remaining by descending weight.
    remaining.sort(key=lambda p: float(p.get_weight()), reverse=True)
    for p in remaining:
        target_pi = min(weights.keys(), key=lambda k: (weights[k], k))
        out[target_pi].append(p)
        weights[target_pi] += float(p.get_weight())

    return out
