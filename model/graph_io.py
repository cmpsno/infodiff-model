"""Load common graph files and NetworkX generators from a compact spec."""

from __future__ import annotations

import csv
from pathlib import Path

import networkx as nx


def load_graph(source: str, *, random_seed: int = 42, **options) -> nx.Graph:
    """Load a graph from a built-in name, generator spec, or local file.

    Generator specs may be supplied inline, for example ``erdos_renyi:100,0.05``.
    Supported files are CSV, edge lists, GML, GraphML and Pajek NET files.
    """
    if source == "karate":
        return nx.karate_club_graph()
    if source.startswith("erdos_renyi"):
        n, p = _generator_args(source, options, ("n", "p"), (34, 0.1))
        return nx.erdos_renyi_graph(int(n), float(p), seed=random_seed)
    if source.startswith("barabasi_albert"):
        n, m = _generator_args(source, options, ("n", "m"), (34, 2))
        return nx.barabasi_albert_graph(int(n), int(m), seed=random_seed)
    if source.startswith("watts_strogatz"):
        n, k, p = _generator_args(source, options, ("n", "k", "p"), (34, 4, 0.1))
        return nx.watts_strogatz_graph(int(n), int(k), float(p), seed=random_seed)

    path = Path(source)
    if not path.exists():
        raise ValueError(f"graph source does not exist: {source}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        graph = nx.Graph()
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            for row_number, row in enumerate(reader, 1):
                if not row or row[0].strip().startswith("#"):
                    continue
                if len(row) < 2:
                    raise ValueError(f"CSV row {row_number} needs source,target")
                try:
                    graph.add_edge(int(row[0]), int(row[1]))
                except ValueError:
                    if row_number == 1:
                        continue
                    raise ValueError(f"CSV row {row_number} has non-integer node ids")
        return graph
    readers = {
        ".edgelist": lambda p: nx.read_edgelist(p, nodetype=int, data=False),
        ".gml": nx.read_gml,
        ".graphml": nx.read_graphml,
        ".net": nx.read_pajek,
    }
    if suffix not in readers:
        raise ValueError(f"unsupported graph format: {suffix}")
    return nx.Graph(readers[suffix](path))


def _generator_args(source, options, names, defaults):
    if ":" in source:
        values = source.split(":", 1)[1].split(",")
        if len(values) != len(names):
            raise ValueError(f"{source.split(':')[0]} expects {len(names)} parameters")
        return values
    return tuple(options.get(name, default) for name, default in zip(names, defaults))


def normalize_node_ids(graph: nx.Graph) -> nx.Graph:
    """Relabel arbitrary file node ids to stable integers for JSON playback."""
    if all(isinstance(node, int) for node in graph.nodes):
        return graph
    return nx.convert_node_labels_to_integers(graph, label_attribute="source_id")
