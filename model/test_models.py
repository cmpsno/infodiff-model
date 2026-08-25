"""Regression tests for diffusion algorithms and generated playback data."""

from __future__ import annotations

import random
import unittest

import networkx as nx

from generate_simulation import THRESHOLD_SEED, build_scenarios_payload
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


class GeneratedDataTests(unittest.TestCase):
    def test_every_model_has_scenarios_that_follow_the_playback_contract(self) -> None:
        graph = nx.karate_club_graph()
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


if __name__ == "__main__":
    unittest.main()
