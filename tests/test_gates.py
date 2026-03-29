# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
tests/test_gates.py
===================
Unit tests for SafetyGate, GateCompiler and GateResult.
Uses only stdlib unittest — zero external dependencies.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from murphy_confidence.engine   import ConfidenceEngine
from murphy_confidence.gates    import SafetyGate
from murphy_confidence.compiler import GateCompiler
from murphy_confidence.types    import (
    Phase, GateAction, GateType, GateResult,
)


def _make_result(goodness=0.8, domain=0.8, hazard=0.1, phase=Phase.EXECUTE):
    return ConfidenceEngine().compute(goodness, domain, hazard, phase)


class TestSafetyGatePass(unittest.TestCase):
    """Gate pass / fail evaluation."""

    # --- Test 1 -----------------------------------------------------------
    def test_gate_passes_when_score_above_threshold(self):
        gate   = SafetyGate("test_ops", GateType.OPERATIONS, blocking=False, threshold=0.50)
        result = _make_result(goodness=1.0, domain=1.0, hazard=0.0, phase=Phase.EXPAND)
        gr     = gate.evaluate(result)
        self.assertTrue(gr.passed)

    # --- Test 2 -----------------------------------------------------------
    def test_gate_fails_when_score_below_threshold(self):
        gate   = SafetyGate("test_strict", GateType.COMPLIANCE, blocking=True, threshold=0.99)
        result = _make_result(goodness=0.5, domain=0.5, hazard=0.3)
        gr     = gate.evaluate(result)
        self.assertFalse(gr.passed)

    # --- Test 3 -----------------------------------------------------------
    def test_blocking_gate_fail_sets_block_action(self):
        gate   = SafetyGate("blocker", GateType.EXECUTIVE, blocking=True, threshold=0.99)
        result = _make_result(goodness=0.3, domain=0.3, hazard=0.5)
        gr     = gate.evaluate(result)
        if not gr.passed:
            self.assertEqual(gr.action, GateAction.BLOCK_EXECUTION)

    # --- Test 4 -----------------------------------------------------------
    def test_non_blocking_gate_fail_requests_approval(self):
        gate   = SafetyGate("soft_gate", GateType.BUDGET, blocking=False, threshold=0.99)
        result = _make_result(goodness=0.4, domain=0.4, hazard=0.4)
        gr     = gate.evaluate(result)
        if not gr.passed:
            self.assertEqual(gr.action, GateAction.REQUIRE_HUMAN_APPROVAL)

    # --- Test 5 -----------------------------------------------------------
    def test_gate_result_is_gate_result_type(self):
        gate   = SafetyGate("typed_gate", GateType.QA, threshold=0.60)
        result = _make_result()
        gr     = gate.evaluate(result)
        self.assertIsInstance(gr, GateResult)

    # --- Test 6 -----------------------------------------------------------
    def test_gate_result_as_dict_has_required_keys(self):
        gate   = SafetyGate("dict_gate", GateType.HITL)
        result = _make_result()
        gr     = gate.evaluate(result)
        d      = gr.as_dict()
        for key in ("gate_id", "gate_type", "blocking", "threshold", "passed",
                    "confidence_score", "action", "message"):
            self.assertIn(key, d)


class TestAllGateTypes(unittest.TestCase):
    """Each GateType can be evaluated."""

    def setUp(self):
        self.result = _make_result(goodness=0.75, domain=0.75, hazard=0.1)

    # --- Test 7 -----------------------------------------------------------
    def test_executive_gate(self):
        gr = SafetyGate("exec", GateType.EXECUTIVE).evaluate(self.result)
        self.assertIsInstance(gr, GateResult)
        self.assertEqual(gr.gate_type, GateType.EXECUTIVE)

    # --- Test 8 -----------------------------------------------------------
    def test_operations_gate(self):
        gr = SafetyGate("ops", GateType.OPERATIONS).evaluate(self.result)
        self.assertEqual(gr.gate_type, GateType.OPERATIONS)

    # --- Test 9 -----------------------------------------------------------
    def test_qa_gate(self):
        gr = SafetyGate("qa", GateType.QA).evaluate(self.result)
        self.assertEqual(gr.gate_type, GateType.QA)

    # --- Test 10 ----------------------------------------------------------
    def test_hitl_gate(self):
        gr = SafetyGate("hitl", GateType.HITL).evaluate(self.result)
        self.assertEqual(gr.gate_type, GateType.HITL)

    # --- Test 11 ----------------------------------------------------------
    def test_compliance_gate(self):
        gr = SafetyGate("comp", GateType.COMPLIANCE).evaluate(self.result)
        self.assertEqual(gr.gate_type, GateType.COMPLIANCE)

    # --- Test 12 ----------------------------------------------------------
    def test_budget_gate(self):
        gr = SafetyGate("budget", GateType.BUDGET).evaluate(self.result)
        self.assertEqual(gr.gate_type, GateType.BUDGET)


