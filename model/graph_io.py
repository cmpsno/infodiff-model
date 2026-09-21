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
    if source == "fourier":
        return fourier_concept_graph()
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


def fourier_concept_graph() -> nx.Graph:
    """Concept graph for the Fourier / sine-wave learning domain.

    Nodes are core concepts and the four misconceptions (M1-M4) from the
    adaptive tutor's taxonomy; edges are prerequisite/relatedness links.
    Understanding spreads across this graph the way a rumor spreads across
    a social network: node ids are stable integers, human-readable names
    live in the ``label`` attribute, and ``kind`` marks core concepts vs
    misconceptions.
    """
    nodes = {
        0: ("frequency", "freq", "Frequency — cycles per second", "concept"),
        1: ("amplitude", "amp", "Amplitude — wave height", "concept"),
        2: ("phase", "phase", "Phase — where the cycle starts", "concept"),
        3: ("superposition", "superpos.", "Superposition — waves add point by point", "concept"),
        4: ("spectrum", "spectrum", "Spectrum — which frequencies a wave contains", "concept"),
        5: ("M1", "M1", "M1 · faster wiggle = taller wave", "misconception"),
        6: ("M2", "M2", "M2 · adding waves adds their frequencies", "misconception"),
        7: ("M3", "M3", "M3 · phase shift changes pitch", "misconception"),
        8: ("M4", "M4", "M4 · a square wave is one frequency", "misconception"),
    }
    edges = [
        (0, 5), (1, 5),      # M1 confuses frequency and amplitude
        (3, 6), (0, 6),      # M2 vs superposition / frequency
        (2, 7), (0, 7),      # M3 vs phase / frequency
        (4, 8), (3, 8),      # M4 vs spectrum / superposition
        (0, 3), (3, 4),      # frequency -> superposition -> spectrum
        (0, 2),              # frequency -> phase
        (1, 3),              # amplitude -> superposition
        (0, 4),              # frequency -> spectrum
    ]
    graph = nx.Graph()
    for node, (name, short, label, kind) in nodes.items():
        graph.add_node(node, name=name, short=short, label=label, kind=kind)
    graph.add_edges_from(edges)
    return graph


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
