# surfit

[English](README.md) | [Русский](https://cfdbwrbq.github.io/surfit/ru/) | [中文](README.zh.md)

## Build a surface that keeps the geology

**Faults stay faults. Wells stay tied. Bounds stay bounds. Layers stay ordered.**

[![CI](https://github.com/cfdbwrbq/surfit/actions/workflows/ci.yml/badge.svg)](https://github.com/cfdbwrbq/surfit/actions/workflows/ci.yml)
[![WPS](https://github.com/cfdbwrbq/surfit/actions/workflows/wps.yml/badge.svg)](https://github.com/cfdbwrbq/surfit/actions/workflows/wps.yml)
[![Release](https://img.shields.io/github/v/release/cfdbwrbq/surfit)](https://github.com/cfdbwrbq/surfit/releases)

![A surface with four faults](docs/_static/map-faults.svg)

*A surface built from points and four fault lines. The faults are explicit
breaks in the grid, not smooth trends through the data.*

## What you give it

Wells, curves, contours, polygon boundaries, surfaces, trends, masks and fault
lines.  You say what each one means:

- this well is a measurement;
- this fault is a break;
- this polygon is a constant;
- this bound must hold;
- this area must stay smooth.

## What you get

A regular surface on the grid you asked for.  Not a smoothed cloud: the rules
remain visible in the result.

- **Faults.** The surface can jump across a fault line instead of averaging
  through it.
- **Data.** Wells and curves stay tied to their values; approximations carry
  their own weight.
- **Limits.** Values can be held above, below or between bounds inside
  polygons and masks.
- **Layers.** `SurfaceStack` checks thickness, ordering and pinch-outs across
  several horizons.
- **Uncertainty.** Cross-validation, bootstrap ensembles and calibrated
  intervals describe what the data supports — and what it does not.

## Three things it refuses to smooth away

| ![Data and bounds](docs/_static/map-points-ineq.svg) | ![A faulted surface](docs/_static/author-surface.svg) |
|---|---|
| **Data and limits.** Wells tie to measurements; bounds hold where you put them. | **Faults and wells.** The surface steps across explicit fault lines; the wells stay tied. |

## What it will not do

- It is a 2.5D surface engine, not a 3D voxel model.
- It will not invent a geological interpretation: you still choose the faults,
  bounds and rules.
- It will not hide a bad input. Missing files, unmatched names and impossible
  bounds are reported.
- It does not claim GCV, kriging or a posterior.  The uncertainty tools say
  what they measure.

## Install

Linux x86_64 wheels (CPython 3.9–3.13) are attached to each
[release](https://github.com/cfdbwrbq/surfit/releases).  Pick the wheel for
your interpreter, for example CPython 3.12:

```bash
pip install https://github.com/cfdbwrbq/surfit/releases/download/v3.7.3/surfit-3.7.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl
```

From source, with CMake and a C++ compiler:

```bash
pip install .
```

Optional extras:

```bash
pip install ".[geoparquet]"   # pyarrow + shapely
pip install ".[mesh]"         # PyVista
```

## One task

```python
import surfit
import numpy as np

x = np.array([0.0, 1.0, 0.0, 1.0, 0.5])
y = np.array([0.0, 0.0, 1.0, 1.0, 0.5])
z = np.array([1.0, 2.0, 3.0, 4.0, 2.5])

task = surfit.Session(map_name="demo", tol=1e-7)
task.add_points(x, y, z, name="wells")
task.grid(0, 1, 0.05, 0, 1, 0.05)
task.points("wells")
task.completer(1, 1.6)
task.solve()

grid = task.values()          # (count_y, count_x), row 0 is min_y
print(grid.shape, np.nanmin(grid), np.nanmax(grid))
```

Faults, bounds and areas use the same task: read the data, add the rule, solve.
The [Python guide](docs/en/python.rst) has a fault-aware example.

## Documentation

- [English guide](https://cfdbwrbq.github.io/surfit/en/)
- [Russian guide](https://cfdbwrbq.github.io/surfit/ru/)
- [Capabilities, English](CAPABILITIES.en.md)
- [Capabilities, Russian](CAPABILITIES.md)
- [How the solver works](docs/en/how_it_works.rst)
- [Python examples](examples/python)

The docs are built with Sphinx from `docs/en` and `docs/ru`; the two trees are
checked for structural parity by `docs/check_docs.py`.

## Under the hood

The C++ engine (2002–2015) is driven by a Python package.  It uses CMOFS:
ordered functionals, a penalty loop for constraints, and an 8×8 multilevel
ladder.  The solver is `cg`, `jcg`, `rf`, `jacobi` or `ssor`.

The test suite compares the Python front end with the original Tcl outputs
byte-for-byte, checks the 35 examples and the realworld pipelines, and runs a
physics/invariance set: translation, rotation, linear fields, point order and
degenerate inputs.  The Tcl front end is deprecated; 3.7.x is its last line and
3.8 removes it.

```bash
# Fast self-check: docs, skills, Python API
python3 ci/selfcheck.py

# Full gate: examples, parity, docs, WPS, wheel smoke test
ci/check.sh --full
```

## Review notes

> “A scientific instrument with an engineering conscience.”
>
> — Alice (Yandex), translated review

> “Mathematics without illusions: a fast C++ core for 2.5D gridding with
> byte-for-byte reproducibility, uncertainty estimation, and honest limits.”
>
> — independent review, not Gemini

These are review notes, not vendor endorsements.

## License

GNU General Public License, version 2.  See [LICENSE](LICENSE) and
[AI_DISCLOSURE.md](AI_DISCLOSURE.md).  The vendored CDT triangulation is
MPL-2.0.