class TestThresholdBoundary(unittest.TestCase):
    """Boundary conditions at exactly the threshold."""

    def setUp(self):
        self.engine = ConfidenceEngine()

    # --- Test 13 ----------------------------------------------------------
    def test_score_exactly_at_threshold_passes(self):
        # Force a known score by choosing weights such that score = 0.70 exactly
        # EXPAND weights: w_g=0.60, w_d=0.30, kappa=0.10
        # g=0.80, d=0.60, h=0.20 → 0.60*0.80 + 0.30*0.60 - 0.10*0.20 = 0.48+0.18-0.02 = 0.64
        result = self.engine.compute(0.80, 0.60, 0.20, Phase.EXPAND)
        gate   = SafetyGate("boundary", GateType.OPERATIONS, blocking=False,
                            threshold=round(result.score, 6))
        gr     = gate.evaluate(result)
        self.assertTrue(gr.passed)

    # --- Test 14 ----------------------------------------------------------
    def test_score_just_below_threshold_fails(self):
        result    = self.engine.compute(0.80, 0.60, 0.20, Phase.EXPAND)
        threshold = result.score + 0.001
        gate      = SafetyGate("just_below", GateType.OPERATIONS, blocking=False,
                               threshold=threshold)
        gr        = gate.evaluate(result)
        self.assertFalse(gr.passed)

    # --- Test 15 ----------------------------------------------------------
    def test_default_blocking_for_compliance_gate(self):
        gate = SafetyGate("default_comp", GateType.COMPLIANCE)
        self.assertTrue(gate.blocking)

    # --- Test 16 ----------------------------------------------------------
    def test_default_non_blocking_for_budget_gate(self):
        gate = SafetyGate("default_budget", GateType.BUDGET)
        self.assertFalse(gate.blocking)


class TestGateCompiler(unittest.TestCase):
    """GateCompiler gate generation tests."""

    def setUp(self):
        self.compiler = GateCompiler()
        self.engine   = ConfidenceEngine()

    # --- Test 17 ----------------------------------------------------------
    def test_compiler_returns_list(self):
        result = self.engine.compute(0.7, 0.7, 0.1, Phase.EXECUTE)
        gates  = self.compiler.compile_gates(result)
        self.assertIsInstance(gates, list)

    # --- Test 18 ----------------------------------------------------------
    def test_compiler_returns_safety_gates(self):
        result = self.engine.compute(0.7, 0.7, 0.1, Phase.EXECUTE)
        gates  = self.compiler.compile_gates(result)
        for g in gates:
            self.assertIsInstance(g, SafetyGate)

    # --- Test 19 ----------------------------------------------------------
    def test_block_action_triggers_executive_gate(self):
        result = self.engine.compute(0.0, 0.0, 1.0, Phase.EXECUTE)
        gates  = self.compiler.compile_gates(result)
        types  = [g.gate_type for g in gates]
        self.assertIn(GateType.EXECUTIVE, types)

    # --- Test 20 ----------------------------------------------------------
    def test_compliance_context_adds_compliance_gate(self):
        result = self.engine.compute(0.8, 0.8, 0.1, Phase.EXECUTE)
        gates  = self.compiler.compile_gates(result, context={"compliance_required": True})
        types  = [g.gate_type for g in gates]
        self.assertIn(GateType.COMPLIANCE, types)

    # --- Test 21 ----------------------------------------------------------
    def test_no_duplicate_gate_ids(self):
        result = self.engine.compute(0.5, 0.5, 0.5, Phase.EXECUTE)
        gates  = self.compiler.compile_gates(result)
        ids    = [g.gate_id for g in gates]
        self.assertEqual(len(ids), len(set(ids)))

    # --- Test 22 ----------------------------------------------------------
    def test_extra_gates_context(self):
        extra  = SafetyGate("my_custom_gate", GateType.QA, blocking=False, threshold=0.60)
        result = self.engine.compute(0.8, 0.8, 0.1, Phase.BIND)
        gates  = self.compiler.compile_gates(result, context={"extra_gates": [extra]})
        ids    = [g.gate_id for g in gates]
        self.assertIn("my_custom_gate", ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
