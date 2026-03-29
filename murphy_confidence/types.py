# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence.types
=======================
Pure-Python data classes and enumerations that form the type system for the
Murphy Confidence Engine.  No external dependencies required.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Optional


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class Phase(enum.Enum):
    """The seven phases of the Murphy confidence pipeline."""
    EXPAND      = "EXPAND"
    TYPE        = "TYPE"
    ENUMERATE   = "ENUMERATE"
    CONSTRAIN   = "CONSTRAIN"
    COLLAPSE    = "COLLAPSE"
    BIND        = "BIND"
    EXECUTE     = "EXECUTE"


class GateAction(enum.Enum):
    """Six-tier action classification produced by confidence scoring."""
    PROCEED_AUTOMATICALLY    = "PROCEED_AUTOMATICALLY"
    PROCEED_WITH_MONITORING  = "PROCEED_WITH_MONITORING"
    PROCEED_WITH_CAUTION     = "PROCEED_WITH_CAUTION"
    REQUEST_HUMAN_REVIEW     = "REQUEST_HUMAN_REVIEW"
    REQUIRE_HUMAN_APPROVAL   = "REQUIRE_HUMAN_APPROVAL"
    BLOCK_EXECUTION          = "BLOCK_EXECUTION"


class GateType(enum.Enum):
    """Types of safety gates that can be compiled into an execution pipeline."""
    EXECUTIVE   = "EXECUTIVE"
    OPERATIONS  = "OPERATIONS"
    QA          = "QA"
    HITL        = "HITL"          # Human-In-The-Loop
    COMPLIANCE  = "COMPLIANCE"
    BUDGET      = "BUDGET"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ConfidenceResult:
    """Output produced by :class:`ConfidenceEngine.compute_confidence`."""
    score:     float
    phase:     Phase
    action:    GateAction
    allowed:   bool
    rationale: str
    weights:   Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict:
        return {
            "score":     self.score,
            "phase":     self.phase.value,
            "action":    self.action.value,
            "allowed":   self.allowed,
            "rationale": self.rationale,
            "weights":   self.weights,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class GateResult:
    """Output produced by :class:`SafetyGate.evaluate`."""
    gate_id:          str
    gate_type:        GateType
    blocking:         bool
    threshold:        float
    passed:           bool
    confidence_score: float
    action:           GateAction
    message:          str

    def as_dict(self) -> dict:
        return {
            "gate_id":          self.gate_id,
            "gate_type":        self.gate_type.value,
            "blocking":         self.blocking,
            "threshold":        self.threshold,
            "passed":           self.passed,
            "confidence_score": self.confidence_score,
            "action":           self.action.value,
            "message":          self.message,
        }
