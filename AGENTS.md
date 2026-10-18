# Agent instructions

## Always run everything

Before declaring a change done, run the full suite:

```bash
ci/check.sh --full
```

That means all 35 Tcl/Python scripts, all 49 examples, the 29 realworld
pipelines, the documentation checks, WPS and the wheel smoke test. A subset is
fine while developing, but not as the final verification.

For performance changes, run both the old and the new tree through the full
suite, and record the comparison in the handoff notes.
