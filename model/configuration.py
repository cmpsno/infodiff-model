"""Configuration primitives shared by single and batch simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _coerce_node_id(node: Any) -> Any:
    """Keep integer-like config keys as ints; leave labels like "M1" as strings."""
    try:
        return int(node)
    except (TypeError, ValueError):
        return str(node)


@dataclass
class SimulationConfig:
    """Serializable experiment configuration.

    ``threshold_distribution`` accepts ``uniform``, ``normal`` or ``custom``.
    Custom distributions use the node-to-threshold mapping in ``thresholds``.
    """

    graph: str = "fourier"
    models: list[str] = field(
        default_factory=lambda: ["independent_cascade", "linear_threshold"]
    )
    probabilities: list[float] = field(default_factory=lambda: [0.2])
    threshold_distribution: str = "uniform"
    threshold_parameters: dict[str, float] = field(
        default_factory=lambda: {"low": 0.1, "high": 0.5}
    )
    thresholds: dict[Any, float] | None = None
    seed_strategies: list[dict[str, Any]] = field(default_factory=list)
    runs: int = 1
    random_seed: int = 42
    graph_options: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "SimulationConfig":
        allowed = set(cls.__dataclass_fields__)
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"unknown configuration keys: {sorted(unknown)}")
        values = dict(values)
        if values.get("thresholds") is not None:
            values["thresholds"] = {
                _coerce_node_id(node): float(value)
                for node, value in values["thresholds"].items()
            }
        return cls(**values)

    def validate(self) -> None:
        if not self.models or not set(self.models) <= {
            "independent_cascade", "linear_threshold"
        }:
            raise ValueError("models must contain independent_cascade and/or linear_threshold")
        if not self.probabilities or any(not 0 <= p <= 1 for p in self.probabilities):
            raise ValueError("probabilities must contain values between 0 and 1")
        if self.threshold_distribution not in {"uniform", "normal", "custom"}:
            raise ValueError("threshold_distribution must be uniform, normal, or custom")
        if self.threshold_distribution == "custom" and self.thresholds is None:
            raise ValueError("custom threshold distribution requires thresholds")
        if self.runs < 1:
            raise ValueError("runs must be at least 1")

