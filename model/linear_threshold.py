"""Linear Threshold (LT) model for information diffusion.

Unlike Independent Cascade, which gives newly active nodes one probabilistic
chance to convince each neighbor, Linear Threshold treats adoption as social
reinforcement. Every inactive node has a threshold between 0 and 1. It becomes
active once the share of its neighbors that are already active meets or exceeds
that threshold.

The implementation uses equal influence weights: each neighbor contributes
``1 / degree(node)`` to a node's total influence. Thresholds are supplied by
the caller so experiments remain explicit and reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ThresholdResult:
    """The full step-by-step record of one Linear Threshold run."""

    seeds: list[int]
    thresholds: dict[int, float]
    steps: list[list[int]] = field(default_factory=list)

    @property
    def activated_total(self) -> int:
        return sum(len(step) for step in self.steps)

    @property
    def cumulative_reach(self) -> list[int]:
        """Cumulative count of activated nodes after each step."""
        out: list[int] = []
        running = 0
        for step in self.steps:
            running += len(step)
            out.append(running)
        return out


def linear_threshold(
    graph, seeds: list[int], thresholds: dict[int, float]
) -> ThresholdResult:
    """Run one synchronous Linear Threshold simulation on ``graph``.

    At each round, every inactive node observes the active set from the end of
    the previous round. A node activates when ``active_neighbors / degree`` is
    at least its threshold. Activations are permanent, and the process stops
    when a round produces no new activations.

    Isolated nodes cannot be activated by influence, but may still be seeds.
    """
    graph_nodes = set(graph.nodes)
    unknown_seeds = set(seeds) - graph_nodes
    if unknown_seeds:
        raise ValueError(f"seed nodes are not in the graph: {sorted(unknown_seeds)}")

    missing_thresholds = graph_nodes - set(thresholds)
    if missing_thresholds:
        raise ValueError(
            f"thresholds are missing for nodes: {sorted(missing_thresholds)}"
        )

    invalid_thresholds = {
        node: value
        for node, value in thresholds.items()
        if node in graph_nodes and not 0 <= value <= 1
    }
    if invalid_thresholds:
        raise ValueError(f"thresholds must be between 0 and 1: {invalid_thresholds}")

    normalized_seeds = list(dict.fromkeys(seeds))
    active = set(normalized_seeds)
    result = ThresholdResult(
        seeds=normalized_seeds,
        thresholds={node: thresholds[node] for node in sorted(graph_nodes)},
        steps=[normalized_seeds],
    )

    while True:
        newly_active: list[int] = []
        for node in sorted(graph_nodes - active):
            degree = graph.degree[node]
            if degree == 0:
                continue
            active_neighbors = sum(neighbor in active for neighbor in graph.neighbors(node))
            if active_neighbors / degree >= thresholds[node]:
                newly_active.append(node)

        if not newly_active:
            break
        active.update(newly_active)
        result.steps.append(newly_active)

    return result
