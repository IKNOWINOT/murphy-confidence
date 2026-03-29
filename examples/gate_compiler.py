# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
examples/gate_compiler.py
=========================
Demonstrates GateCompiler — the dynamic gate synthesis engine that
builds the right gate set from a confidence result and execution context.

Run:
    python examples/gate_compiler.py
"""

from murphy_confidence import GateCompiler, SafetyGate, compute_confidence
from murphy_confidence.types import GateType, Phase


def demo_basic_compile() -> None:
    print("─" * 60)
    print("1. Basic compilation — moderate score at EXECUTE")
    print("─" * 60)

    result = compute_confidence(0.72, 0.68, 0.18, Phase.EXECUTE)
    print(f"Confidence: score={result.score:.4f}  action={result.action.value}")
    print()

    compiler = GateCompiler()
    gates = compiler.compile_gates(result)

    print(f"Compiled {len(gates)} gate(s):")
    for gate in gates:
        print(f"  {gate!r}")
    print()


def demo_compliance_context() -> None:
    print("─" * 60)
    print("2. With compliance_required=True context")
    print("─" * 60)

    result = compute_confidence(0.88, 0.84, 0.05, Phase.EXECUTE)
    compiler = GateCompiler()
    gates = compiler.compile_gates(result, context={"compliance_required": True})

    print(f"Compiled {len(gates)} gate(s):")
    for gate in gates:
        print(f"  {gate!r}")

    # Evaluate all gates
    print()
    print("Evaluation results:")
    for gate in gates:
        gr = gate.evaluate(result)
        status = "PASS" if gr.passed else ("BLOCK" if gr.blocking else "WARN")
        print(f"  [{status}] {gr.gate_id:<20} {gr.message}")
    print()


def demo_budget_context() -> None:
    print("─" * 60)
    print("3. With custom budget_limit context")
    print("─" * 60)

    result = compute_confidence(0.75, 0.70, 0.10, Phase.EXECUTE)
    compiler = GateCompiler()
    gates = compiler.compile_gates(result, context={"budget_limit": 0.60})

    print(f"Compiled {len(gates)} gate(s):")
    for gate in gates:
        print(f"  {gate!r}")
    print()


def demo_extra_gates() -> None:
    print("─" * 60)
    print("4. With extra_gates injected by caller")
    print("─" * 60)

    custom_gate = SafetyGate("domain_specific", GateType.QA, blocking=True, threshold=0.80)
    result = compute_confidence(0.85, 0.80, 0.05, Phase.BIND)
    compiler = GateCompiler()
    gates = compiler.compile_gates(result, context={"extra_gates": [custom_gate]})

    print(f"Compiled {len(gates)} gate(s):")
    for gate in gates:
        print(f"  {gate!r}")
    print()


def demo_phase_comparison() -> None:
    print("─" * 60)
    print("5. Gate count varies by phase")
    print("─" * 60)

    goodness, domain, hazard = 0.80, 0.75, 0.10
    compiler = GateCompiler()

    print(f"{'Phase':<12}  {'Gates':>5}  Gate IDs")
    print("-" * 60)
    for phase in Phase:
        result = compute_confidence(goodness, domain, hazard, phase)
        gates  = compiler.compile_gates(result)
        ids    = ", ".join(g.gate_id for g in gates)
        print(f"{phase.value:<12}  {len(gates):>5}  {ids}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print(" murphy-confidence  |  Gate Compiler Demo")
    print("=" * 60)
    print()
    demo_basic_compile()
    demo_compliance_context()
    demo_budget_context()
    demo_extra_gates()
    demo_phase_comparison()
