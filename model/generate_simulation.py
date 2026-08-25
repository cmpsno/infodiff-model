"""Generate reproducible diffusion runs for the static playback site.

Builds Zachary's Karate Club network, runs both Independent Cascade and
Linear Threshold scenarios, and writes a single JSON file that the GitHub
Pages front end (docs/) plays back frame by frame.

Run with:
    python3 model/generate_simulation.py

Regenerating is deterministic: every scenario is driven by a fixed
random.Random(seed), so re-running this script always produces the same
data/simulation.json / docs/simulation.json.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import networkx as nx

from independent_cascade import independent_cascade
from linear_threshold import linear_threshold

P = 0.2  # probability an active node "convinces" a given inactive neighbor
THRESHOLD_MIN = 0.1
THRESHOLD_MAX = 0.5
THRESHOLD_SEED = 152  # one stable set of node traits shared by every LT scenario

# (key, display name, seed node ids, IC rng seed, one-line story)
SEEDING_SCENARIOS = [
    (
        "hub",
        "Start at the hub (Officer, node 33)",
        [33],
        2,
        "The rumor starts with the single most-connected member of the club.",
    ),
    (
        "leader_hi",
        "Start with the instructor (Mr. Hi, node 0)",
        [0],
        1,
        "Same idea, seeded from the rival hub on the other side of the eventual split.",
    ),
    (
        "peripheral",
        "Start at the edge (node 11, 1 connection)",
        [11],
        14,
        "Seeded from the network's only degree-1 member — most cascades stall almost immediately.",
    ),
    (
        "dual",
        "Start in both factions at once (nodes 0 and 33)",
        [0, 33],
        5,
        "Both future factions hear the rumor independently on the same day.",
    ),
]


def build_graph_payload(graph: nx.Graph) -> dict:
    nodes = []
    for n in sorted(graph.nodes):
        club = graph.nodes[n]["club"]  # 'Mr. Hi' or 'Officer' — the real 1977 factions
        nodes.append(
            {
                "id": n,
                "faction": "Hi" if club == "Mr. Hi" else "Officer",
                "degree": graph.degree[n],
            }
        )
    links = [{"source": u, "target": v} for u, v in graph.edges]
    return {"nodes": nodes, "links": links}


def sample_thresholds(graph: nx.Graph, seed: int) -> dict[int, float]:
    """Sample one deterministic threshold per node for an LT scenario."""
    rng = random.Random(seed)
    return {
        node: rng.uniform(THRESHOLD_MIN, THRESHOLD_MAX)
        for node in sorted(graph.nodes)
    }


def build_scenarios_payload(graph: nx.Graph) -> dict:
    payload: dict[str, dict] = {}

    for key, name, seeds, ic_seed, story in SEEDING_SCENARIOS:
        result = independent_cascade(graph, seeds, P, random.Random(ic_seed))
        payload[key] = {
            "model": "independent_cascade",
            "name": name,
            "story": story,
            "seeds": seeds,
            "parameters": {"activation_probability": P, "random_seed": ic_seed},
            "steps": result.steps,
            "cumulative_reach": result.cumulative_reach,
            "total_reached": result.activated_total,
            "total_nodes": graph.number_of_nodes(),
        }

    thresholds = sample_thresholds(graph, THRESHOLD_SEED)
    for key, name, seeds, _ic_seed, story in SEEDING_SCENARIOS:
        result = linear_threshold(graph, seeds, thresholds)
        payload[f"lt_{key}"] = {
            "model": "linear_threshold",
            "name": name,
            "story": story,
            "seeds": seeds,
            "parameters": {
                "influence": "active_neighbor_fraction",
                "threshold_range": [THRESHOLD_MIN, THRESHOLD_MAX],
                "threshold_seed": THRESHOLD_SEED,
            },
            "steps": result.steps,
            "cumulative_reach": result.cumulative_reach,
            "total_reached": result.activated_total,
            "total_nodes": graph.number_of_nodes(),
        }
    return payload


def main() -> None:
    graph = nx.karate_club_graph()

    output = {
        "model": "multiple",
        "models": {
            "independent_cascade": {
                "name": "Independent Cascade",
                "short_name": "IC",
                "parameter": f"p = {P}",
                "description": (
                    "Each newly active person gets one independent chance to "
                    "activate each inactive neighbor. Failed attempts are not retried."
                ),
            },
            "linear_threshold": {
                "name": "Linear Threshold",
                "short_name": "LT",
                "parameter": f"thresholds {THRESHOLD_MIN}–{THRESHOLD_MAX}",
                "description": (
                    "A person adopts once the share of their active neighbors meets "
                    "their individual threshold, turning repeated social reinforcement "
                    "into diffusion."
                ),
            },
        },
        "graph": build_graph_payload(graph),
        "scenarios": build_scenarios_payload(graph),
    }

    repo_root = Path(__file__).resolve().parent.parent
    targets = [repo_root / "data" / "simulation.json", repo_root / "docs" / "simulation.json"]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, indent=2))
        print(f"wrote {target}")


if __name__ == "__main__":
    main()
