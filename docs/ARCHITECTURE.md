# Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
# Created by: Corey Post

# Architecture: murphy-confidence

## Overview

`murphy-confidence` implements the **Multi-Factor Generative-Deterministic
Confidence (MFGC)** scoring system — a mathematically grounded approach to
answering the question every autonomous AI agent must face:

> *"Am I confident enough to act?"*

The library is extracted from the **Murphy System**, a larger autonomous AI
orchestration platform.  It is designed to be embedded in any AI pipeline,
agent framework, or execution environment that needs a principled, auditable
confidence gate.

---

## The MFGC Formula

```
C(t) = w_g · G(x) + w_d · D(x) − κ · H(x)
```

| Symbol | Name | Range | Description |
|--------|------|-------|-------------|
| `C(t)` | Confidence score | [0, 1] | Final output — the single number the gate reads |
| `G(x)` | Generative quality score | [0, 1] | How good is the generative output? (LLM quality, coherence, completeness) |
| `D(x)` | Domain-deterministic score | [0, 1] | How well does the action match domain rules, constraints, and history? |
| `H(x)` | Hazard/risk factor | [0, 1] | How dangerous is the action if wrong? (irreversibility, blast radius) |
| `w_g`  | Generative weight | — | Phase-locked; decreases toward EXECUTE |
| `w_d`  | Domain weight | — | Phase-locked; increases toward EXECUTE |
| `κ`    | Hazard penalty multiplier | — | Phase-locked; increases toward EXECUTE |

**Key insight**: as execution approaches, the formula shifts weight *away* from
the LLM's generative quality and *toward* deterministic domain knowledge —
because by EXECUTE phase, you should be relying on facts, not vibes.

---

## Phase-Locked Weight Schedules

The weight schedule is the heart of the system.  It enforces that the engine
becomes progressively more conservative as the pipeline advances:

| Phase | w_g | w_d | κ | Threshold |
|-------|-----|-----|---|-----------|
| EXPAND | 0.60 | 0.30 | 0.10 | 0.50 |
| TYPE | 0.55 | 0.35 | 0.10 | 0.55 |
| ENUMERATE | 0.50 | 0.40 | 0.10 | 0.60 |
| CONSTRAIN | 0.40 | 0.45 | 0.15 | 0.65 |
| COLLAPSE | 0.35 | 0.50 | 0.15 | 0.70 |
| BIND | 0.30 | 0.55 | 0.15 | 0.78 |
| EXECUTE | 0.25 | 0.55 | 0.20 | 0.85 |

**Rationale**: Early phases (EXPAND, TYPE) are exploratory.  A low-confidence
generative output is acceptable when you are brainstorming.  By EXECUTE, you
are about to take an irreversible real-world action.  At that point, you need
deterministic validation and a low hazard score — or the action is blocked.

---

## Six-Tier Action Classification

After computing `C(t)`, the score is mapped to one of six action tiers:

| Tier | Threshold | Description |
|------|-----------|-------------|
| `PROCEED_AUTOMATICALLY` | ≥ 0.90 | Full autonomy — execute immediately |
| `PROCEED_WITH_MONITORING` | ≥ 0.80 | Execute, but log everything |
| `PROCEED_WITH_CAUTION` | ≥ 0.70 | Execute with additional checks |
| `REQUEST_HUMAN_REVIEW` | ≥ 0.55 | Flag for human but do not block |
| `REQUIRE_HUMAN_APPROVAL` | ≥ 0.40 | Block until human approves |
| `BLOCK_EXECUTION` | < 0.40 | Hard stop |

Note that the phase threshold is applied *independently* of these tiers:
if `C(t) ≥ tier_threshold` but `C(t) < phase_threshold`, the action is
downgraded to `REQUIRE_HUMAN_APPROVAL` even if the tier says "proceed."

---

## Safety Gates

A `SafetyGate` wraps a gate type, a blocking flag, and a threshold.  It
evaluates a `ConfidenceResult` and produces a `GateResult`.

### Default gate thresholds

| Gate Type | Default Threshold | Blocking by Default |
|-----------|------------------|---------------------|
| EXECUTIVE | 0.85 | Yes |
| OPERATIONS | 0.70 | No |
| QA | 0.75 | No |
| HITL | 0.80 | Yes |
| COMPLIANCE | 0.90 | Yes |
| BUDGET | 0.65 | No |

### Blocking semantics

When a **blocking** gate fails:
- The `GateResult.action` is set to `BLOCK_EXECUTION`
- The caller must halt the pipeline

When a **non-blocking** gate fails:
- The `GateResult.action` is set to `REQUIRE_HUMAN_APPROVAL`
- Execution may continue but should be annotated

---

## Gate Compiler

The `GateCompiler` synthesises the right set of gates from a `ConfidenceResult`
and optional context.  It implements a rule table:

