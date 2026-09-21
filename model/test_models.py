"""Regression tests for diffusion algorithms and generated playback data."""

from __future__ import annotations

import random
import unittest

import networkx as nx

from batch_simulate import run_batch
from configuration import SimulationConfig
from generate_simulation import FOURIER_THRESHOLDS, THRESHOLD_SEED, build_scenarios_payload
from graph_io import fourier_concept_graph, load_graph
from independent_cascade import independent_cascade
from linear_threshold import linear_threshold


class ResultContractMixin:
    def assert_valid_result(self, result, node_count: int) -> None:
        flattened = [node for step in result.steps for node in step]
        self.assertEqual(result.steps[0], result.seeds)
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(result.activated_total, len(flattened))
        self.assertLessEqual(result.activated_total, node_count)
        self.assertEqual(result.cumulative_reach[-1], result.activated_total)
        self.assertEqual(
            result.cumulative_reach,
            [sum(len(step) for step in result.steps[: i + 1]) for i in range(len(result.steps))],
        )


class IndependentCascadeTests(ResultContractMixin, unittest.TestCase):
    def test_seeded_run_is_reproducible_and_valid(self) -> None:
        graph = nx.karate_club_graph()
        first = independent_cascade(graph, [33], 0.2, random.Random(2))
        second = independent_cascade(graph, [33], 0.2, random.Random(2))
        self.assertEqual(first.steps, second.steps)
        self.assert_valid_result(first, graph.number_of_nodes())

    def test_zero_probability_stops_at_seeds(self) -> None:
        graph = nx.path_graph(4)
        result = independent_cascade(graph, [0], 0, random.Random(1))
        self.assertEqual(result.steps, [[0]])

    def test_invalid_probability_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "p must be between 0 and 1"):
            independent_cascade(nx.path_graph(2), [0], 1.1, random.Random(1))


class LinearThresholdTests(ResultContractMixin, unittest.TestCase):
    def test_synchronous_threshold_activation(self) -> None:
        graph = nx.path_graph(4)
        thresholds = {0: 1.0, 1: 0.5, 2: 0.5, 3: 1.0}
        result = linear_threshold(graph, [0], thresholds)
        self.assertEqual(result.steps, [[0], [1], [2], [3]])
        self.assert_valid_result(result, graph.number_of_nodes())

    def test_missing_threshold_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "thresholds are missing"):
            linear_threshold(nx.path_graph(2), [0], {0: 0.5})

    def test_frequency_first_spread_is_deterministic(self) -> None:
        graph = fourier_concept_graph()
        result = linear_threshold(graph, [0], FOURIER_THRESHOLDS)
        self.assertEqual(result.steps, [[0], [2, 4], [3, 7], [1, 6, 8], [5]])
        self.assert_valid_result(result, graph.number_of_nodes())

    def test_misconception_seed_stalls(self) -> None:
        graph = fourier_concept_graph()
        result = linear_threshold(graph, [5], FOURIER_THRESHOLDS)
        self.assertEqual(result.steps, [[5], [1]])
        self.assert_valid_result(result, graph.number_of_nodes())


class FourierGraphTests(unittest.TestCase):
    def test_concept_graph_structure(self) -> None:
        graph = fourier_concept_graph()
        self.assertEqual(graph.number_of_nodes(), 9)
        self.assertEqual(graph.number_of_edges(), 13)
        kinds = [graph.nodes[n]["kind"] for n in graph.nodes]
        self.assertEqual(kinds.count("concept"), 5)
        self.assertEqual(kinds.count("misconception"), 4)
        for node in graph.nodes:
            self.assertTrue(graph.nodes[node]["label"])
            self.assertTrue(graph.nodes[node]["short"])

    def test_load_graph_fourier(self) -> None:
        graph = load_graph("fourier")
        self.assertEqual(graph.number_of_nodes(), 9)


class GeneratedDataTests(unittest.TestCase):
    def test_every_model_has_scenarios_that_follow_the_playback_contract(self) -> None:
        graph = load_graph("fourier")
        scenarios = build_scenarios_payload(graph)
        self.assertEqual(
            {scenario["model"] for scenario in scenarios.values()},
            {"independent_cascade", "linear_threshold"},
        )
        self.assertEqual(len(scenarios), 8)
        self.assertEqual(
            {
                scenario["parameters"]["threshold_seed"]
                for scenario in scenarios.values()
                if scenario["model"] == "linear_threshold"
            },
            {THRESHOLD_SEED},
        )

        for scenario in scenarios.values():
            with self.subTest(scenario=scenario["name"], model=scenario["model"]):
                flattened = [node for step in scenario["steps"] for node in step]
                self.assertEqual(scenario["steps"][0], scenario["seeds"])
                self.assertEqual(len(flattened), len(set(flattened)))
                self.assertEqual(scenario["total_reached"], len(flattened))
                self.assertEqual(
                    scenario["cumulative_reach"][-1], scenario["total_reached"]
                )
                self.assertEqual(scenario["total_nodes"], graph.number_of_nodes())

    def test_parameter_sweep_and_activation_times(self) -> None:
        graph = nx.path_graph(5)
        config = SimulationConfig(
            models=["independent_cascade"],
            probabilities=[0, 1],
            seed_strategies=[{"key": "start", "name": "Start", "seeds": [0]}],
        )
        scenarios = build_scenarios_payload(graph, config)
        self.assertEqual(len(scenarios), 2)
        self.assertEqual(scenarios["start_p0"]["activation_times"], {"0": 0})
        self.assertEqual(scenarios["start_p1"]["total_reached"], 5)

    def test_graph_generator_and_batch_summary(self) -> None:
        graph = load_graph("erdos_renyi:12,0.2", random_seed=7)
        self.assertEqual(graph.number_of_nodes(), 12)
        rows, summaries = run_batch(nx.path_graph(4), [0], [1.0], 3)
        self.assertEqual(len(rows), 3)
        self.assertEqual(summaries[0]["mean"], 4)


if __name__ == "__main__":
    unittest.main()
