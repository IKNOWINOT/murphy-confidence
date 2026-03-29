# Contributing to murphy-confidence

Thank you for your interest in contributing!  This guide will get you set up
in minutes.

---

## Development setup

```bash
# 1. Fork and clone the repository
git clone https://github.com/<your-username>/murphy-confidence.git
cd murphy-confidence

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install the package in editable mode
pip install -e .

# 4. Run the test suite
python -m pytest tests/ -v
```

That's it.  There are **no external dependencies** — not even for development.

---

## Running the examples

```bash
python examples/basic_scoring.py
python examples/safety_gates.py
python examples/gate_compiler.py
python examples/langchain_callback.py   # no LangChain required for the demo
```

---

## Pull request guidelines

1. **One thing per PR** — focused changes are easier to review and merge.
2. **Add tests** — every new behaviour should have a corresponding test in
   `tests/test_engine.py` or `tests/test_gates.py`.  The test suite uses
   only `unittest` (stdlib) — no pytest plugins required.
3. **Keep it zero-dependency** — the core `murphy_confidence` package must
   never import anything outside the Python stdlib.
4. **Match the copyright header** — every `.py` file must start with:
   ```python
   # Copyright © 2020-2026 Inoni Limited Liability Company. All rights reserved.
   # Created by: Corey Post
   ```
5. **Run tests before opening the PR**:
   ```bash
   python -m pytest tests/ -v
   ```
6. **Describe your change** in the PR description — what problem does it
   solve, what did you change, and why?

---

## Reporting bugs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).
Please include a minimal reproduction — the smaller the better.

## Suggesting features

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.yml).

---

## Code style

- Follow PEP 8.
- Use type annotations everywhere.
- Keep line length ≤ 100 characters.
- No external formatters are required, but your code should be readable.

---

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE).
