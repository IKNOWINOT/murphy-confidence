# Changelog

All notable changes to `murphy-confidence` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-03-29

### Added

- **`murphy_confidence.engine`** — `ConfidenceEngine` and `compute_confidence()`
  implementing the MFGC formula: `C(t) = w_g·G(x) + w_d·D(x) − κ·H(x)`
- **`murphy_confidence.types`** — `Phase`, `GateAction`, `GateType`,
  `ConfidenceResult`, `GateResult` enums and dataclasses
- **`murphy_confidence.gates`** — `SafetyGate` with six gate types
  (EXECUTIVE, OPERATIONS, QA, HITL, COMPLIANCE, BUDGET) and default blocking
  policies
- **`murphy_confidence.compiler`** — `GateCompiler` for dynamic gate synthesis
  from a `ConfidenceResult` and execution context
- **`murphy_confidence.domain`** — Domain-specific sub-models for healthcare,
  financial, manufacturing, and cross-system scenarios
- Phase-locked weight schedules (7 phases: EXPAND → TYPE → ENUMERATE →
  CONSTRAIN → COLLAPSE → BIND → EXECUTE)
- Adaptive phase thresholds (0.50 at EXPAND, 0.85 at EXECUTE)
- Six-tier action classification (PROCEED_AUTOMATICALLY through BLOCK_EXECUTION)
- `py.typed` marker for PEP 561 / mypy / pyright compatibility
- Zero external dependencies — pure Python 3.10+ stdlib only
- Full `as_dict()` serialisation on `ConfidenceResult` and `GateResult`
- Examples: basic scoring, safety gates, gate compiler, FastAPI middleware,
  LangChain callback
- GitHub Actions CI matrix (Python 3.10–3.13)
- GitHub Actions PyPI publish workflow (OIDC trusted publisher)

### Fixed

- Replaced deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)`
  in `engine.py` and `types.py` for Python 3.12+ compatibility

### Notes

- Initial extraction from the
  [Murphy System](https://github.com/IKNOWINOT/Murphy-System) internal
  `strategic/murphy_confidence` package
- Apache-2.0 licensed

[0.1.0]: https://github.com/IKNOWINOT/murphy-confidence/releases/tag/v0.1.0
