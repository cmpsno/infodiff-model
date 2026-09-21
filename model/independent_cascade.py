"""
Independent Cascade (IC) model for information diffusion.

The IC model is the classic node-to-node contagion model used across network
science, epidemiology and marketing research (Kempe, Kleinberg & Tardos,
2003). It answers a simple question: if a rumor, product or belief starts
with a handful of people, how far does it spread through a social network,
and how fast?

Here it doubles as a learner model: run on a concept graph, each activation
is a mastered concept, and the cascade is an "aha" spreading from idea to idea.

Mechanics
---------
1. A set of "seed" nodes starts active at step 0.
2. At every following step, each node that became active in the *previous*
   step gets exactly one independent chance to activate each of its
   currently-inactive neighbors, with fixed probability `p`.
3. A node that succeeds becomes newly active this step. A node only ever
   gets one shot at activating a given neighbor - if it fails, it never
   tries again (though other newly-active neighbors of that node may still
   succeed on their own turn).
4. The process halts once a step produces no new activations.

This module is deliberately dependency-light (only networkx + random) so it
is easy to read, test, and swap out for Linear Threshold / SIR variants
later.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class CascadeResult:
    """The full step-by-step record of one Independent Cascade run."""

    seeds: list[int]
    p: float
    steps: list[list[int]] = field(default_factory=list)  # newly-activated node ids per step

    @property
    def activated_total(self) -> int:
        return sum(len(step) for step in self.steps)

    @property
    def cumulative_reach(self) -> list[int]:
        """Cumulative count of activated nodes after each step."""
        out, running = [], 0
        for step in self.steps:
            running += len(step)
            out.append(running)
        return out


def independent_cascade(graph, seeds: list[int], p: float, rng: random.Random) -> CascadeResult:
    """Run one Independent Cascade simulation on `graph`.

    Parameters
    ----------
    graph : networkx.Graph
        The social network the cascade spreads over.
    seeds : list[int]
        Node ids that start active (step 0).
    p : float
        Probability that an active node successfully activates a given
        inactive neighbor on its one turn.
    rng : random.Random
        A seeded RNG so runs are reproducible.

    Returns
    -------
    CascadeResult
        `steps[0]` is always the seed set. Every subsequent entry is the
        list of node ids that turned active on that step (may be empty-free;
        the list stops once nothing new activates).
    """
    graph_nodes = set(graph.nodes)
    unknown_seeds = set(seeds) - graph_nodes
    if unknown_seeds:
        raise ValueError(f"seed nodes are not in the graph: {sorted(unknown_seeds)}")
    if not 0 <= p <= 1:
        raise ValueError("p must be between 0 and 1")

    normalized_seeds = list(dict.fromkeys(seeds))
    active = set(normalized_seeds)
    frontier = list(normalized_seeds)
    result = CascadeResult(
        seeds=normalized_seeds, p=p, steps=[normalized_seeds]
    )

    while frontier:
        newly_active: list[int] = []
        for node in frontier:
            for neighbor in graph.neighbors(node):
                if neighbor in active or neighbor in newly_active:
                    continue
                if rng.random() < p:
                    newly_active.append(neighbor)
        if not newly_active:
            break
        active.update(newly_active)
        result.steps.append(newly_active)
        frontier = newly_active

    return result
