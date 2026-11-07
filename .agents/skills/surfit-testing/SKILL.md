---
name: surfit-testing
description: >
  Use when adding or fixing tests for surfit: C++/pybind11 behaviour, Python
  API, Tcl/Python parity, examples, numerical recovery, weights, diagnostics,
  metadata or documentation. Produces tests that fail on the old tree, not
  happy-path theatre. Does not introduce a new test framework.
---

# Testing surfit

surfit already has a large, unusual test suite. A new test earns its keep only
if it would have caught a real failure. Match the existing layers; do not add
pytest, GoogleTest, CTest or a coverage service just because another project
uses them.

## First: pick the layer

| What changed | Where the test belongs | Command |
|---|---|---|
| Tcl command or C++ core | `run_tcl_suite.py`, realworld | `ci/check.sh --full` |
| Python binding / Session | `src/pysurfit/tests/test_*.py` | direct + CI |
| Same output from both front ends | `test_parity.py`, `test_examples.py` | direct + CI |
| Numeric recovery | `test_synthetic.py` | direct + CI |
| Weights / per-cell aggregation | `test_weights.py` | direct + CI |
| Residuals / outliers | `test_diagnostics.py` | direct + CI |
| Provenance sidecar | `test_metadata.py` | direct + CI |
| K-fold prediction | `test_cross_validation.py` | direct + CI |
| Docs / figures | `docs/check_docs.py`, `docs/build.sh` | direct + CI |

The current suite is not pytest: test files are standalone scripts with a
`main()`. Keep that style. C++ has no GoogleTest harness; do not add one for a
single fix. The Tcl suite is the C++ integration test.

## Workflow

### 1. Reproduce before writing

Write a failing case on the current tree and record the exact failure. If the
old tree cannot reproduce it, you do not yet know what the bug is. For a
regression, keep the minimal input that triggers it.

### 2. State the behaviour as a table

Before writing code, list:

- inputs and the expected output;
- every branch, early return and error;
- boundary values: empty, single point, all undefined, zero weight, wrong length,
  duplicate cell, name that matches nothing;
- external effects: files, temp dirs, threads, global state, clock, network.

### 3. Write the smallest test that fails

- One behaviour per test; a descriptive name, not `test_case_3`.
- Use a temporary directory; never write into the repo.
- Fixed seed for random data; no sleep and no real network.
- For Python, call the public `Session`/module API, not internals.
- For C++, exercise the pybind boundary if the bug is in the binding; exercise
  the core through the Tcl suite if it is in the engine.
- For a weight or diagnostic test, compare with hand-computed numbers, not with
  the engine's own output.

### 4. Check the test can fail

Temporarily flip the comparison, remove the guard or revert the fix; the new
test must fail. Restore. A test that passes on both trees is documentation, not
a regression test; keep it only if it checks a real invariant.

### 5. Run the neighbourhood, then everything

```bash
export SURFIT_BIN="$PWD/build-ci/bin"
export PYTHONPATH="$SURFIT_BIN"
python3 src/pysurfit/tests/test_<area>.py
./ci/check.sh --full
```

A performance change also needs the old tree through the full suite and an
equal-output check. A docs-only change still needs `docs/check_docs.py` and a
Sphinx `-W` build.

## surfit-specific cases that are usually missed

- `Session()` before loading data; a loader called before it is wiped.
- `task.names()` is surfaces; areas are `area_size()` / `area_getName("*")`.
- `area_leq/geq` on a missing name return `[]`; assert that miss is handled.
- Grid shape and orientation: `(count_y, count_x)`, row 0 at `min_y`.
- Undefined = `FLT_MAX`; use `defined_mask`.
- Weights: `[1,3]`, `[0,1]`, wrong length, all-zero.
- Diagnostic prediction: nearest node, not bilinear.
- Metadata: JSON sidecar survives and is not confused with reprojection.
- Tcl and Python both read the same file; byte equality matters.
- Two Sessions or two threads must give the same result as a solo run.

## Anti-patterns

- Do not test only the happy path.
- Do not assert on log text when the numeric result is observable.
- Do not tighten a tolerance until a flaky test passes; find the nondeterminism.
- Do not add a new framework or a coverage service for one test.
- Do not mark a test skipped because the full suite is slow; fix the test or
  move it to the documented integration layer.
- Do not call a test "passed" if `ci/check.sh --full` was not run.

## Sources

The strongest parts are adapted from
[test-forge](https://github.com/Hahaknight/claude-skills-pro/blob/main/free-skills/test-forge/SKILL.md)
(failure-first, mutation check, no new framework) and
[cpp-testing](https://github.com/marshall0524/everythingclaudecode/blob/main/skills/cpp-testing/SKILL.md)
(isolation, flakiness and sanitizer discipline). The GoogleTest/CTest specifics
of `cpp-testing` do **not** apply here: surfit's C++ checks run through the Tcl
and Python suites.
