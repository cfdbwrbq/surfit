# Silent exceptions audit

Scope: Python package (`src/pysurfit/python/surfit`), C++ core and plugins,
docs/CI helpers and examples.  Tests are listed separately because an
`except` in a test is usually an assertion mechanism, not runtime behaviour.

Method: searched every `try/except`, `contextlib.suppress`, `catch` and
`throw` in the tracked sources, then read each production handler in context.
A handler is **silent** when it neither re-raises nor reports the failure.

## Summary

- No bare `except:` in production Python.
- No `except Exception: pass` in the Python package.
- C++ has **7** `catch (...)` handlers, all in file-autoload paths; none logs
  the exception.
- Python has **one** real silent-skip path in `anisotropy`; the other handlers
  are optional-dependency errors, cleanup/re-raise, or destructor guards.
- `file_load()` ignores the boolean result of `auto_load()`, so a failed format
  probe can leave no data and no error message.

## P1 — silent file autoload (C++)

| Location | What happens | Why it matters |
|---|---|---|
| `src/surfit/src/data_manager.cpp:701` | `curv_read()` inside `catch (...)`, then `goto exit` | malformed 2-column file is silently treated as “not this format” |
| `src/surfit/src/data_manager.cpp:715` | `pnts_read()` inside `catch (...)`, then `goto exit` | same for 3-column data |
| `src/surfit_io/src/surfit_io_data_manager.cpp:163` | shapefile loader `catch (...)` | a broken SHP/DBF gives `false`, no reason |
| `src/surfit_io/src/surfit_io_data_manager.cpp:177` | GMT loader `catch (...)` | same |
| `src/surfit_io/src/surfit_io_data_manager.cpp:196` | Surfer GRD loader `catch (...)` | same |
| `src/surfit_io/src/surfit_io_data_manager.cpp:210` | Grass loader `catch (...)` | same |
| `src/surfit_io/src/surfit_io_data_manager.cpp:223` | ArcGIS ASCII loader `catch (...)` | same |

`data_manager::auto_load()` (`data_manager.cpp:116`) tries managers in reverse
order and returns `false` if none succeeds.  `file_load()` at
`data_manager.cpp:901` calls it but ignores that result, so the user sees an
empty task rather than “no loader accepted this file”.

**Why the catches exist.** They are a format-probing mechanism: a loader that
throws should let the next format try.  That part is reasonable.  What is
missing is the diagnostic.

**Options, in order of value:**

1. Log a warning from each catch with the filename and, when possible, the
   exception:
   ```cpp
   } catch (const std::exception & error) {
       writelog(LOG_WARNING, "auto_load %s: %s", filename, error.what());
   } catch (...) {
       writelog(LOG_WARNING, "auto_load %s: unknown exception", filename);
   }
   ```
   Keep `return false` so probing continues.
2. In `file_load()`, if `auto_load()` returns false, emit
   `writelog(LOG_ERROR, ...)` (or a Python-visible error) instead of silently
   doing nothing.  This changes the current “empty result” behaviour and needs
   a test.
3. Do not convert all exceptions to `false`; let `std::bad_alloc` and
   `std::logic_error` propagate.  `catch (...)` currently hides both.
4. Keep the format-specific branches; they are not the problem.

## P2 — variogram anisotropy skips directions

`src/pysurfit/python/surfit/variogram.py:181`:

```python
try:
    fit = fit_variogram(...)
except ValueError:
    continue
```

A direction with too few finite bins is silently omitted.  If at least two
directions survive, `anisotropy()` returns a result based on a subset with no
record of what was dropped.  That can turn a weak estimate into an apparently
complete angle/ratio.

**Fix:** collect `skipped = [{"direction": ..., "reason": ...}]` and include it
in the result; add `strict=True` to raise when any direction fails.  Add a test
with one direction that has no pairs.

## P3 — optional dependencies and cleanup (intentional)

These are clear and should stay, but they should remain distinguishable from
real failures:

| Location | Handler | Assessment |
|---|---|---|
| `provenance.py:24` | `PackageNotFoundError` → `"unknown"` | intentional for source trees; the report should keep the `unknown` marker |
| `geotiff.py:24` | `ImportError` → explicit `ImportError` | clear, not silent |
| `crs.py:16` | `ImportError` → explicit `ImportError` | clear |
| `__init__.py:182` | optional `tqdm` → explicit install hint | clear |
| `postgis.py:78,87` | cleanup then re-raise | opaque, but the exception is preserved |
| `postgis.py:133` | CSV parse `ValueError` → better message | clear |
| `postgis.py:68` | `contextlib.suppress(OSError)` on temp unlink | cleanup only; losing the unlink error is acceptable |
| `__init__.py:411` | `Session.__del__` catches everything | intentional; destructors must not raise |
| `sampling.py:198,202,264` | SciPy import/Qhull error | re-raised or converted to a clear `ValueError`; `auto` fallback is intentional |
| `docs/conf.py:42` | optional Sphinx theme | intentional fallback |
| `examples/python/progress.py:37` | optional `tqdm` | prints and continues |

`src/pysurfit/src/module.cpp:154` is not silent: it calls
`py::error_already_set::discard_as_unraisable`, which reports the observer
exception as unraisable.

## Tests and CI helpers

Test `except` blocks in `src/pysurfit/tests/` are assertion mechanisms
(`assertRaises`, expected failure) and should not be changed just to satisfy a
grep.  `ci/selfcheck.py` catches import errors and turns them into a failed
selfcheck, which is correct.

## Recommended order

1. **P1:** log `auto_load` failures and check the return value in `file_load`.
   This is the only group that can produce a genuinely empty result with no
   diagnostic.
2. **P2:** report skipped variogram directions and add a strict mode.
3. **Guard:** add a small CI grep that rejects a future
   `except Exception:\s*pass` in the package (tests excluded).
4. Do not “fix” optional-dependency, cleanup or destructor handlers by making
   them noisy; their current behaviour is intentional and documented.

## What not to do

- Do not remove all `catch (...)` in autoload: a broken file should still let
  the next format probe run.
- Do not turn every optional-import failure into a hard dependency.
- Do not add a global `sys.excepthook` or wrap the whole Python API; it hides
  the traceback that users need.
