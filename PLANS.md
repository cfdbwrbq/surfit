# Plans

## Layered surface systems

The product roadmap is in [ROADMAP.md](ROADMAP.md); the design detail is in
[SURFACE_STACK_PLAN.md](SURFACE_STACK_PLAN.md).
 The validation gate is specified in
[STACK_VALIDATION_PLAN.md](STACK_VALIDATION_PLAN.md).


The generalisation plan from one surface to an ordered surface stack is in
[SURFACE_STACK_PLAN.md](SURFACE_STACK_PLAN.md).  It covers array/raster
ingestion, group-aware validation, stack orchestration and calibrated
uncertainty without adding a second solver.

## Competitive review

The 2026 review of Surfer, Topo to Raster/ANUDEM, RockWorks, Leapfrog, the
open-source GIS/geostatistics stack and the interpolation literature, with a
prioritised feature plan, is in
[COMPETITIVE_ANALYSIS.md](COMPETITIVE_ANALYSIS.md).

## Deferred

### Agent-first (AI-first) repository

Not part of the current release; do this **later**, after the current work.

The direction is to make the repository self-describing for agents instead of
relying on conversation history:

- keep [.agents/skills/surfit/SKILL.md](.agents/skills/surfit/SKILL.md) as the
  usage entry point and keep it current when new traps are found;
- keep build, test and release procedures in `AGENTS.md` / `HANDOFF.md`, not in
  the usage skill — the two scopes must not mix;
- add a small, machine-readable map of the tree and the commands an agent needs
  (build, full suite, docs, release gate);
- link the Python API traps in the docs from that map so the same rule is not
  maintained in two places.

### Keep the usage skill growing

While the skill is new, every new surfit usage trap goes into the skill and,
when it is user-facing, into `docs/en/python.rst` and `docs/ru/python.rst`.
This is an ongoing task, not a one-time document.
