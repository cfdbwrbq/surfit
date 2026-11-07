# Agent instructions

## Silent mode: no pushes

While an experiment is silent, do not push anywhere: no `git push`, no tags,
no releases, no remote branch updates. Commit locally if needed, keep the
remote untouched, and wait for an explicit request before publishing.

## Always run everything

Before declaring a change done, run the full suite:

```bash
ci/check.sh --full
```

That means all 35 Tcl/Python scripts, all 49 examples, the 29 realworld
pipelines, the analytic injection-recovery check, the per-point weight,
residual/outlier-diagnostic, provenance-metadata, cross-validation and
bootstrap-uncertainty, robust-IRLS, strict-rule, GeoTIFF and out-of-core tiled checks, the
documentation checks, WPS and the wheel smoke test. A subset is
fine while developing, but not as the final verification.

For performance changes, run both the old and the new tree through the full
suite, and record the comparison in the handoff notes.

## Plans

Deferred direction and the agent-first notes are in [PLANS.md](PLANS.md).
