# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence.gates
=======================
Safety gate evaluation logic for the Murphy Confidence Engine.

A :class:`SafetyGate` wraps a gate type, blocking flag, and threshold.
Calling :meth:`SafetyGate.evaluate` against a :class:`ConfidenceResult`
produces a :class:`GateResult` that records whether the gate passed and
what action should be taken.

Six gate types are supported:
  EXECUTIVE, OPERATIONS, QA, HITL, COMPLIANCE, BUDGET

Blocking gates halt execution when they fail; non-blocking gates annotate
the pipeline but allow execution to continue.

Zero external dependencies.
"""

from __future__ import annotations

from .types import ConfidenceResult, GateAction, GateResult, GateType


# ---------------------------------------------------------------------------
# Default thresholds per gate type
# ---------------------------------------------------------------------------

_DEFAULT_THRESHOLDS: dict[GateType, float] = {
    GateType.EXECUTIVE:  0.85,
    GateType.OPERATIONS: 0.70,
    GateType.QA:         0.75,
    GateType.HITL:       0.80,
    GateType.COMPLIANCE: 0.90,
    GateType.BUDGET:     0.65,
}

# Gate types that are blocking by default
_BLOCKING_BY_DEFAULT: frozenset[GateType] = frozenset({
    GateType.EXECUTIVE,
    GateType.COMPLIANCE,
    GateType.HITL,
})


def _pass_message(gate_id: str, gate_type: GateType, score: float, threshold: float) -> str:
    return (
        f"Gate '{gate_id}' ({gate_type.value}) PASSED — "
        f"confidence {score:.4f} ≥ threshold {threshold:.4f}"
    )


def _fail_message(gate_id: str, gate_type: GateType, score: float, threshold: float, blocking: bool) -> str:
    mode = "BLOCKING" if blocking else "NON-BLOCKING"
    return (
        f"Gate '{gate_id}' ({gate_type.value}) FAILED [{mode}] — "
        f"confidence {score:.4f} < threshold {threshold:.4f}"
    )


class SafetyGate:
    """
    A single configurable safety gate.

    Parameters
    ----------
    gate_id:
        Unique string identifier for this gate (e.g. ``"clinical_safety"``).
    gate_type:
        One of the six :class:`GateType` values.
    blocking:
        When ``True`` a failing gate blocks execution.  Defaults to the
        standard blocking policy for the given gate type.
    threshold:
        Minimum confidence score required to pass.  Defaults to the
        standard threshold for the given gate type.

    Usage::

        gate = SafetyGate("hipaa", GateType.COMPLIANCE)
        result = gate.evaluate(confidence_result)
        if not result.passed and result.blocking:
            raise RuntimeError(result.message)
    """

    def __init__(
        self,
        gate_id: str,
        gate_type: GateType,
        blocking: bool | None = None,
        threshold: float | None = None,
    ) -> None:
        self.gate_id   = gate_id
        self.gate_type = gate_type
        self.blocking  = (
            blocking
            if blocking is not None
            else (gate_type in _BLOCKING_BY_DEFAULT)
        )
        self.threshold = (
            threshold
            if threshold is not None
            else _DEFAULT_THRESHOLDS[gate_type]
        )

    # ------------------------------------------------------------------
    def evaluate(self, confidence_result: ConfidenceResult) -> GateResult:
        """
        Evaluate this gate against *confidence_result*.

        Parameters
        ----------
        confidence_result:
            A :class:`ConfidenceResult` produced by :class:`ConfidenceEngine`.

        Returns
        -------
        GateResult
        """
        score  = confidence_result.score
        passed = score >= self.threshold

        if passed:
            action  = confidence_result.action
            message = _pass_message(
                self.gate_id, self.gate_type, score, self.threshold
            )
        else:
            # Failing a blocking gate upgrades action to BLOCK_EXECUTION
            action = (
                GateAction.BLOCK_EXECUTION
                if self.blocking
                else GateAction.REQUIRE_HUMAN_APPROVAL
            )
            message = _fail_message(
                self.gate_id, self.gate_type, score, self.threshold, self.blocking
            )

        return GateResult(
            gate_id=self.gate_id,
            gate_type=self.gate_type,
            blocking=self.blocking,
            threshold=self.threshold,
            passed=passed,
            confidence_score=score,
            action=action,
            message=message,
        )

    def __repr__(self) -> str:
        return (
            f"SafetyGate(id={self.gate_id!r}, type={self.gate_type.value}, "
            f"blocking={self.blocking}, threshold={self.threshold})"
        )
