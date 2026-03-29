# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
examples/safety_gates.py
========================
Demonstrates creating custom SafetyGate objects, evaluating them against
a confidence result, and handling blocking gate failures.

Run:
    python examples/safety_gates.py
"""

from murphy_confidence import SafetyGate, compute_confidence
from murphy_confidence.types import GateAction, GateType, Phase


def demo_default_gates() -> None:
    print("─" * 60)
    print("1. Default gate thresholds per gate type")
    print("─" * 60)

    result = compute_confidence(0.72, 0.68, 0.18, Phase.EXECUTE)
    print(f"Confidence score: {result.score:.4f}  Action: {result.action.value}")
    print()

    gate_types = [
        GateType.EXECUTIVE,
        GateType.OPERATIONS,
        GateType.QA,
        GateType.HITL,
        GateType.COMPLIANCE,
        GateType.BUDGET,
    ]

    print(f"{'Gate Type':<14} {'Threshold':>9}  {'Blocking':>8}  {'Passed':>6}  Message")
    print("-" * 90)

    for gtype in gate_types:
        gate = SafetyGate(gtype.value.lower(), gtype)
        gr = gate.evaluate(result)
        passed_str = "✓" if gr.passed else "✗"
        print(
            f"{gtype.value:<14} {gr.threshold:>9.2f}  {str(gr.blocking):>8}  "
            f"{passed_str:>6}  {gr.message}"
        )
    print()


def demo_custom_gate() -> None:
    print("─" * 60)
    print("2. Custom gate with non-default threshold")
    print("─" * 60)

    # A medical device scenario: compliance gate at 0.95, blocking
    gate = SafetyGate("fda_class_ii", GateType.COMPLIANCE, blocking=True, threshold=0.95)
    result = compute_confidence(0.85, 0.80, 0.05, Phase.EXECUTE)

    print(f"Gate: {gate!r}")
    print(f"Confidence score: {result.score:.4f}")

    gr = gate.evaluate(result)
    print(f"Gate result: passed={gr.passed}  action={gr.action.value}")
    print(f"Message: {gr.message}")
    print()


def demo_blocking_behavior() -> None:
    print("─" * 60)
    print("3. Blocking vs. non-blocking gate behaviour")
    print("─" * 60)

    result = compute_confidence(0.60, 0.55, 0.30, Phase.EXECUTE)
    print(f"Low-confidence result: score={result.score:.4f}")
    print()

    blocking_gate     = SafetyGate("safety_stop",  GateType.EXECUTIVE,  blocking=True)
    nonblocking_gate  = SafetyGate("audit_trail",  GateType.OPERATIONS, blocking=False)

    for gate in (blocking_gate, nonblocking_gate):
        gr = gate.evaluate(result)
        if not gr.passed and gr.blocking:
            print(f"  [BLOCKED] {gr.message}")
            print("  → Execution halted by blocking gate.")
        elif not gr.passed:
            print(f"  [WARN]    {gr.message}")
            print("  → Non-blocking: execution continues with annotation.")
        else:
            print(f"  [OK]      {gr.message}")
    print()


def demo_gate_pipeline() -> None:
    print("─" * 60)
    print("4. Gate pipeline — evaluate a suite of gates")
    print("─" * 60)

    gates = [
        SafetyGate("ops_check",    GateType.OPERATIONS, blocking=False),
        SafetyGate("qa_check",     GateType.QA,         blocking=False, threshold=0.75),
        SafetyGate("hitl_approve", GateType.HITL,       blocking=True),
        SafetyGate("compliance",   GateType.COMPLIANCE, blocking=True),
    ]

    result = compute_confidence(0.82, 0.78, 0.08, Phase.EXECUTE)
    print(f"Confidence score: {result.score:.4f}  Action: {result.action.value}")
    print()

    all_passed = True
    for gate in gates:
        gr = gate.evaluate(result)
        status = "✓ PASS" if gr.passed else ("✗ BLOCK" if gr.blocking else "⚠ WARN")
        print(f"  [{status}] {gr.gate_id:<16} threshold={gr.threshold:.2f}")
        if not gr.passed and gr.blocking:
            all_passed = False
            print(f"    → {gr.message}")
            print("    → EXECUTION HALTED")
            break

    if all_passed:
        print()
        print("  All gates passed — execution may proceed.")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print(" murphy-confidence  |  Safety Gates Demo")
    print("=" * 60)
    print()
    demo_default_gates()
    demo_custom_gate()
    demo_blocking_behavior()
    demo_gate_pipeline()
