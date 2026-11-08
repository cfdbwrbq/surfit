# Audit: state that is not per-session

Scope: `src/surfit`, `src/globe`, `src/freeflow`, `src/sstuff` and
`src/pysurfit`.  Vendored code, generated SWIG wrappers, `minizip` and the Tcl
front end are excluded; Tcl is no longer a design constraint for this work.

Method: file-scope `static`/`extern` globals, function-level statics that keep
state, mutable singletons, and the ownership of the managers in `surfit_state`.
Each entry is a candidate for a real per-session context, not a style issue.

## Already per session

`surfit_state` already owns the seven containers, `functionals`, the target
grid, settings, solver scratch and now a `data_manager` with a borrowed manager
list.  `state_install()` still copies that state into the process globals under
`_STATE_LOCK`; that is the remaining architectural boundary.

## Findings

### P0: blocks parallel sessions

| Location | State | Effect |
|---|---|---|
| `src/surfit/src/surfit_state.cpp:91` | `active_state`, `origin` | one active state per process; the swap is what the lock protects |
| `src/sstuff/src/threads.cpp:32` | `cpu`, `slaves`, `jobs`, `garb_slaves` | one internal worker pool; two solves share jobs/slaves |
| `src/surfit/src/variables.cpp:76` | `map_name`, `solver_name`, `functionals`, containers | copied by `state_install`, but still process globals while active |
| `src/globe/src/dem.cpp:621` | `globe_dems` | DEM container is global; Python `_dems` is per task only at the call boundary |
| `src/globe/src/globe_state.cpp:27` | `library_dems` | static library container is shared by every task |
| `src/freeflow/src/flow_variables.cpp:37` | `flow_manager`, `flow_garb` | freeflow manager is a process singleton |
| `src/pysurfit/src/module.cpp:144` | `log_observer` | last Python observer wins; concurrent sessions interleave callbacks |
| `src/pysurfit/src/module.cpp:83` | `my_surfit_io_manager` | shared IO manager; borrowed by each state |

These are enough to explain the current `test_sessions` result: two Sessions in
two threads serialize through `_STATE_LOCK`; removing the lock alone is not
safe.

### P1: reentrancy and reproducibility

| Location | State | Effect |
|---|---|---|
| `src/sstuff/src/fileio.cpp:49` | `logfile`, `logfilename`, `loglevel`, `stop_on_error`, `fileio_append` | log destination and level are process-wide |
| `src/sstuff/src/fileio.cpp:75` | `surfit_log_hook` | one log hook for all tasks |
| `src/sstuff/src/findfile.cpp:36` | `find_pattern`, `find_res`, `path_pos`, `file_handle`, `ff` | `find_first`/`find_next` is not reentrant |
| `src/sstuff/src/datafile.cpp:54` | `datafile_modE` | global file-open mode |
| `src/surfit/src/data.cpp:30` | `noname_counter`, `id_counter` | global IDs make interleaved sessions non-deterministic |
| `src/surfit/src/solvers.cpp:43` | `solvers`, static solver objects, `debug_cnt` | registry is mostly read-only; counter is not |
| `src/sstuff/src/rnd.cpp` | `srand`/`rand` | noise commands change the process-wide C RNG |
| `src/globe/src/dem_show.cpp:48` | `draw_dem` | display setting is process-wide |
| `src/surfit/src/variables.cpp:107` | `randomize()` at init | one RNG stream for every task |

### P2: read-only or low risk

- `src/surfit/src/creeps/CreEPS.cpp` static const string tables;
- `src/sstuff/src/bitvec.cpp:37` `bits_per_byte` (a constant in practice);
- `src/surfit/src/license.cpp` has no mutable state;
- vendored CDT and minizip are outside the session contract.

## What this means

The per-session `data_manager` is real progress: `clear_data()` and
`grid_auto()` no longer cross a session boundary.  It does **not** make solves
parallel, because:

1. `state_install()` still swaps globals;
2. the internal thread pool is global;
3. globe/freeflow managers and their containers are global;
4. logging/file search/RNG/ID counters are global.

The failed `thread_local` prototype was therefore not a surprise: it changed
the first layer and left the other three shared, so the second worker produced
a different grid (`d523…` instead of `4616…`).

## Order of work

1. **sstuff context**: thread pool + fileio/findfile/datafile/RNG per task.
2. **plugin contexts**: `globe_dems`/`library_dems` and freeflow manager inside
   `surfit_state` (opaque pointers if the core must not depend on the plugin).
3. **remove swap**: make the active context explicit or thread-local; delete
   `state_install()` copy-in/copy-out.
4. **per-session lock**: remove `_STATE_LOCK`; keep one mutex per Session for
   same-session calls.
5. **tests**: two Sessions in two threads must match solo hashes; DEM and
   freeflow must not mix; logging must not interleave into one file.

Until 1–3 are done, the honest claim is **interleaved sessions**, not parallel
sessions.
