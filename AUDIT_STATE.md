# Audit: state that is not per-session

Scope: `src/surfit`, `src/globe`, `src/freeflow`, `src/sstuff` and
`src/pysurfit`.  Vendored code, generated SWIG wrappers, `minizip` and the Tcl
front end are excluded; Tcl is no longer a design constraint for this work.

Method: file-scope `static`/`extern` globals, function-level statics that keep
state, mutable singletons, and the ownership of the managers in `surfit_state`.
Each entry is a candidate for a real per-session context, not a style issue.

## Already per session

`surfit_state` owns the seven containers, `functionals`, the target grid,
settings, solver scratch, a `data_manager` with a borrowed manager list and an
`sstuff_state`.  `sstuff_state` owns the worker pool, log file/hook, file-search
cursor, datafile mode and RNG; `globe_state` owns one DEM container and
`draw_dem`; freeflow has no task data beyond ordinary functionals and its
manager is a process-level registration.

`state_install()` still copies the public state into the process globals under
`_STATE_LOCK`.  That swap, the process-wide active pointer and the mirrored
sstuff/globe settings are the remaining boundary.

## Findings

### P0: blocks parallel sessions

| Location | State | Effect |
|---|---|---|
| `src/surfit/src/surfit_state.cpp:91` | `active_state`, `origin` | one active state per process; the swap is what the lock protects |
| `src/surfit/src/variables.cpp:76` | `map_name`, `solver_name`, `functionals`, containers | copied by `state_install`, but still process globals while active |
| `src/sstuff/src/sstuff_state.cpp` | active `sstuff_state` + mirrored `loglevel`/`stop_on_error`/`fileio_append`/`datafile_modE` | context is per task, but the installed value is process-wide |
| `src/globe/src/globe_state.cpp` | installed `globe_dems`/`draw_dem` | context is per task, but the installed value is process-wide |
| `src/pysurfit/src/module.cpp:144` | `log_observer` | last Python observer wins; concurrent sessions interleave callbacks |
| `src/pysurfit/src/module.cpp:83` | `my_surfit_io_manager` | shared IO manager; borrowed by each state |

These are enough to explain the current `test_sessions` result: two Sessions in
two threads serialize through `_STATE_LOCK`; removing the lock alone is not
safe.

### P1: reentrancy and reproducibility

| Location | State | Effect |
|---|---|---|
| `src/sstuff/src/fileio.cpp:49` | `logfile`, `logfilename`, `loglevel`, `stop_on_error`, `fileio_append` | log file/hook are state-owned; the mirrored settings are still process-wide |
| `src/sstuff/src/findfile.cpp:36` | `find_pattern`, `find_res`, `path_pos`, `file_handle`, `ff` | now state-owned; the installed cursor is process-wide |
| `src/sstuff/src/datafile.cpp:54` | `datafile_modE` | state-owned value, mirrored globally |
| `src/surfit/src/data.cpp:30` | `noname_counter`, `id_counter` | global IDs make interleaved sessions non-deterministic |
| `src/surfit/src/solvers.cpp:43` | `solvers`, static solver objects, `debug_cnt` | registry is mostly read-only; counter is not |
| `src/sstuff/src/rnd.cpp` | per-state xorshift64* | fixed; no process-wide `rand()` |
| `src/globe/src/dem_show.cpp:48` | `draw_dem` | now per globe_state, installed globally |
| `src/surfit/src/variables.cpp:107` | `randomize()` at init | now reseeds the active state's stream |

### P2: read-only or low risk

- `src/surfit/src/creeps/CreEPS.cpp` static const string tables;
- `src/sstuff/src/bitvec.cpp:37` `bits_per_byte` (a constant in practice);
- `src/surfit/src/license.cpp` has no mutable state;
- vendored CDT and minizip are outside the session contract.

## What this means

The per-task `data_manager`, `sstuff_state` and `globe_state` are real
progress: pools, logs, file search, RNG and DEMs no longer cross a session
boundary.  It does **not** make solves parallel, because:

1. `state_install()` still swaps globals;
2. the active `surfit_state`, `sstuff_state` and `globe_state` pointers are
   process-wide;
3. the mirrored settings and the surfit globals are process-wide;
4. the Python log observer and IO manager are shared.

The failed `thread_local` prototype was therefore not a surprise: it changed
the first layer and left the active pointers/mirrored settings shared, so the
second worker produced a different grid (`d523…` instead of `4616…`).

## Order of work

1. **sstuff context**: DONE — worker pool, log, file search, datafile mode and
   RNG are per task.
2. **plugin contexts**: DONE — `globe_state` owns the DEM container and display
   flag; freeflow managers are process-level registrations, rules are ordinary
   functionals.
3. **remove swap**: make the active surfit/sstuff/globe pointers and mirrored
   settings thread-local together; bind worker threads to their owning sstuff
   state; then delete the copy-in/copy-out.
4. **per-session lock**: remove `_STATE_LOCK`; keep one mutex per Session for
   same-session calls.
5. **tests**: two Sessions in two threads must match solo hashes; DEM and
   freeflow must not mix; logging must not interleave into one file.

Until 1–3 are done, the honest claim is **interleaved sessions**, not parallel
sessions.
