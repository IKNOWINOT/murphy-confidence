# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
murphy_confidence
=================
Standalone, zero-dependency confidence-scoring library for the Murphy System.

Public surface::

    from murphy_confidence import ConfidenceEngine, SafetyGate, GateCompiler, compute_confidence
    from murphy_confidence.types import Phase, GateAction, GateType, ConfidenceResult, GateResult
"""

from .engine   import ConfidenceEngine, compute_confidence
from .gates    import SafetyGate
from .compiler import GateCompiler
from .types    import (
    Phase,
    GateAction,
    GateType,
    ConfidenceResult,
    GateResult,
)

__all__ = [
    "ConfidenceEngine",
    "SafetyGate",
    "GateCompiler",
    "compute_confidence",
    "Phase",
    "GateAction",
    "GateType",
    "ConfidenceResult",
    "GateResult",
]

__version__ = "0.1.0"
__author__  = "Corey Post"
__license__ = "Apache-2.0"
