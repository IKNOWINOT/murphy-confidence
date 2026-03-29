# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence.engine
========================
Multi-Factor Generative-Deterministic Confidence (MFGC) scoring engine.

Formula
-------
    C(t) = w_g · G(x) + w_d · D(x) − κ · H(x)

Where:
    G(x)  – Generative quality score          [0, 1]
    D(x)  – Domain-deterministic match score  [0, 1]
    H(x)  – Hazard / risk factor              [0, 1]
    w_g   – Weight for generative component
    w_d   – Weight for domain component
    κ     – Hazard penalty multiplier

Phase-locked weight schedules and adaptive thresholds are applied so that
the system becomes progressively more conservative as execution nears.

Zero external dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from .types import ConfidenceResult, GateAction, Phase


# ---------------------------------------------------------------------------
# Phase-locked weight schedules
# ---------------------------------------------------------------------------

_PHASE_WEIGHTS: Dict[Phase, Dict[str, float]] = {
    Phase.EXPAND:      {"w_g": 0.60, "w_d": 0.30, "kappa": 0.10},
    Phase.TYPE:        {"w_g": 0.55, "w_d": 0.35, "kappa": 0.10},
    Phase.ENUMERATE:   {"w_g": 0.50, "w_d": 0.40, "kappa": 0.10},
    Phase.CONSTRAIN:   {"w_g": 0.40, "w_d": 0.45, "kappa": 0.15},
    Phase.COLLAPSE:    {"w_g": 0.35, "w_d": 0.50, "kappa": 0.15},
    Phase.BIND:        {"w_g": 0.30, "w_d": 0.55, "kappa": 0.15},
    Phase.EXECUTE:     {"w_g": 0.25, "w_d": 0.55, "kappa": 0.20},
}

# Adaptive thresholds per phase — becomes stricter toward EXECUTE
_PHASE_THRESHOLDS: Dict[Phase, float] = {
    Phase.EXPAND:    0.50,
    Phase.TYPE:      0.55,
    Phase.ENUMERATE: 0.60,
    Phase.CONSTRAIN: 0.65,
    Phase.COLLAPSE:  0.70,
    Phase.BIND:      0.78,
    Phase.EXECUTE:   0.85,
}

# Six-tier action classification thresholds (applied after phase check)
_ACTION_THRESHOLDS: Tuple[Tuple[float, GateAction], ...] = (
    (0.90, GateAction.PROCEED_AUTOMATICALLY),
    (0.80, GateAction.PROCEED_WITH_MONITORING),
    (0.70, GateAction.PROCEED_WITH_CAUTION),
    (0.55, GateAction.REQUEST_HUMAN_REVIEW),
    (0.40, GateAction.REQUIRE_HUMAN_APPROVAL),
)


def _classify_action(score: float) -> GateAction:
    """Map a raw confidence score to a GateAction tier."""
    for threshold, action in _ACTION_THRESHOLDS:
        if score >= threshold:
            return action
    return GateAction.BLOCK_EXECUTION


def _build_rationale(
    score: float,
    phase: Phase,
    action: GateAction,
    phase_threshold: float,
    allowed: bool,
    weights: Dict[str, float],
    goodness: float,
    domain: float,
    hazard: float,
) -> str:
    status = "ALLOWED" if allowed else "BLOCKED"
    return (
        f"[{status}] Phase={phase.value} | "
        f"C={score:.4f} (threshold={phase_threshold:.2f}) | "
        f"Action={action.value} | "
        f"G={goodness:.3f} w_g={weights['w_g']:.2f} | "
        f"D={domain:.3f} w_d={weights['w_d']:.2f} | "
        f"H={hazard:.3f} κ={weights['kappa']:.2f}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ConfidenceEngine:
    """
    Stateless MFGC confidence engine.

    Usage::

        engine = ConfidenceEngine()
        result = engine.compute(
            goodness=0.82, domain=0.75, hazard=0.10, phase=Phase.EXECUTE
        )
        print(result.action)   # GateAction.PROCEED_WITH_MONITORING
    """

    def compute(
        self,
        goodness: float,
        domain: float,
        hazard: float,
        phase: Phase,
        weights: Optional[Dict[str, float]] = None,
    ) -> ConfidenceResult:
        """
        Compute a :class:`ConfidenceResult` using the MFGC formula.

        Parameters
        ----------
        goodness:
            Generative quality score G(x) ∈ [0, 1].
        domain:
            Domain-deterministic match score D(x) ∈ [0, 1].
        hazard:
            Hazard / risk factor H(x) ∈ [0, 1].
        phase:
            Current pipeline phase (determines weight schedule and threshold).
        weights:
            Optional override dict with keys ``w_g``, ``w_d``, ``kappa``.
        """
        goodness = max(0.0, min(1.0, float(goodness)))
        domain   = max(0.0, min(1.0, float(domain)))
        hazard   = max(0.0, min(1.0, float(hazard)))

        w = dict(_PHASE_WEIGHTS[phase])
        if weights:
            for key in ("w_g", "w_d", "kappa"):
                if key in weights:
                    w[key] = float(weights[key])

        # MFGC formula
        score = w["w_g"] * goodness + w["w_d"] * domain - w["kappa"] * hazard
        score = max(0.0, min(1.0, score))

        phase_threshold = _PHASE_THRESHOLDS[phase]
        action  = _classify_action(score)
        allowed = score >= phase_threshold

        # Override action to BLOCK if score is below phase threshold
        if not allowed and action not in (
            GateAction.BLOCK_EXECUTION, GateAction.REQUIRE_HUMAN_APPROVAL
        ):
            action = GateAction.REQUIRE_HUMAN_APPROVAL

        rationale = _build_rationale(
            score, phase, action, phase_threshold, allowed, w,
            goodness, domain, hazard,
        )

        return ConfidenceResult(
            score=round(score, 6),
            phase=phase,
            action=action,
            allowed=allowed,
            rationale=rationale,
            weights=w,
            timestamp=datetime.now(timezone.utc),
        )


def compute_confidence(
    goodness: float,
    domain: float,
    hazard: float,
    phase: Phase,
    weights: Optional[Dict[str, float]] = None,
) -> ConfidenceResult:
    """
    Module-level convenience wrapper around :class:`ConfidenceEngine`.

    Parameters
    ----------
    goodness:
        Generative quality score G(x) ∈ [0, 1].
    domain:
        Domain-deterministic match score D(x) ∈ [0, 1].
    hazard:
        Hazard / risk factor H(x) ∈ [0, 1].
    phase:
        Current pipeline :class:`Phase`.
    weights:
        Optional weight overrides (``w_g``, ``w_d``, ``kappa``).

    Returns
    -------
    ConfidenceResult
    """
    return ConfidenceEngine().compute(goodness, domain, hazard, phase, weights)
