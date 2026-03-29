# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
examples/langchain_callback.py
==============================
A LangChain callback handler that gates tool execution using
murphy-confidence scoring.  Every time LangChain calls a tool, the
handler scores the action and raises ToolExecutionBlockedError if
the confidence gates do not pass.

Requirements:
    pip install langchain langchain-openai

This file is runnable as a standalone demo without LangChain installed
— it prints a simulation trace instead.

Run:
    python examples/langchain_callback.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from murphy_confidence import GateCompiler, compute_confidence
from murphy_confidence.types import GateAction, Phase

compiler = GateCompiler()


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ToolExecutionBlockedError(RuntimeError):
    """Raised when a blocking safety gate prevents a tool from running."""

    def __init__(self, tool_name: str, score: float, gates: List[Dict[str, Any]]) -> None:
        self.tool_name = tool_name
        self.score     = score
        self.gates     = gates
        super().__init__(
            f"Tool '{tool_name}' blocked by confidence gate "
            f"(score={score:.4f}, failed_gates={[g['gate_id'] for g in gates]})"
        )


# ---------------------------------------------------------------------------
# murphy-confidence callback handler
# ---------------------------------------------------------------------------

class MurphyConfidenceCallback:
    """
    LangChain-compatible callback handler that gates tool execution.

    How to use with LangChain::

        from langchain_openai import ChatOpenAI
        from langchain.agents import AgentExecutor

        callback = MurphyConfidenceCallback(
            default_phase=Phase.EXECUTE,
            compliance_required=True,
        )
        agent = AgentExecutor(agent=..., tools=..., callbacks=[callback])

    When ``on_tool_start`` fires, the handler:
        1. Extracts or estimates confidence inputs from the tool input
        2. Scores using compute_confidence()
        3. Compiles and evaluates gates
        4. Raises ToolExecutionBlockedError if any blocking gate fails
    """

    def __init__(
        self,
        default_phase: Phase = Phase.EXECUTE,
        compliance_required: bool = False,
        goodness_default: float = 0.70,
        domain_default: float = 0.65,
        hazard_default: float = 0.15,
    ) -> None:
        self.default_phase        = default_phase
        self.compliance_required  = compliance_required
        self.goodness_default     = goodness_default
        self.domain_default       = domain_default
        self.hazard_default       = hazard_default
        self._last_result: Optional[Any] = None

    # --- LangChain callback interface -------------------------------------

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Called by LangChain before a tool executes."""
        tool_name = serialized.get("name", "unknown_tool")

        # In production you would derive goodness/domain/hazard from
        # real context — agent state, tool type, upstream outputs, etc.
        # Here we use caller-supplied kwargs or fall back to defaults.
        goodness = float(kwargs.get("goodness", self.goodness_default))
        domain   = float(kwargs.get("domain",   self.domain_default))
        hazard   = float(kwargs.get("hazard",   self.hazard_default))
        phase    = kwargs.get("phase", self.default_phase)

        result = compute_confidence(goodness, domain, hazard, phase)
        self._last_result = result

        ctx = {"compliance_required": self.compliance_required}
        gates = compiler.compile_gates(result, context=ctx)

        blocking_failures = []
        for gate in gates:
            gr = gate.evaluate(result)
            if not gr.passed and gr.blocking:
                blocking_failures.append(gr.as_dict())

        if blocking_failures:
            raise ToolExecutionBlockedError(tool_name, result.score, blocking_failures)

        # If we get here, all blocking gates passed
        print(
            f"[MurphyConfidence] Tool '{tool_name}' ALLOWED — "
            f"score={result.score:.4f} action={result.action.value}"
        )

    def on_tool_end(self, output: str, **kwargs: Any) -> None:
        """Called by LangChain after a tool completes."""
        pass

    def on_tool_error(
        self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any
    ) -> None:
        """Called by LangChain when a tool raises an exception."""
        pass

    @property
    def last_confidence_result(self) -> Optional[Any]:
        """The most recent ConfidenceResult produced by this callback."""
        return self._last_result


# ---------------------------------------------------------------------------
# Simulation demo (no LangChain required)
# ---------------------------------------------------------------------------

def simulate() -> None:
    """Simulate what happens when LangChain calls on_tool_start."""
    print("=" * 62)
    print(" murphy-confidence  |  LangChain Callback Demo (simulated)")
    print("=" * 62)
    print()

    callback = MurphyConfidenceCallback(
        default_phase=Phase.EXECUTE,
        compliance_required=True,
    )

    scenarios = [
        ("web_search",    {"goodness": 0.88, "domain": 0.82, "hazard": 0.05}),
        ("send_email",    {"goodness": 0.75, "domain": 0.70, "hazard": 0.20}),
        ("delete_record", {"goodness": 0.50, "domain": 0.45, "hazard": 0.55}),
        ("read_file",     {"goodness": 0.92, "domain": 0.90, "hazard": 0.02}),
    ]

    for tool_name, scores in scenarios:
        print(f"Tool: {tool_name}")
        try:
            callback.on_tool_start(
                {"name": tool_name},
                input_str="(simulated input)",
                **scores,
            )
            print(f"  → Execution proceeds.")
        except ToolExecutionBlockedError as exc:
            print(f"  [BLOCKED] {exc}")
        print()


if __name__ == "__main__":
    simulate()