| Condition | Gate Added |
|-----------|-----------|
| Always | `ops` (OPERATIONS, non-blocking) |
| Phase = EXECUTE | `qa_execute` (QA, threshold=0.80, non-blocking) |
| Action = BLOCK_EXECUTION | `exec_block` (EXECUTIVE, blocking) |
| Action = REQUIRE_HUMAN_APPROVAL | `exec_hitl` (HITL, blocking) |
| Action = REQUEST_HUMAN_REVIEW | `exec_review` (HITL, threshold=0.70, non-blocking) |
| Phase = EXECUTE + proceed actions | `budget_exec` (BUDGET, non-blocking or blocking) |
| Context: `compliance_required=True` | `compliance` (COMPLIANCE, blocking) |
| Context: `budget_limit=N` | `budget_ctx` (BUDGET, threshold=N) |
| Context: `extra_gates=[...]` | caller-supplied gates appended |

---

## Domain Models

The `murphy_confidence.domain` sub-package provides vertical-specific scorers
that compute specialised `G(x)`, `D(x)`, and `H(x)` values:

### Healthcare (`domain.healthcare`)

- `DrugInteractionScorer` — cross-reference drug pairs against interaction databases
- `AllergyCrossReference` — patient allergy vs. prescribed medication
- `FHIRAdapter` — bridges FHIR R4 patient records to domain scores
- `LongitudinalHistoryScorer` — weighs recent vs. historical patient data
- `PaediatricDosingModel` — age/weight-adjusted dosing hazard computation
- `HealthcareDomainEngine` — combines all sub-models into a single G/D/H triple

### Financial (`domain.financial`)

- `MarketLiquidityScorer` — integrates real-time liquidity into D(x)
- `RegulatoryMapper` — cross-border mapping (MiFID II, SEC, etc.)
- `WashTradeDetector` — pattern-based hazard sub-model
- `CounterpartyCreditScorer` — live credit risk → H(x)
- `IntradayPositionLimiter` — budget gate threshold computation
- `DarkPoolComplianceChecker` — order routing compliance rules
- `FinancialDomainEngine` — composite domain engine

### Manufacturing (`domain.manufacturing`)

- `OPCUAStreamAdapter` — real-time OPC-UA sensor data → G(x)
- `MultiSensorFusion` — Kalman-filter style sensor fusion
- `PredictiveMaintenanceModel` — failure probability → H(x)
- `SIL2CertificationMapper` — IEC 61511 SIL-2 safety requirements
- `HumanPresenceDetector` — safety zone occupancy → H(x) spike
- `DynamicHazardRecalibrator` — adaptive recalibration on anomaly detection
- `ManufacturingDomainEngine` — composite domain engine

### Cross-System (`domain.cross_system`)

- `IntegrationTestRunner` — runs all domain engines against a common test matrix
- `PerformanceBenchmark` — latency and throughput benchmarks for the MFGC formula
- `AdversarialRobustnessTester` — edge-case and adversarial input testing
- `MultiTenantIsolationVerifier` — validates per-tenant gate isolation
- `GateCompilerLoadTester` — stress-tests the compiler under concurrent load

---

## Design Principles

1. **Zero external dependencies** — the entire package is pure Python stdlib.
   No NumPy, no Pandas, no LangChain.  Import it anywhere.

2. **Stateless core** — `ConfidenceEngine.compute()` is a pure function.
   No global state, no singleton, no database.  Thread-safe by construction.

3. **Composable** — use just the engine, or layer on gates, or use the
   compiler.  Each layer is independently useful.

4. **Auditable** — every `ConfidenceResult` carries a `rationale` string that
   fully explains the decision: phase, score, threshold, weights, inputs.

5. **Type-safe** — full `py.typed` marker, complete type annotations, PEP 561
   compliant.  Works with mypy and pyright out of the box.

---

## Relationship to Murphy System

`murphy-confidence` is extracted from the
[Murphy System](https://github.com/IKNOWINOT/Murphy-System) — a full
autonomous AI orchestration platform that uses this library as its central
decision gate at every stage of its 7-phase execution pipeline.

In the full system, the `ConfidenceEngine` is wired to:
- The **Human-in-the-Loop (HITL) controller** — which arms/disarms human
  oversight based on confidence trends over time
- The **Campaign orchestrator** — which gates every automated marketing action
  through a confidence + compliance check before execution
- The **CEO Branch** — the autonomous decision maker that uses confidence
  scores to decide whether to escalate to human review
- The **Self-healing immune engine** — which uses confidence drops as a signal
  to trigger recovery workflows

The standalone `murphy-confidence` package exposes the scoring engine and
gate system so any AI project can benefit from principled confidence gating
without adopting the full Murphy System.
