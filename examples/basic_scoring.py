# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
examples/basic_scoring.py
=========================
Demonstrates the core compute_confidence() function across all 7 pipeline
phases, showing how the phase-locked weight schedule makes the engine
progressively stricter as execution approaches.

Run:
    python examples/basic_scoring.py
"""

from murphy_confidence import compute_confidence
from murphy_confidence.types import Phase, GateAction


def main() -> None:
    print("=" * 65)
    print(" murphy-confidence  |  Basic Scoring Demo")
    print("=" * 65)
    print()

    # Moderate-quality inputs — watch how strictness ramps up by phase
    goodness = 0.78
    domain   = 0.72
    hazard   = 0.15

    print(f"Inputs: goodness={goodness}  domain={domain}  hazard={hazard}")
    print()
    print(f"{'Phase':<12} {'Score':>7}  {'Action':<30}  {'Allowed'}")
    print("-" * 65)

    for phase in Phase:
        result = compute_confidence(goodness, domain, hazard, phase)
        allowed_str = "✓ YES" if result.allowed else "✗ NO"
        print(
            f"{phase.value:<12} {result.score:>7.4f}  "
            f"{result.action.value:<30}  {allowed_str}"
        )

    print()
    print("─" * 65)
    print("Notice: same inputs — blocked at EXECUTE because the")
    print("phase threshold ramps from 0.50 (EXPAND) to 0.85 (EXECUTE).")
    print()

    # High-confidence inputs — allowed at every phase
    print("High-confidence run (goodness=0.95, domain=0.90, hazard=0.02):")
    print()
    print(f"{'Phase':<12} {'Score':>7}  {'Action':<30}  {'Allowed'}")
    print("-" * 65)
    for phase in Phase:
        result = compute_confidence(0.95, 0.90, 0.02, phase)
        allowed_str = "✓ YES" if result.allowed else "✗ NO"
        print(
            f"{phase.value:<12} {result.score:>7.4f}  "
            f"{result.action.value:<30}  {allowed_str}"
        )

    print()

    # Full rationale for the EXECUTE phase
    print("Full rationale at EXECUTE phase (high-confidence):")
    result = compute_confidence(0.95, 0.90, 0.02, Phase.EXECUTE)
    print(f"  {result.rationale}")
    print()

    # Custom weight override
    print("Custom weight override (w_g=0.10, w_d=0.80, kappa=0.10):")
    result = compute_confidence(
        0.78, 0.72, 0.15, Phase.EXECUTE,
        weights={"w_g": 0.10, "w_d": 0.80, "kappa": 0.10},
    )
    print(f"  Score: {result.score:.4f}  Action: {result.action.value}  Allowed: {result.allowed}")
    print()

    # as_dict() for JSON serialisation
    print("result.as_dict() output:")
    import json
    data = result.as_dict()
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    main()
