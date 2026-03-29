# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence.compiler
==========================
Gate compiler — dynamically synthesises a list of :class:`SafetyGate` objects
from a :class:`ConfidenceResult` and optional execution context.

The compiler implements the core claim of Patent #2: "System and Method for
Dynamic Synthesis of Safety Gates in AI Execution Pipelines."

Zero external dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .gates import SafetyGate
from .types import ConfidenceResult, GateAction, GateType, Phase


# ---------------------------------------------------------------------------
# Compilation rules
# ---------------------------------------------------------------------------

# Maps (phase, action) → list of (gate_id, gate_type, blocking, threshold)
# Rules are additive: all matching rules contribute gates.
_RULES: List[
    tuple[
        Optional[Phase],       # None = any phase
        Optional[GateAction],  # None = any action
        str,                   # gate_id prefix
        GateType,
        bool,                  # blocking
        Optional[float],       # threshold override (None = default)
    ]
] = [
    # Always compile an OPERATIONS gate
    (None, None, "ops", GateType.OPERATIONS, False, None),

    # EXECUTE phase always needs a QA gate
    (Phase.EXECUTE, None, "qa_execute", GateType.QA, False, 0.80),

    # Any BLOCK or REQUIRE_HUMAN action triggers blocking EXECUTIVE gate
    (None, GateAction.BLOCK_EXECUTION,         "exec_block", GateType.EXECUTIVE, True,  None),
    (None, GateAction.REQUIRE_HUMAN_APPROVAL,  "exec_hitl",  GateType.HITL,     True,  None),
    (None, GateAction.REQUEST_HUMAN_REVIEW,    "exec_review", GateType.HITL,    False, 0.70),

    # EXECUTE phase with proceed actions gets a BUDGET gate
    (Phase.EXECUTE, GateAction.PROCEED_AUTOMATICALLY,   "budget_exec", GateType.BUDGET, False, None),
    (Phase.EXECUTE, GateAction.PROCEED_WITH_MONITORING, "budget_exec", GateType.BUDGET, False, None),
    (Phase.EXECUTE, GateAction.PROCEED_WITH_CAUTION,    "budget_exec", GateType.BUDGET, True,  None),
]


class GateCompiler:
    """
    Compiles a set of :class:`SafetyGate` objects from a confidence result.

    Usage::

        compiler = GateCompiler()
        gates = compiler.compile_gates(confidence_result)
        for gate in gates:
            result = gate.evaluate(confidence_result)
            print(result.message)
    """

    def compile_gates(
        self,
        confidence_result: ConfidenceResult,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[SafetyGate]:
        """
        Synthesise a gate list for *confidence_result*.

        Parameters
        ----------
        confidence_result:
            The scored result to drive gate selection.
        context:
            Optional dict with extra hints.  Recognised keys:

            * ``"compliance_required"`` (bool) → adds a COMPLIANCE gate
            * ``"budget_limit"`` (float) → overrides BUDGET gate threshold
            * ``"extra_gates"`` (list[SafetyGate]) → appended verbatim

        Returns
        -------
        List[SafetyGate]
            Ordered list of gates to evaluate (duplicates by gate_id removed,
            first occurrence wins).
        """
        ctx = context or {}
        phase  = confidence_result.phase
        action = confidence_result.action

        seen: set[str] = set()
        gates: List[SafetyGate] = []

        def _add(gate_id: str, gate_type: GateType, blocking: bool, threshold: Optional[float]) -> None:
            if gate_id not in seen:
                seen.add(gate_id)
                gates.append(SafetyGate(gate_id, gate_type, blocking, threshold))

        # Apply rule table
        for rule_phase, rule_action, gid, gtype, gblocking, gthreshold in _RULES:
            phase_match  = rule_phase  is None or rule_phase  == phase
            action_match = rule_action is None or rule_action == action
            if phase_match and action_match:
                _add(gid, gtype, gblocking, gthreshold)

        # Context-driven additions
        if ctx.get("compliance_required"):
            _add("compliance", GateType.COMPLIANCE, True, None)

        if "budget_limit" in ctx:
            budget_threshold = float(ctx["budget_limit"])
            _add("budget_ctx", GateType.BUDGET, False, budget_threshold)

        # Extra gates supplied by caller
        for extra in ctx.get("extra_gates", []):
            if isinstance(extra, SafetyGate) and extra.gate_id not in seen:
                seen.add(extra.gate_id)
                gates.append(extra)

        return gates
