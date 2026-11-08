# Audit: engine state and parallel Sessions

Scope: `src/surfit`, `src/globe`, `src/freeflow`, `src/sstuff` and
`src/pysurfit`.  Vendored code, generated SWIG wrappers, `minizip` and the Tcl
front end are excluded; Tcl is not a design constraint for this work.

Method: file-scope `static`/`extern` globals, function-level statics that keep
state, mutable singletons, manager ownership and the solver's job arrays.  Each
entry was treated as a candidate for per-task context, not as a style issue.

## Final state

The engine globals and the installed task are **thread-local**.  A `Session`
call installs its `surfit_state` in the calling thread only; the process-wide
`_STATE_LOCK` is gone and each Session has its own re-entrant lock.  A task
built in one thread can be solved in another: every command stores its snapshot
with `state_store()`, and a thread that has no origin yet gets a clone of the
library defaults captured at module initialisation.

Per-task contexts now own:

| Resource | Owner |
|---|---|
| seven data containers, `functionals`, grid, settings, solver scratch | `surfit_state` |
| data manager and its manager list | `surfit_state` (borrowed managers) |
| worker pool, log file/hook, file-search cursor, datafile mode, RNG | `sstuff_state` |
| DEM container and `draw_dem` | `globe_state` |
| freeflow rules | ordinary `surfit_state::functionals`; the manager is a process registration |

The six process-static solver job arrays were the final correctness bug:
`matr_mult_jobs` / `matr_rect_mult_jobs` (`matr.cpp`),
`surf_project_jobs` (`surf_internal.cpp`) and
`axpy_jobs` / `xpay_jobs` / `times_jobs` (`solvers.cpp`) are now
`thread_local`.  Before that, two concurrent solves overwrote each other's job
payloads and the second result was wrong; after it, repeated two-thread stress
matches the solo hashes.

Also thread-local: engine settings (`tol`, `undef_value`, penalty/omega),
`map_name`, `solver_name`, grid/method pointers, `data_manager`, ID/name
counters, mirrored sstuff settings (`cpu`, `loglevel`, `stop_on_error`,
`fileio_append`, `datafile_modE`) and `globe_dems` / `draw_dem`.

## Verification

`test_threadlocal_state.py` covers:

- two area solves in two threads, hashes equal to solo;
- a task whose last command created the grid, solved in another thread;
- Sessions created and solved entirely in worker threads (plugin managers
  available);
- release-while-installed on a reused worker pool;
- DEM/freeflow isolation across threads;
- real overlap (cpu/wall > 1.2 in the two-solve case).

`ci/check.sh --full` passes, including Tcl parity, commands, examples and the
wheel smoke test.

## Remaining limits (not state-correctness bugs)

1. **Per-matrix cache mutexes** in `matr_onesrow.cpp`
   (`matr_onesrow_mutex`, `matr_row_alloc_prev_b_begin`) still serialize the hot
   `mult_line` path.  Two 1-worker solves overlap at about 1.7x, not 2x.
   Per-matrix mutexes would recover the last bit of scaling.
2. **Python log observer** in `src/pysurfit/src/module.cpp` is still a
   process-wide last-wins pointer.  Two concurrent solves can interleave
   callbacks into one observer; results are unaffected.
3. **Per-thread library state**: a thread that creates only a default origin
   keeps a small (~1 KB) clone after it exits.  The task states themselves are
   released by `Session.close()`; this is bounded and documented, not a growing
   per-task leak.
4. **Tcl** remains single-threaded by design; the thread-local externs only keep
   the TCL=ON build compiling.

No silent no-op or shared mutable state addressed by the earlier audit remains
on the solve path.  The honest claim is now **parallel Sessions**, with the
scaling caveat above.
