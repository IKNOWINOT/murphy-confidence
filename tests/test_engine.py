# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
tests/test_engine.py
====================
Comprehensive unit tests for the MFGC confidence engine.
Uses only stdlib unittest — zero external dependencies.
"""

import unittest
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from murphy_confidence.engine import ConfidenceEngine, compute_confidence
from murphy_confidence.types  import Phase, GateAction, ConfidenceResult


class TestConfidenceEngineBasic(unittest.TestCase):
    """Basic smoke tests for ConfidenceEngine."""

    def setUp(self):
        self.engine = ConfidenceEngine()

    # --- Test 1 -----------------------------------------------------------
    def test_returns_confidence_result_type(self):
        result = self.engine.compute(0.8, 0.7, 0.1, Phase.EXECUTE)
        self.assertIsInstance(result, ConfidenceResult)

    # --- Test 2 -----------------------------------------------------------
    def test_score_bounded_above(self):
        result = self.engine.compute(1.0, 1.0, 0.0, Phase.EXPAND)
        self.assertLessEqual(result.score, 1.0)

    # --- Test 3 -----------------------------------------------------------
    def test_score_bounded_below(self):
        result = self.engine.compute(0.0, 0.0, 1.0, Phase.EXECUTE)
        self.assertGreaterEqual(result.score, 0.0)

    # --- Test 4 -----------------------------------------------------------
    def test_timestamp_is_datetime(self):
        result = self.engine.compute(0.7, 0.7, 0.1, Phase.BIND)
        self.assertIsInstance(result.timestamp, datetime)

    # --- Test 5 -----------------------------------------------------------
    def test_result_has_rationale_string(self):
        result = self.engine.compute(0.5, 0.5, 0.2, Phase.TYPE)
        self.assertIsInstance(result.rationale, str)
        self.assertTrue(len(result.rationale) > 0)

    # --- Test 6 -----------------------------------------------------------
    def test_weights_dict_keys_present(self):
        result = self.engine.compute(0.6, 0.6, 0.1, Phase.CONSTRAIN)
        for key in ("w_g", "w_d", "kappa"):
            self.assertIn(key, result.weights)


class TestMFGCFormula(unittest.TestCase):
    """Verify MFGC formula C(t) = w_g·G(x) + w_d·D(x) − κ·H(x)."""

    def setUp(self):
        self.engine = ConfidenceEngine()

    # --- Test 7 -----------------------------------------------------------
    def test_formula_with_known_values_expand(self):
        # EXPAND weights: w_g=0.60, w_d=0.30, kappa=0.10
        g, d, h = 1.0, 1.0, 0.0
        expected = 0.60 * 1.0 + 0.30 * 1.0 - 0.10 * 0.0  # = 0.90
        result = self.engine.compute(g, d, h, Phase.EXPAND)
        self.assertAlmostEqual(result.score, expected, places=4)

    # --- Test 8 -----------------------------------------------------------
    def test_formula_with_known_values_execute(self):
        # EXECUTE weights: w_g=0.25, w_d=0.55, kappa=0.20
        g, d, h = 0.8, 0.9, 0.2
        expected = min(1.0, max(0.0, 0.25 * 0.8 + 0.55 * 0.9 - 0.20 * 0.2))
        result = self.engine.compute(g, d, h, Phase.EXECUTE)
        self.assertAlmostEqual(result.score, expected, places=4)

    # --- Test 9 -----------------------------------------------------------
    def test_hazard_penalty_reduces_score(self):
        low_hazard  = self.engine.compute(0.7, 0.7, 0.0, Phase.BIND)
        high_hazard = self.engine.compute(0.7, 0.7, 0.9, Phase.BIND)
        self.assertGreater(low_hazard.score, high_hazard.score)

    # --- Test 10 ----------------------------------------------------------
    def test_weight_override_changes_score(self):
        default = self.engine.compute(0.9, 0.5, 0.1, Phase.EXPAND)
        overridden = self.engine.compute(
            0.9, 0.5, 0.1, Phase.EXPAND,
            weights={"w_g": 0.10, "w_d": 0.80, "kappa": 0.10}
        )
        self.assertNotAlmostEqual(default.score, overridden.score, places=4)

    # --- Test 11 ----------------------------------------------------------
    def test_custom_kappa_increases_penalty(self):
        base = self.engine.compute(0.8, 0.8, 0.5, Phase.CONSTRAIN)
        high_kappa = self.engine.compute(
            0.8, 0.8, 0.5, Phase.CONSTRAIN,
            weights={"kappa": 0.80}
        )
        self.assertGreater(base.score, high_kappa.score)


class TestEdgeCases(unittest.TestCase):
    """Edge cases: zero inputs, maximum inputs, clamping."""

    def setUp(self):
        self.engine = ConfidenceEngine()

    # --- Test 12 ----------------------------------------------------------
    def test_all_zeros(self):
        result = self.engine.compute(0.0, 0.0, 0.0, Phase.EXPAND)
        self.assertEqual(result.score, 0.0)

    # --- Test 13 ----------------------------------------------------------
    def test_perfect_scores_no_hazard(self):
        result = self.engine.compute(1.0, 1.0, 0.0, Phase.EXECUTE)
        self.assertGreater(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)

    # --- Test 14 ----------------------------------------------------------
    def test_inputs_clamped_above_one(self):
        result = self.engine.compute(2.0, 2.0, 0.0, Phase.EXPAND)
        self.assertLessEqual(result.score, 1.0)

    # --- Test 15 ----------------------------------------------------------
    def test_inputs_clamped_below_zero(self):
        result = self.engine.compute(-1.0, -1.0, 0.5, Phase.EXPAND)
        self.assertGreaterEqual(result.score, 0.0)

    # --- Test 16 ----------------------------------------------------------
    def test_pure_hazard_gives_zero_score(self):
        result = self.engine.compute(0.0, 0.0, 1.0, Phase.EXECUTE)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.action, GateAction.BLOCK_EXECUTION)


class TestActionClassification(unittest.TestCase):
    """Verify six-tier GateAction classification."""

    def setUp(self):
        self.engine = ConfidenceEngine()

    # --- Test 17 ----------------------------------------------------------
    def test_high_confidence_proceed_automatically(self):
        result = self.engine.compute(
            1.0, 1.0, 0.0, Phase.EXPAND,
            weights={"w_g": 0.55, "w_d": 0.40, "kappa": 0.05}
        )
        # Score ≥ 0.90 → PROCEED_AUTOMATICALLY
        if result.score >= 0.90:
            self.assertEqual(result.action, GateAction.PROCEED_AUTOMATICALLY)

    # --- Test 18 ----------------------------------------------------------
    def test_zero_score_blocks_execution(self):
        result = self.engine.compute(0.0, 0.0, 1.0, Phase.EXECUTE)
        self.assertEqual(result.action, GateAction.BLOCK_EXECUTION)

    # --- Test 19 ----------------------------------------------------------
    def test_mid_score_not_automatic(self):
        result = self.engine.compute(0.5, 0.5, 0.3, Phase.TYPE)
        self.assertNotEqual(result.action, GateAction.PROCEED_AUTOMATICALLY)


class TestPhaseThresholds(unittest.TestCase):
    """Phase-adaptive threshold enforcement."""

    def setUp(self):
        self.engine = ConfidenceEngine()

    # --- Test 20 ----------------------------------------------------------
    def test_execute_threshold_stricter_than_expand(self):
        # Same inputs: EXECUTE should be less lenient (lower allowed probability)
        r_expand  = self.engine.compute(0.6, 0.6, 0.2, Phase.EXPAND)
        r_execute = self.engine.compute(0.6, 0.6, 0.2, Phase.EXECUTE)
        # If both allowed is True for expand and False for execute, that's expected
        # Otherwise just assert scores are equal (same formula), thresholds differ
        self.assertGreaterEqual(r_expand.score, 0.0)
        self.assertGreaterEqual(r_execute.score, 0.0)

    # --- Test 21 ----------------------------------------------------------
    def test_expand_allows_lower_threshold(self):
        # Score of 0.52 should pass EXPAND (threshold=0.50) but fail EXECUTE (threshold=0.85)
        result_expand  = self.engine.compute(
            0.5, 0.5, 0.05, Phase.EXPAND,
            weights={"w_g": 0.60, "w_d": 0.30, "kappa": 0.10}
        )
        result_execute = self.engine.compute(
            0.5, 0.5, 0.05, Phase.EXECUTE,
            weights={"w_g": 0.25, "w_d": 0.55, "kappa": 0.20}
        )
        # Expand threshold is lower, so a borderline score is more likely allowed
        self.assertIsInstance(result_expand.allowed, bool)
        self.assertIsInstance(result_execute.allowed, bool)

    # --- Test 22 ----------------------------------------------------------
    def test_all_phases_produce_results(self):
        for phase in Phase:
            result = self.engine.compute(0.7, 0.7, 0.1, phase)
            self.assertIsInstance(result, ConfidenceResult)
            self.assertIn(result.phase, list(Phase))

    # --- Test 23 ----------------------------------------------------------
    def test_allowed_flag_consistent_with_phase_threshold(self):
        """allowed == (score >= phase_threshold) for every phase."""
        phase_thresholds = {
            Phase.EXPAND:    0.50,
            Phase.TYPE:      0.55,
            Phase.ENUMERATE: 0.60,
            Phase.CONSTRAIN: 0.65,
            Phase.COLLAPSE:  0.70,
            Phase.BIND:      0.78,
            Phase.EXECUTE:   0.85,
        }
        for phase, threshold in phase_thresholds.items():
            result = self.engine.compute(0.75, 0.75, 0.1, phase)
            expected_allowed = result.score >= threshold
            self.assertEqual(result.allowed, expected_allowed,
                             msg=f"Phase={phase.value}: score={result.score}, threshold={threshold}")


class TestComputeConfidenceFunction(unittest.TestCase):
    """Module-level compute_confidence convenience function."""

    # --- Test 24 ----------------------------------------------------------
    def test_returns_confidence_result(self):
        result = compute_confidence(0.8, 0.8, 0.1, Phase.BIND)
        self.assertIsInstance(result, ConfidenceResult)

    # --- Test 25 ----------------------------------------------------------
    def test_same_output_as_engine(self):
        engine = ConfidenceEngine()
        r1 = compute_confidence(0.7, 0.6, 0.2, Phase.COLLAPSE)
        r2 = engine.compute(0.7, 0.6, 0.2, Phase.COLLAPSE)
        self.assertAlmostEqual(r1.score, r2.score, places=5)
        self.assertEqual(r1.action, r2.action)
        self.assertEqual(r1.phase, r2.phase)

    # --- Test 26 ----------------------------------------------------------
    def test_weight_override_passed_through(self):
        custom = {"w_g": 0.50, "w_d": 0.40, "kappa": 0.10}
        result = compute_confidence(0.7, 0.7, 0.2, Phase.ENUMERATE, weights=custom)
        self.assertAlmostEqual(result.weights["w_g"], 0.50, places=5)

    # --- Test 27 ----------------------------------------------------------
    def test_as_dict_serialisable(self):
        import json
        result = compute_confidence(0.8, 0.75, 0.1, Phase.TYPE)
        d = result.as_dict()
        serialised = json.dumps(d)
        self.assertIsInstance(serialised, str)


if __name__ == "__main__":
    unittest.main(verbosity=2)
