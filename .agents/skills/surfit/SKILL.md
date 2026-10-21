---
name: surfit
description: >
  Use when building, testing, packaging, releasing, or preparing data for the
  surfit C++/Python gridding engine. Covers the CMake/pybind11 setup, the full
  test suite, Tcl and documentation prerequisites, the Python Session/area
  traps, and the manylinux release gate.
---

# Working on surfit

surfit is a C++ gridding engine with three front ends in this tree:

- the C++ library in `src/surfit`, `src/sstuff`, `src/globe`, `src/freeflow`;
- the pybind11 package in `src/pysurfit/python/surfit` (the supported Python API);
- the legacy Tcl front end in `src/tclsurfit` (off by default).

The original engine is from 2002–2015; the Python port and the newer checks are
recent. Read `HANDOFF.md` in the parent directory for the current state, and
`AGENTS.md` for the mandatory full-test/silent-push rules.

## First commands

```bash
pwd                       # repo root ends with /surfit
git status --short
git log --oneline -5
sed -n '1,160p' AGENTS.md
```

Do not assume the remote is up to date: when an experiment is silent, do not
push at all. Finish, verify locally, and leave the branch for review.

## Build for Python

Prerequisites: CMake >= 3.10, a C++17 compiler, Python development headers, and
pybind11. Tcl is optional and only needed for the Tcl examples.

```bash
cmake -S src -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
```

If CMake says ``pybind11 not found``, point it at a config directory, either the
installed one or the checkout's bundled copy:

```bash
python3 -m pybind11 --cmakedir
# or, in this workspace:
export PYBIND11_DIR="$PWD/../third_party/pybind11/share/cmake/pybind11"
cmake -S src -B build -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR="$PYBIND11_DIR"
```

The build tree has the pure-Python package next to the extension:
`build/bin/surfit`. For direct tests:

```bash
export SURFIT_BIN="$PWD/build/bin"
export PYTHONPATH="$SURFIT_BIN"
python3 src/pysurfit/tests/test_parity.py
```

For the Tcl front end add `-DSURFIT_BUILD_TCL=ON`. It needs `tcl-dev`, `tk-dev`
and SWIG; without Tk headers CMake fails with `Could NOT find TCLTK (missing:
TK_INCLUDE_PATH)`.

## The full suite is the only final check

```bash
PYBIND11_DIR="$PWD/../third_party/pybind11/share/cmake/pybind11" \
PYTHONPATH="$PWD/../.wpsdeps:$PWD/../.docsdeps" \
./ci/check.sh --full
```

It runs 35 Tcl/Python scripts, 49 examples, the 29 realworld pipelines,
documentation, WPS and the wheel smoke test. While developing a subset is fine;
before declaring a change done, the full run is mandatory.

The script builds in `build-ci/`. If Python tests fail with
`ModuleNotFoundError: surfit`, pybind11 was not found during configure; set
`PYBIND11_DIR` (above) and remove the stale `build-ci` if necessary.

## Documentation

```bash
python3 -m pip install -r docs/requirements.txt   # or use .docsdeps
PYTHONPATH=../.docsdeps ./docs/build.sh
PYTHONPATH=../.docsdeps python3 docs/check_docs.py
```

Figures are generated separately, not by `docs/build.sh`:

```bash
mkdir -p ../js-test && cd ../js-test && npm install d3 jsdom
cd .. && PYTHONPATH=.docsdeps SURFIT_BIN=surfit/build/bin \
  python3 surfit/docs/make_images.py
```

The 3-D area figure is produced by `docs/surface3d.js` through
`docs/render_svg.js` with `RENDERER=3d`; the normal viewer stays 2-D. Committed
SVGs live in `docs/_static/`, so a docs build needs neither Node nor a browser.

## Python API traps

Create the `Session` first. Its constructor resets the process-wide engine
state, so data loaded before it disappears:

```python
# wrong: the areas are gone by the time the task exists
surfit.area_read("area6.txt", "area6")
task = surfit.Session(...)
task.area_leq(20, "area6")       # []

# right
task = surfit.Session(...)
task.area_read("area6.txt", "area6")
task.area_leq(20, "area6")       # [True]
```

- `task.names()` lists **surfaces**, not areas. Use `surfit.area_size()` and
  `surfit.area_getName("*")` for areas.
- `area_leq`, `area_geq`, `area_mean` and the other area rules return one flag
  per matched area and an **empty list** when nothing matches. They do not
  raise; a miss is a silent no-op. Check the return value.
- Conditions (`area_leq`/`area_geq`) must be followed by a functional in the
  rule order; the penalty pass attaches them to the next rule.
- `Session` calls are serialised by a process-wide lock; do not run two sessions
  concurrently in one process.
- `surfit.defined_mask(values)` selects defined nodes; undefined nodes carry
  `surfit.UNDEF_VALUE` (FLT_MAX).

## Preparing input data

- Text points: `pnts_read(path, name, col1, col2, col3, col4, delimiter,
  skip_lines, grow_by)`. Column numbers are 1-based; `col4=0` means no name.
- Areas: `area_read(path, name, col1, col2, delimiter, ...)`; each row is one
  polygon node, first and last point usually repeat.
- Contours: `cntr_load_shp(path, name, zfield)`; for shapefiles with a constant
  Z use an ARCZ shapefile or pass the correct `zfield`. The old `cntr_shp` bug
  (type fixed by the first contour) is fixed; do not reintroduce a one-pass
  writer.
- Bad isolines: filter multipart or <2-point shapes before feeding the binding,
  and clip/tile large contour sets. The 4 m isoline experiment in
  `tmp_izol/isolines_pipeline_history.py` is the reference for that workflow.
- Triangle is gone. Triangulation uses the vendored CDT under
  `src/surfit/src/third_party/cdt`; do not add Shewchuk's Triangle back.

## Packaging and release

Manylinux wheels are built in Docker, not by the agent (the sandbox has no
Docker socket). The user runs:

```bash
sudo ./build-manylinux.sh
./collect-release.sh
./check-release.sh
```

`build-manylinux.sh` builds cp39–cp313 manylinux2014 wheels into
`surfit/dist/manylinux2014`; `collect-release.sh` copies them, writes
`SHA256SUMS-release.txt`, and runs the gate. `check-release.sh` checks the
repository, tracked artifacts, wheel tags, absence of netcdf/curl/ssl, the docs
zip and personal data. The release text lives in `RELEASE_v<version>.md`.

For a version bump update `pyproject.toml`, `src/CMakeLists.txt`,
`docs/conf.py`, `src/pysurfit/python/surfit/_viewer.py` and
`requires-python`; then rebuild docs and the wheel. Tag only after the gate
passes.

## Before you call it done

```text
[ ] ./ci/check.sh --full  -> all checks passed
[ ] docs/check_docs.py    -> both trees in step
[ ] git status --short    -> only intended files
[ ] git diff              -> no generated binaries, no personal paths
[ ] silent mode?          -> no push, no tag, no release
```
