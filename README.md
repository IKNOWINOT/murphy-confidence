<!-- Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved. -->
<!-- Created by: Corey Post -->

<div align="center">

# murphy-confidence

**Should your AI agent act? `murphy-confidence` answers that question with math, not vibes.**

[![PyPI version](https://img.shields.io/pypi/v/murphy-confidence?color=blue&label=PyPI)](https://pypi.org/project/murphy-confidence/)
[![Python versions](https://img.shields.io/pypi/pyversions/murphy-confidence)](https://pypi.org/project/murphy-confidence/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![CI](https://github.com/IKNOWINOT/murphy-confidence/actions/workflows/ci.yml/badge.svg)](https://github.com/IKNOWINOT/murphy-confidence/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/pypi/dm/murphy-confidence)](https://pypi.org/project/murphy-confidence/)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/IKNOWINOT?label=Sponsors)](https://github.com/sponsors/IKNOWINOT)

Zero dependencies · Pure Python 3.10+ · `pip install murphy-confidence`

</div>

---

## The problem

Every AI agent framework gives you a way to *call* tools.  None of them give
you a principled way to decide *whether* to call them.

You end up with one of:
- **A hardcoded threshold** — `if confidence > 0.7: execute()` — no phase
  awareness, no hazard weighting, no audit trail
- **A vibe check** — asking the LLM "are you sure?" and hoping it says no
  when it should
- **Nothing** — just letting the agent do whatever it calculates and hoping
  for the best

When you're automating actions that touch real data, real money, or real
people, none of those options are acceptable.

---

## The solution

`murphy-confidence` implements the **Multi-Factor Generative-Deterministic
Confidence (MFGC)** formula:

```
C(t) = w_g · G(x) + w_d · D(x) − κ · H(x)
```

Where:

| Symbol | Meaning | Range |
|--------|---------|-------|
| `G(x)` | Generative quality score — how good is the LLM output? | [0, 1] |
| `D(x)` | Domain-deterministic score — does this match the rules? | [0, 1] |
| `H(x)` | Hazard factor — how bad if this is wrong? | [0, 1] |
| `w_g, w_d, κ` | Phase-locked weights — shift toward determinism as execution approaches | — |

The weights are **phase-locked**: as your pipeline moves from brainstorming
to executing, the formula automatically shifts trust away from the LLM and
toward your domain rules.  At `EXECUTE` phase, the threshold is 0.85.  At
`EXPAND` phase, it's 0.50.

---

## 5-second quickstart

```bash
pip install murphy-confidence
```

```python
from murphy_confidence import compute_confidence
from murphy_confidence.types import Phase

result = compute_confidence(
    goodness=0.82,   # How good is the AI output?  [0-1]
    domain=0.75,     # How well does it match domain rules?  [0-1]
    hazard=0.10,     # How risky is this action?  [0-1]
    phase=Phase.EXECUTE,
)

print(result.score)    # 0.7585
print(result.action)   # GateAction.PROCEED_WITH_MONITORING
print(result.allowed)  # True
print(result.rationale)
# [ALLOWED] Phase=EXECUTE | C=0.7585 (threshold=0.85) | Action=PROCEED_WITH_MONITORING | ...
```

---

## Complete feature walkthrough

### The Confidence Engine

The engine is stateless.  Call it anywhere, in any thread, with any inputs:

```python
from murphy_confidence import ConfidenceEngine
from murphy_confidence.types import Phase

engine = ConfidenceEngine()

# Low hazard, high quality — proceeds automatically at EXECUTE
result = engine.compute(goodness=0.95, domain=0.90, hazard=0.02, phase=Phase.EXECUTE)
assert result.action.value == "PROCEED_AUTOMATICALLY"

# High hazard — blocked even with good quality
result = engine.compute(goodness=0.90, domain=0.85, hazard=0.80, phase=Phase.EXECUTE)
assert not result.allowed
```

The phase-locked weight schedule means the same inputs produce different
outcomes at different phases — early phases are lenient, EXECUTE is strict:

| Phase | Score (goodness=0.78, domain=0.72, hazard=0.15) | Allowed |
|-------|--------------------------------------------------|---------|
| EXPAND | 0.6570 | ✓ |
| TYPE | 0.6410 | ✓ |
| ENUMERATE | 0.6250 | ✓ |
| CONSTRAIN | 0.6045 | ✓ |
| COLLAPSE | 0.5885 | ✓ |
| BIND | 0.5745 | ✗ |
| EXECUTE | 0.5555 | ✗ |

### Safety Gates

Gates wrap a confidence result in a domain-specific policy check:

```python
from murphy_confidence import SafetyGate
from murphy_confidence.types import GateType

# A compliance gate at 0.90 — blocking by default
gate = SafetyGate("hipaa_compliance", GateType.COMPLIANCE)

result = compute_confidence(0.82, 0.78, 0.08, Phase.EXECUTE)
gr = gate.evaluate(result)

if not gr.passed and gr.blocking:
    raise RuntimeError(gr.message)
    # Gate 'hipaa_compliance' (COMPLIANCE) FAILED [BLOCKING] — confidence 0.7368 < threshold 0.9000
```

Six gate types, each with sensible defaults:

| Gate Type | Default Threshold | Blocking |
|-----------|------------------|----------|
| `EXECUTIVE` | 0.85 | ✓ |
| `OPERATIONS` | 0.70 | ✗ |
| `QA` | 0.75 | ✗ |
| `HITL` | 0.80 | ✓ |
| `COMPLIANCE` | 0.90 | ✓ |
| `BUDGET` | 0.65 | ✗ |

### Gate Compiler

Don't know which gates you need?  The compiler figures it out:

```python
from murphy_confidence import GateCompiler, compute_confidence
from murphy_confidence.types import Phase

result = compute_confidence(0.72, 0.68, 0.18, Phase.EXECUTE)
compiler = GateCompiler()
gates = compiler.compile_gates(result, context={"compliance_required": True})

for gate in gates:
    gr = gate.evaluate(result)
    print(f"{gr.gate_id}: {'PASS' if gr.passed else 'FAIL'}")
```

The compiler uses a rule table that maps `(phase, action)` pairs to gate
sets — so the right gates are automatically included for EXECUTE phase, for
blocking actions, for compliance contexts, etc.

### Domain Models

For vertical-specific scoring, the `domain` sub-package provides ready-made
scorers for healthcare, financial, and manufacturing scenarios:

```python
from murphy_confidence.domain.healthcare import HealthcareDomainEngine
from murphy_confidence import compute_confidence
from murphy_confidence.types import Phase

engine = HealthcareDomainEngine()
g, d, h = engine.compute(patient_record, prescription)

result = compute_confidence(g, d, h, Phase.EXECUTE)
```

---

## Integration examples

### FastAPI middleware

Gate every AI agent action before it hits your handler:

```python
from fastapi import FastAPI, Request
from murphy_confidence import GateCompiler, compute_confidence
from murphy_confidence.types import Phase

app = FastAPI()
compiler = GateCompiler()

@app.middleware("http")
async def confidence_gate(request: Request, call_next):
    if request.url.path == "/agent/action":
        body = await request.json()
        result = compute_confidence(
            body["goodness"], body["domain"], body["hazard"], Phase.EXECUTE
        )
        gates = compiler.compile_gates(result, context={"compliance_required": True})
        for gate in gates:
            gr = gate.evaluate(result)
            if not gr.passed and gr.blocking:
                return JSONResponse({"blocked": True, "reason": gr.message}, status_code=403)
    return await call_next(request)
```

See [`examples/fastapi_middleware.py`](examples/fastapi_middleware.py) for the
full runnable example.

### LangChain callback

Intercept every tool call and gate it:

```python
from murphy_confidence import GateCompiler, compute_confidence
from murphy_confidence.types import Phase

class MurphyConfidenceCallback:
    def on_tool_start(self, serialized, input_str, **kwargs):
        result = compute_confidence(
            kwargs.get("goodness", 0.70),
            kwargs.get("domain", 0.65),
            kwargs.get("hazard", 0.15),
            Phase.EXECUTE,
        )
        gates = GateCompiler().compile_gates(result)
        for gate in gates:
            gr = gate.evaluate(result)
            if not gr.passed and gr.blocking:
                raise RuntimeError(f"Tool blocked: {gr.message}")
```

See [`examples/langchain_callback.py`](examples/langchain_callback.py) for the
full runnable example (no LangChain install required for the demo).

### Raw Python

```python
from murphy_confidence import compute_confidence, SafetyGate
from murphy_confidence.types import GateType, Phase

# Score the action
result = compute_confidence(
    goodness=0.88,
    domain=0.82,
    hazard=0.05,
    phase=Phase.EXECUTE,
)

# Create a domain-specific gate
gate = SafetyGate("production_deploy", GateType.EXECUTIVE, blocking=True)
gr = gate.evaluate(result)

if gr.passed:
    deploy_to_production()
else:
    notify_human(gr.message)
```

---

## Why not just use a threshold?

A simple `if confidence > 0.7: proceed` has four failure modes that
`murphy-confidence` fixes:

| Problem | Simple threshold | murphy-confidence |
|---------|-----------------|-------------------|
| Same threshold at brainstorm and execute | ✗ both same | ✓ 0.50 → 0.85 ramp |
| No hazard awareness | ✗ ignored | ✓ κ · H(x) penalty |
| No domain validation | ✗ only LLM score | ✓ w_d · D(x) component |
| No audit trail | ✗ silent pass/fail | ✓ rationale string on every result |
| No gate composition | ✗ one boolean | ✓ gate pipeline with blocking semantics |
| No serialisation | ✗ raw float | ✓ `as_dict()` on all results |

---

## Part of Murphy System

`murphy-confidence` is extracted from the
[Murphy System](https://github.com/IKNOWINOT/Murphy-System) — a full
autonomous AI orchestration platform featuring:

- 🧠 **Multi-agent architecture** — CEO Branch, campaign orchestrator, 90+
  platform connectors
- 🛡️ **HITL autonomy controller** — policy-based arm/disarm with graduation
  from supervised to autonomous operation
- 🔄 **Self-healing immune engine** — detects failures, remembers them,
  prevents recurrence
- 📡 **Event backbone** — production-grade pub/sub with circuit breakers,
  dead letter queue, and exponential backoff retry
- 🏭 **Industrial connectors** — OPC-UA, BACnet, SCADA adapters

**murphy-confidence is the gating layer that every decision in Murphy
passes through.**  If you find this library useful, check out the full
system at [github.com/IKNOWINOT/Murphy-System](https://github.com/IKNOWINOT/Murphy-System).

---

## Pipeline phases

| Phase | Description | Threshold |
|-------|-------------|-----------|
| `EXPAND` | Brainstorming, ideation | 0.50 |
| `TYPE` | Classifying and labelling | 0.55 |
| `ENUMERATE` | Listing options | 0.60 |
| `CONSTRAIN` | Applying rules and limits | 0.65 |
| `COLLAPSE` | Selecting the best option | 0.70 |
| `BIND` | Binding to specific resources | 0.78 |
| `EXECUTE` | Taking real-world action | 0.85 |

---

## Action classification

| Action | Score range | Meaning |
|--------|-------------|---------|
| `PROCEED_AUTOMATICALLY` | ≥ 0.90 | Full autonomy |
| `PROCEED_WITH_MONITORING` | ≥ 0.80 | Execute + log |
| `PROCEED_WITH_CAUTION` | ≥ 0.70 | Execute with extra checks |
| `REQUEST_HUMAN_REVIEW` | ≥ 0.55 | Flag for human, don't block |
| `REQUIRE_HUMAN_APPROVAL` | ≥ 0.40 | Block until approved |
| `BLOCK_EXECUTION` | < 0.40 | Hard stop |

---

## Community

- 💬 [Discussions](https://github.com/IKNOWINOT/murphy-confidence/discussions)
  — questions, ideas, show-and-tell
- 🐛 [Issues](https://github.com/IKNOWINOT/murphy-confidence/issues) — bugs
  and feature requests
- 🤝 [Contributing](CONTRIBUTING.md) — how to contribute
- ❤️ [Sponsor](https://github.com/sponsors/IKNOWINOT) — support the project

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

Copyright © 2020-2026 Inoni Limited Liability Company (Corey Post)

<!-- SEO: ai safety confidence scoring ai agents autonomous agent guardrails
human-in-the-loop llm safety gates mfgc murphy confidence python zero-dependency
agent framework fastapi langchain ai agent gating trust scoring -->
