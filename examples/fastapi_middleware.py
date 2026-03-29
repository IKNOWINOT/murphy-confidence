# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

"""
examples/fastapi_middleware.py
==============================
A FastAPI middleware that runs every AI agent action through the
murphy-confidence scoring engine before allowing execution.

Demonstrates a real-world integration pattern: intercept, score, gate.

Requirements:
    pip install fastapi uvicorn

Run:
    uvicorn examples.fastapi_middleware:app --reload
"""

from __future__ import annotations

import json
import time
from typing import Any, Callable, Dict

try:
    from fastapi import FastAPI, HTTPException, Request, Response
    from fastapi.responses import JSONResponse
except ImportError:  # pragma: no cover
    raise SystemExit(
        "FastAPI not installed. Run: pip install fastapi uvicorn"
    )

from murphy_confidence import GateCompiler, compute_confidence
from murphy_confidence.types import GateAction, Phase

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Agent Action API",
    description="Example: every action is confidence-scored before execution",
)

compiler = GateCompiler()


# ---------------------------------------------------------------------------
# Confidence-gating middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def confidence_gate_middleware(request: Request, call_next: Callable) -> Response:
    """
    Score every POST to /agent/action before allowing it through.

    The request body must contain:
        {
          "goodness": 0.0-1.0,
          "domain":   0.0-1.0,
          "hazard":   0.0-1.0,
          "phase":    "EXECUTE" | "BIND" | ... (optional, defaults to EXECUTE)
        }

    If the gate blocks, returns HTTP 403 with the gate failure detail.
    """
    if request.method == "POST" and request.url.path == "/agent/action":
        body_bytes = await request.body()

        try:
            body: Dict[str, Any] = json.loads(body_bytes)
        except (json.JSONDecodeError, ValueError):
            return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

        goodness = float(body.get("goodness", 0.5))
        domain   = float(body.get("domain",   0.5))
        hazard   = float(body.get("hazard",   0.5))
        phase_str = body.get("phase", "EXECUTE").upper()

        try:
            phase = Phase[phase_str]
        except KeyError:
            return JSONResponse(
                {"error": f"Unknown phase: {phase_str}. Valid: {[p.value for p in Phase]}"},
                status_code=400,
            )

        # Score the action
        result = compute_confidence(goodness, domain, hazard, phase)

        # Compile and evaluate gates
        gates = compiler.compile_gates(result, context={"compliance_required": True})
        blocking_failures = []
        for gate in gates:
            gr = gate.evaluate(result)
            if not gr.passed and gr.blocking:
                blocking_failures.append(gr.as_dict())

        if blocking_failures:
            return JSONResponse(
                {
                    "blocked": True,
                    "confidence": result.score,
                    "action": result.action.value,
                    "rationale": result.rationale,
                    "blocking_gates": blocking_failures,
                },
                status_code=403,
            )

        # Attach scoring info to request state so the route handler can read it
        request.state.confidence_result = result

    return await call_next(request)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

@app.post("/agent/action")
async def execute_agent_action(request: Request) -> Dict[str, Any]:
    """
    This endpoint is only reached if the middleware allowed the action.
    The confidence result is available via request.state.confidence_result.
    """
    result = getattr(request.state, "confidence_result", None)
    return {
        "executed": True,
        "confidence": result.score if result else None,
        "action": result.action.value if result else None,
        "rationale": result.rationale if result else None,
        "message": "Agent action executed successfully.",
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Example: calling this API from Python (run in a second terminal)
# ---------------------------------------------------------------------------

def _example_client() -> None:  # pragma: no cover
    """Demonstrates how to call the middleware-protected endpoint."""
    import urllib.request

    url = "http://127.0.0.1:8000/agent/action"

    cases = [
        ("High confidence",  {"goodness": 0.92, "domain": 0.88, "hazard": 0.03, "phase": "EXECUTE"}),
        ("Medium confidence", {"goodness": 0.72, "domain": 0.68, "hazard": 0.18, "phase": "EXECUTE"}),
        ("Low confidence",   {"goodness": 0.45, "domain": 0.40, "hazard": 0.45, "phase": "EXECUTE"}),
    ]

    for label, payload in cases:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                body = json.loads(resp.read())
                print(f"[{label}] 200 OK — {body['action']}")
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
            print(f"[{label}] {e.code} BLOCKED — gates: {[g['gate_id'] for g in body['blocking_gates']]}")


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    uvicorn.run("examples.fastapi_middleware:app", host="127.0.0.1", port=8000, reload=True)
