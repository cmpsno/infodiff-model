"""Generate configurable, reproducible diffusion data for the static site."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path
import networkx as nx
from configuration import SimulationConfig
from graph_io import load_graph, normalize_node_ids
from independent_cascade import independent_cascade
from linear_threshold import linear_threshold

P = 0.2
THRESHOLD_MIN, THRESHOLD_MAX, THRESHOLD_SEED = 0.1, 0.5, 152
# Node ids on the fourier concept graph: 0 frequency, 1 amplitude, 2 phase,
# 3 superposition, 4 spectrum, 5 M1, 6 M2, 7 M3, 8 M4.
# Core concepts are easier to master (0.3); misconceptions only resolve once
# most of their prerequisites are mastered (0.55).
FOURIER_THRESHOLDS = {0: 0.3, 1: 0.3, 2: 0.3, 3: 0.3, 4: 0.3, 5: 0.55, 6: 0.55, 7: 0.55, 8: 0.55}
SEEDING_SCENARIOS = [
 ("frequency_first", "Frequency clicks first", [0], 2, "The learner finally gets frequency. Phase and spectrum follow, then superposition — the misconceptions fall one by one, M1 last: it needs both frequency and amplitude."),
 ("superposition_clicks", "Superposition clicks", [3], 1, "Superposition pulls in amplitude and spectrum, then frequency — the misconceptions resolve in a burst, M3 last: it waits on phase."),
 ("misconception_first", "Confront M1 head-on", [5], 14, "Attacking M1 ('faster = taller') directly teaches amplitude — then stalls. One misconception can't seed a curriculum."),
 ("core_pair", "Frequency + amplitude together", [0, 1], 5, "Two core concepts at once: M1 resolves on the first step and the rest of the graph follows in two more."),
]

def default_config():
    return SimulationConfig(graph="fourier", random_seed=THRESHOLD_SEED, threshold_distribution="custom",
                            thresholds=dict(FOURIER_THRESHOLDS), seed_strategies=[
        {"key": k, "name": n, "seeds": s, "random_seed": r, "story": story}
        for k, n, s, r, story in SEEDING_SCENARIOS])

def build_graph_payload(graph):
    nodes = []
    for node in sorted(graph.nodes):
        attrs = graph.nodes[node]
        kind = attrs.get("kind")
        club = attrs.get("club")
        faction = kind if kind else ("Hi" if club == "Mr. Hi" else "Officer" if club else "Unknown")
        item = {"id": node, "faction": faction, "degree": graph.degree[node]}
        if "label" in attrs: item["label"] = str(attrs["label"])
        if "short" in attrs: item["short"] = str(attrs["short"])
        if "source_id" in attrs: item["source_id"] = str(attrs["source_id"])
        nodes.append(item)
    links = [{"source": u, "target": v, "weight": float(d.get("weight", 1.0))} for u, v, d in graph.edges(data=True)]
    return {"nodes": nodes, "links": links}

def sample_thresholds(graph, seed=THRESHOLD_SEED, distribution="uniform", parameters=None, custom=None):
    parameters = parameters or {"low": THRESHOLD_MIN, "high": THRESHOLD_MAX}
    if distribution == "custom":
        missing = set(graph.nodes) - set(custom or {})
        if missing: raise ValueError(f"custom thresholds missing nodes: {sorted(missing)}")
        return {n: float(custom[n]) for n in graph.nodes}
    rng = random.Random(seed)
    if distribution == "normal":
        mean, std = parameters.get("mean", .3), parameters.get("std", .1)
        return {n: min(1, max(0, rng.gauss(mean, std))) for n in sorted(graph.nodes)}
    low, high = parameters.get("low", .1), parameters.get("high", .5)
    return {n: rng.uniform(low, high) for n in sorted(graph.nodes)}

def _strategies(config, graph):
    if config.seed_strategies: return config.seed_strategies
    node = sorted(graph.degree, key=lambda x: (-x[1], x[0]))[0][0]
    return [{"key": "top_degree", "name": "Top-degree seed", "seeds": [node], "story": "Information starts at the highest-degree node."}]

def _payload(result, graph, strategy, model, parameters):
    times = {str(node): step for step, nodes in enumerate(result.steps) for node in nodes}
    return {"model": model, "name": strategy.get("name", str(strategy["seeds"])), "story": strategy.get("story", ""),
            "seeds": strategy["seeds"], "parameters": parameters, "steps": result.steps, "activation_times": times,
            "cumulative_reach": result.cumulative_reach, "total_reached": result.activated_total, "total_nodes": graph.number_of_nodes()}

def build_scenarios_payload(graph, config=None):
    config = config or default_config(); config.validate()
    payload, strategies = {}, _strategies(config, graph)
    if "independent_cascade" in config.models:
        for probability in config.probabilities:
            suffix = "" if len(config.probabilities) == 1 else f"_p{probability:g}".replace(".", "_")
            for i, strategy in enumerate(strategies):
                key = f"{strategy.get('key', f'seed_{i}')}{suffix}"
                rng_seed = int(strategy.get("random_seed", config.random_seed + i))
                result = independent_cascade(graph, strategy["seeds"], probability, random.Random(rng_seed))
                payload[key] = _payload(result, graph, strategy, "independent_cascade", {"activation_probability": probability, "random_seed": rng_seed})
    if "linear_threshold" in config.models:
        thresholds = sample_thresholds(graph, config.random_seed, config.threshold_distribution, config.threshold_parameters, config.thresholds)
        for i, strategy in enumerate(strategies):
            result = linear_threshold(graph, strategy["seeds"], thresholds, weight="weight")
            key = f"lt_{strategy.get('key', f'seed_{i}')}"
            payload[key] = _payload(result, graph, strategy, "linear_threshold", {"influence": "normalized_edge_weight", "threshold_distribution": config.threshold_distribution, "threshold_parameters": config.threshold_parameters, "threshold_seed": config.random_seed})
            payload[key]["thresholds"] = {str(k): v for k, v in thresholds.items()}
    return payload

def generate(config):
    config.validate()
    graph = normalize_node_ids(load_graph(config.graph, random_seed=config.random_seed, **config.graph_options))
    models = {
      "independent_cascade": {"name": "Independent Cascade", "short_name": "IC", "parameter": "configurable p", "description": "A newly mastered concept gets one chance to unlock each related concept — the 'aha' spreading."},
      "linear_threshold": {"name": "Linear Threshold", "short_name": "LT", "parameter": f"{config.threshold_distribution} thresholds", "description": "A concept is mastered once enough of its neighbors are mastered — reinforcement."}}
    return {"model": "multiple", "graph_source": config.graph, "models": {k: models[k] for k in config.models}, "graph": build_graph_payload(graph), "scenarios": build_scenarios_payload(graph, config)}

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, help="JSON configuration file")
    parser.add_argument("--graph", default="fourier", help="fourier, karate, generator spec, or graph file")
    parser.add_argument("--model", choices=["ic", "lt", "both"], default="both")
    parser.add_argument("--p", type=float, nargs="+", default=[P])
    parser.add_argument("--seeds", type=int, nargs="+", help="one custom seed set")
    parser.add_argument("--output", type=Path, help="write one JSON file instead of data/ and docs/")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.config:
        config = SimulationConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
    elif args.graph == "fourier" and args.model == "both" and args.p == [P] and not args.seeds:
        config = default_config()
    else:
        models = {"ic": ["independent_cascade"], "lt": ["linear_threshold"], "both": ["independent_cascade", "linear_threshold"]}[args.model]
        strategies = [{"key": "custom", "name": "Custom seeds", "seeds": args.seeds}] if args.seeds else []
        config = SimulationConfig(graph=args.graph, models=models, probabilities=args.p, seed_strategies=strategies)
    output = generate(config); root = Path(__file__).resolve().parent.parent
    targets = [args.output] if args.output else [root/"data/simulation.json", root/"docs/simulation.json"]
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"wrote {target}")

if __name__ == "__main__": main()
