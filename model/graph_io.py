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
    if source == "rumor":
        return rumor_market_graph()
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


def rumor_market_graph() -> nx.Graph:
    """Rumor network: how a hot CPI print reprices the Fed and moves the stock market.

    Nodes are rumor sources, transmission channels, market participants, and
    market outcomes; edges are information-flow links with weights. A rumor
    seeded at the FOMC (or a speaker, or retail) spreads across this graph
    the way information spreads across a social network: node ids are stable
    integers, human-readable names live in the ``label`` attribute, ``kind``
    marks the node's role, and market nodes carry an ``impact`` string
    describing the price move when the rumor reaches them. Node labels and
    impacts are anchored to the September 2026 episode: a hot August CPI
    print, a 25bp Fed hike to 3.75-4.00%, and the market pricing another.
    """
    nodes = {
        0: ("fomc", "FOMC", "FOMC — the Fed hikes 25bp to 3.75–4.00%", "source", ""),
        1: ("speaker", "Speaker", "Chair Warsh: inflation 'too high for too long'", "source", ""),
        2: ("wires", "Wires", "Bloomberg / Reuters newswires", "media", ""),
        3: ("social", "Social", "Financial social media", "media", ""),
        4: ("tv", "TV", "CNBC / TV coverage", "media", ""),
        5: ("algos", "Algos", "HFT / algo traders", "participant", ""),
        6: ("desks", "Desks", "Institutional trading desks", "participant", ""),
        7: ("makers", "Makers", "Market makers", "participant", ""),
        8: ("bonds", "Bonds", "Bond desks", "participant", ""),
        9: ("econ", "Econ", "Economists / strategists", "participant", ""),
        10: ("retail", "Retail", "Retail investors", "participant", ""),
        11: ("options", "Options", "Options / gamma desks", "participant", ""),
        12: ("fedfunds", "Odds", "Hike odds for the next meeting (FedWatch)", "market", "dot plot: one more hike this year"),
        13: ("y2", "2Y", "2-year Treasury yield", "market", "2Y 4.22% → 4.30%"),
        14: ("y10", "10Y", "10-year Treasury yield", "market", "10Y closed 5.006%"),
        15: ("spx", "S&P", "S&P 500", "market", "S&P 500 −0.45%"),
        16: ("ndx", "Nasdaq", "Nasdaq Composite", "market", "Nasdaq −0.01%"),
        17: ("vix", "VIX", "VIX volatility index", "market", "VIX 17.71 (+3%)"),
        18: ("dxy", "Dollar", "US dollar index", "market", "dollar +0.7%"),
        19: ("gold", "Gold", "Gold", "market", "gold fell to $4,310"),
    }
    edges = [
        (0, 2, 3), (0, 12, 3),
        (1, 2, 2), (1, 3, 2),
        (2, 3, 2), (2, 4, 2), (2, 5, 3), (2, 6, 2),
        (3, 5, 2), (3, 10, 2),
        (4, 10, 2),
        (5, 7, 2), (5, 12, 3),
        (6, 8, 2), (6, 9, 1), (6, 15, 2),
        (7, 15, 1),
        (8, 13, 3), (8, 14, 2),
        (9, 14, 1),
        (10, 11, 1), (10, 16, 1),
        (11, 17, 2),
        (12, 13, 2),
        (13, 14, 1), (13, 15, 1),
        (14, 18, 1),
        (15, 16, 2), (15, 17, 1),
        (18, 19, 1),
    ]
    graph = nx.Graph()
    for node, (name, short, label, kind, impact) in nodes.items():
        graph.add_node(node, name=name, short=short, label=label, kind=kind, impact=impact)
    for source, target, weight in edges:
        graph.add_edge(source, target, weight=weight)
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
