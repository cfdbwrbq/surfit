# surfit

surfit is a computer program which enables to calculate regular grid from 
various data (scattered points, curves, surfaces, etc), conditions 
and inequalities by setting called "gridding rules".

It interpolates and approximates scattered points, contours, surfaces and areas;
it can take fault lines, trend surfaces, anisotropy and inequalities into
account, and it supports a range of data formats.

## How this port was made

The original surfit engine and its Tcl front end were written by M. V.
Dmitrievsky and V. N. Kutrunov between 2002 and 2015.

The 2026 Python port — pybind11 bindings, the test harness, the build scripts
and the documentation — was produced with an **AI coding agent under human
direction and review**. The maintainer is responsible for the code and for its
correctness.

The port is checked against the original: 49 Tcl examples produce byte-identical
data files, 504 command steps run on both front ends, and `ci/check.sh` runs the
full suite. AI-assisted code can still contain errors; the software is provided
under GPL-2, without warranty.

See [AI_DISCLOSURE.md](AI_DISCLOSURE.md) for the full statement and
`docs/en/stats.rst` for the measured AI session and token counts.

## Python

The engine is available as a Python package. It drives the original C++ core,
so results are identical to those of the Tcl front end, and grids cross the
boundary as numpy arrays in both directions.

Runnable versions of both snippets below are in [`examples/python/`](examples/python).

```bash
pip install .                     # needs cmake and a C++ compiler
```

```python
import surfit
import numpy as np

task = surfit.Session(map_name="map_area", tol=5.01187e-06)

for name in ("area1", "area2", "area3", "area4", "area5"):
    task.read_areas("data/%s.txt" % name, name)

task.grid(-12, 12, 0.2, -12, 12, 0.2)

task.area(10, "area1")        # the surface equals 10 inside area1
task.area(30, "area3")
task.area("undef", "area5")   # leave area5 undefined
task.completer(1, 1.6)        # tend to a constant or a plane
task.area_add(20, 0.07, "area2")   # approximate, with a weight
task.area_add(40, 0.07, "area4")

task.solve()
task.save("area.dat")             # surfit native data file

grid = task.values()              # numpy (count_y, count_x), float64
print(grid.shape, surfit.defined_mask(grid).sum())
```

Undefined nodes carry `surfit.UNDEF_VALUE` (`FLT_MAX`); `surfit.defined_mask()`
selects the defined ones.

### numpy in, numpy out

```python
import surfit
import numpy as np

# A regional trend, handed to the engine as an array: 40 x 50 nodes,
# 25 units apart, covering x 0..1225 and y 0..975.
trend = np.linspace(100.0, 120.0, 40 * 50).reshape(40, 50)

task = surfit.Session(map_name="result")
task.add_surface(trend, start_x=0.0, step_x=25.0, start_y=0.0, step_y=25.0,
                 name="regional")
task.read_points("wells.txt", "wells")

task.grid(0, 1225, 25, 0, 975, 25)
task.points("wells")              # honour the measurements
task.surface("regional")          # and follow the regional trend
task.completer(1, 2)
task.solve()

result = task.values()            # the surface created last, i.e. the result
```

### File formats

The shapefile / BLN / Surfer / GMT / Grass / ArcGIS / xyz / jpg / bmp loaders and
savers of the `surfit_io` plugin are exposed under their Tcl names:

```python
surfit.area_load_shp("zones.shp", "zones")
surfit.cntr_load_shp("isolines.shp", "iso")
surfit.surf_load_grd("surface.grd", "top")
surfit.surf_save_grd("smoothed.grd", "top")
```

Every command of the Tcl front end is available under the same name, so the
scripts in `examples/` translate one call to one call. `src/pysurfit/tests/`
contains a runner that does exactly that and compares the output byte for byte.

### More than one task

Each `Session` owns its state, so several tasks can share a process. Calls may be
interleaved; a process-wide lock serializes them, and a solve blocks the other
Session's calls until it finishes. Module-level functions use whichever state is
active and are not protected by that lock.

## Building

```bash
mkdir -p build && cd build
cmake ../src
make -j"$(nproc)"
export LD_LIBRARY_PATH="$PWD/bin:$LD_LIBRARY_PATH"
```

Requirements: `cmake` >= 3.10 and a C++ compiler. The engine itself has no
Tcl dependency. `zlib`, `libjpeg` and `netcdf` are optional and enable the globe
module and the JPEG/netCDF formats.

The original examples use a Tcl front end, which is off by default; it needs
`tcl-dev` and SWIG:

```bash
cmake -DSURFIT_BUILD_TCL=ON ../src
make -j"$(nproc)"
cd examples/surfit/tests
tclsh area.tcl
```

## Code style

[![WPS](https://github.com/cfdbwrbq/surfit/actions/workflows/wps.yml/badge.svg)](https://github.com/cfdbwrbq/surfit/actions/workflows/wps.yml)

The Python package and the documentation tooling are checked with
[wemake-python-styleguide](https://wemake-python-styleguide.readthedocs.io/):

```bash
pip install -r requirements-dev.txt
python3 -m flake8 --config .flake8 src/pysurfit/python docs
```

Tests and examples are excluded (they are scripts with literal numbers and
`print`), and `.flake8` documents the package's deliberate exceptions: the
dynamic re-export facade, the public `Session` API and the psql/tempfile error
handling.

## Tests

```bash
# the original Tcl regression suite
./run_baseline.sh

# the same scripts driven through the Python bindings, compared byte for byte
python3 src/pysurfit/tests/run_tcl_suite.py
python3 src/pysurfit/tests/run_tcl_suite.py --sequential examples/surfit/realworld
```

## Documentation

The full documentation lives in `docs/` and is built with Sphinx in English and
Russian, English first:

```bash
pip install -r docs/requirements.txt
docs/build.sh                 # -> docs/_build/html/index.html
```

`docs/check_docs.py` verifies that the two language trees have the same pages,
sections and toctrees; run it after editing either one. The older `doc/`
directory holds the original Doxygen sources.

## License

GNU General Public License, version 2. See [LICENSE](LICENSE).

Note that `src/surfit/src/triangle.cpp` is Shewchuk's Triangle, whose licence is
not GPL: redistribution is free but commercial use requires a separate
arrangement. That file is on the repository's default build path, so anyone
shipping a binary should review this first.
