---
name: surfit
description: >
  Use when writing or running a surfit gridding task: loading points, curves,
  contours, areas, surfaces or masks; defining rules; solving; reading the
  resulting grid; validating it with spatial CV, variograms, support or
  diagnostics; or debugging an empty/no-op result. This is the usage skill,
  not a build or release checklist.
---

# Working with surfit

surfit builds a regular grid from scattered data under **gridding rules**.
The Python package is a thin wrapper around the same C++ engine as the Tcl
front end: one Tcl command maps to one Python call, and both produce the same
result.

## The shape of a task

```python
import numpy as np
import surfit

task = surfit.Session(map_name="result", tol=1e-6)   # Session first
task.pnts_read("wells.txt", "wells")                  # data after it
task.grid(0, 1000, 25, 0, 1000, 25)                  # x0,x1,dx, y0,y1,dy
task.points("wells")                                  # a rule
task.completer(1, 2)                                  # another rule
task.solve()
grid = task.values()                                  # (count_y, count_x)
```

**Order matters:** a `Session` creates a task on the calling thread. Data
loaded into the module-level state before the constructor is not part of that
task. `grid()` may be called before or after the rules, but all data and rules
must be created on that session.  Engine globals are thread-local, so Sessions
in different threads can solve in parallel; calls on one Session are serialized
by its own lock.

## Grid and result conventions

- `grid(x0, x1, dx, y0, y1, dy)`; the result is `(count_y, count_x)` row-major.
- Row 0 is `min_y` (south edge), the last row is `max_y`.
- Undefined nodes carry `surfit.UNDEF_VALUE` (`FLT_MAX`). Select defined nodes
  with `surfit.defined_mask(grid)`; do not compare to `FLT_MAX` by hand.
- `task.values()` without a name returns the **most recently created surface**
  (normally the solve result). Use `task.values("name")` when the task holds
  several surfaces.
- `surf_extent(name)` returns the matching `min_x/max_x/min_y/max_y/step_x/step_y`.

## Edge effects and halos

The grid edge is not an ordinary part of the map:

- cells near `min_x`/`max_x`/`min_y`/`max_y` have points on one side only; the
  completer extrapolates from the interior, so edge values are less constrained
  and can be biased;
- do not compare a global RMSE dominated by edge cells with the error of the
  interior; report the edge band separately or exclude it from a data-quality
  claim;
- in a tiled/out-of-core solve, overlap tiles by a **halo** and write only the
  inner part.  Without a halo, the pieces are separate boundary-value problems
  and the seams show as jumps or undefined nodes;
- area and mask boundaries are also boundaries: the rule applies inside, the
  outside is unconstrained/undefined unless `inside=0` or a complement mask is
  used;
- `save_geotiff` places nodes at cell centres; the raster edge is half a step
  beyond the first/last node.  Do not shift the grid twice when comparing with
  a GIS raster.

## Rules that are easy to get wrong

### Min/max and equality rules

The complete table of result-shaping rules — global, points, areas, contours,
curves, masks, surfaces and surface-to-surface bounds — is in
[RULES.md](RULES.md). Read it before adding a bound: the direction, `inside`,
penalty behaviour and condition order all matter. `area_leq`/`area_geq` are
conditions, not a clip, and they do not raise when the area name is missing.

### Areas

```python
task.area_read("area1.txt", "area1")    # rows are x y of one polygon
task.area(10, "area1")                  # surface == 10 inside
task.area_add(20, 0.07, "area2")        # approximate, with weight
task.area_leq(20, "area6")              # surface <= 20 inside area6
task.area_geq(15, "area6")              # surface >= 15 inside area6
```

- `area_leq` / `area_geq` / `area_mean` are **conditions**. Put them before the
  functional that should carry them; the penalty pass attaches a condition to
  the next rule.
- They return one flag per matched area, and an **empty list** when the name does
  not match. They do not raise: check the return value.
- `task.names()` lists **surfaces**, not areas. Areas are
  `surfit.area_size()` and `surfit.area_getName("*")`.
- Load areas after creating the `Session`; loading them before it is the most
  common silent no-op.

### Points

```python
task.pnts_read("points.txt", "p", 1, 2, 3, 0, " \t", 0, 250)
task.points("p")          # exact at the point nodes, averaged per grid cell

# optional per-point positive weights (Python only):
task.read_points("points.txt", "p", weights=[1.0, 0.5, ...])
# or: task.pnts_set_weights("p", weights)
```

Arguments after the name are `col1 col2 col3 col4 delimiter skip_lines grow_by`;
columns are 1-based and `col4=0` means “no name column”. Points in the same grid
cell are averaged; a `999 999 999` row is skipped.

### Contours

```python
task.cntr_load_shp("isolines.shp", "iso", "Z")
task.contour("iso")
```

`cntr_load_shp` needs the Z field name when the shapefile stores Z as an
attribute rather than as 3D arc coordinates. Contours are curves with a
constant value; use `curv_load_shp` when the geometry is a plain line without a
value.

### Curves, surfaces, masks

- `curv_read(path, name)` / `curv_load_shp` then `curve("name")`.
- `surf_load_grd` / `surf_load` then `surface("name")` uses a surface as data.
- `mask_read` / `mask_load` then `mask("name")`; `mask_ineq("name")` for bounds.
- `trend` and `fault` are separate rules; keep the rule order of the Tcl script
  when porting an example.

## Solving, saving, viewing

```python
task.solve()
task.save("result.dat")                       # native surfit data file
task.surf_save_grd("result.grd", "result")    # Surfer grid
page = task.viewer()                          # self-contained HTML

stats = task.residuals(x, y, z, weights=sigma_inv)  # observed - nearest node
# stats: n, residuals, rmse, bias, weighted_mse, chi2, dof
flags, stats = task.outliers(x, y, z, weights=sigma_inv, threshold=3.5)
# flags are suggestions; zero their weights and re-solve

from surfit.diagnostics import robust_weights
# IRLS: rebuild the task with robust_weights(residuals) and solve again;
# the engine's inner solve is still least squares.

from surfit.diagnostics import bootstrap_uncertainty
# stats = bootstrap_uncertainty(build, len(x), replicates=50, seed=7)
# ensemble spread, not a covariance matrix

from surfit.diagnostics import robust_solve
# result = robust_solve(build, x, y, z, loss="huber", iterations=4)
# outer IRLS: build(weights) returns a solved task

task.set_metadata(crs="EPSG:32637", x_units="m", y_units="m")
task.save_metadata("result.meta.json")
task.save_report("result.report.json", x, y, z, weights=sigma_inv,
                 sources=["wells.txt"])
task.save_geotiff("result.tif")       # uses metadata crs; GDAL optional
# strict=True turns an empty rule match into ValueError
# Session(serial=True) forces one worker for this task's solve

from surfit.tiled import solve_point_tiles, solve_tiled
# point-only out-of-core mosaic:
# result = solve_point_tiles(x, y, z, extent, step,
#     inner=256, halo=32, memmap_path="map.f64")
# generic tiled rules (curves, contours, areas):
# result = solve_tiled(build_tile, extent, step,
#     inner=64, halo=16, memmap_path="map.f64")
```

`viewer()` is a 2-D filled contour map; `save_viewer(path)` writes it. For a
headless check, inspect `task.values()` and `defined_mask`, not the HTML.

## Quality, validation and support

These are diagnostics, not a covariance model.  They answer different
questions; do not turn one number into "the uncertainty".

```python
# Spatial CV: callback gets only training indices and training weights.
cv = surfit.cross_validate(
    build, x, y, z, folds=5, mode="block", block=10.0)
# cv["rmse"], cv["bias"], cv["fold_details"]

# Block bootstrap: whole blocks, not i.i.d. points.
labels = surfit.block_labels(x, y, block=10.0)
stats = surfit.bootstrap_uncertainty(
    build, len(x), replicates=100, seed=7, blocks=labels)
# stats["sampling"] == "block"; stats is ensemble spread

# Variogram: diagnostic and anisotropy hint, not kriging.
exp = surfit.experimental_variogram(x, y, z, bins=16, direction=0)
fit = surfit.fit_variogram(exp["lag"], exp["gamma"], model="spherical")
direction = surfit.anisotropy(x, y, z, angles=(0, 45, 90, 135))

# Per-node support: count, sum/negative weights, distances.
attrs = task.quality_attributes(x, y, weights=sigma_inv)
# attrs["count"], attrs["min_distance"], attrs["negative_weights"]

# Typed point diagnostics and GeoJSON/CSV hand-off.
doc = task.diagnostic_points(x, y, z, weights=sigma_inv)
# codes: 0 used, 1 outlier, 2 undefined cell, 3 outside grid, 4 zero weight
task.save_diagnostics("qc.geojson", x, y, z, weights=sigma_inv)

# Provenance and source hashes in the report/sidecar.
report = task.report(x, y, z, weights=sigma_inv, sources=["wells.txt"])
# report["provenance"]["engine_version"], report["provenance"]["sources"]

# Decluster dense clusters before rebuilding the task.
reduced = surfit.decluster_points(
    x, y, z, weights=sigma_inv, method="mean", block=10.0)
# methods: mean, nearest, idw, min, max; raw points stay for residuals

# 2D polygonal declustering: inverse clipped Voronoi cell area, mean 1.
weights = surfit.voronoi_weights(x, y, bounds=extent)
# backend="auto" uses scipy when present; "clip" is pure numpy fallback

# Collar (solve larger, crop back) and support-based resolution.
padded = surfit.pad_extent(extent, margin=20.0)
values, extent = surfit.crop_surface(values, padded, original_extent)
quality = surfit.resolution_report(extent, x=x, y=y, values=values)

# Measure an impulse response you already have (not an automatic solve).
psf = surfit.psf_report(values, extent, center=(x0, y0))
# psf["half_width"], psf["sigma"]
```

`surfit.select_parameter(build, x, y, z, parameters, ...)` runs the same
spatial CV for each candidate; the callback receives the candidate as its first
argument.  It is an outer search, not a new solver.

CRS helpers are optional and require `pyproj`:

```python
lon, lat = surfit.to_crs(x, y, "EPSG:4326", "EPSG:32637")
bounds = surfit.transform_extent(extent, "EPSG:4326", "EPSG:32637")
# transform_extent returns bounds only; rebuild the grid, do not assume
# an affine grid survives reprojection
```

## Generalised surfaces

For data that does not arrive as a file:

```python
task.add_points(x, y, z, weights=sigma_inv, name="p")
task.add_curves(x, y, name="line")
task.add_areas(x, y, name="zone")
task.add_contours(x, y, z, name="iso")
```

For raster exchange use `surfit.read_geotiff(path)` and
`surfit.save_geotiff_stack(directory, {name: array}, extent, crs=...)`.
North-up/cell-centre conventions are explicit; rotated rasters are rejected.

For grouped validation:

```python
surfit.cross_validate(build, x, y, z, mode="group", groups=group_id)
# folds=None means leave-one-group-out
```

For several ordered surfaces on one grid:

```python
stack = surfit.SurfaceStack("site")
stack.add_layer("top", build_top)
stack.add_layer("bottom", build_bottom)
stack.solve()
stack.report()["crossings"]
```

`SurfaceStack` is orchestration over independent Sessions; it is not a second
solver and does not turn surfit into a 3D modeller.  ``solve(parallel=True)``
fans independent layers out to a thread pool; ``thickness(name)`` and
``pinchout_mask(name)`` expose the relation between adjacent layers.
A solver-level relation is opt-in: the upper builder receives a
``SurfaceRelation`` and must call ``relation.apply(task)`` before the next
functional (for example before the points rule); the stack then solves
bottom-up and enforces ``top >= lower + min_thickness``.

For held-out calibration use ``conformal_quantile(residuals, level)`` and
``calibrated_interval(center, residuals, level)``.  Calibrate on held-out
residuals, not training residuals; call it a calibrated interval, not a
posterior.

## Files and examples

- Example data: `examples/surfit/tests/data`.
- Python examples: `examples/python`; each has a Tcl original in
  `examples/surfit/tests` (except `trend_from_numpy`, `progress`, `viewer`,
  `quality_workflow`, which is Python-only quality tooling).
- The regression runner keeps the two front ends byte-identical:
  `src/pysurfit/tests/run_tcl_suite.py`.

## Porting a Tcl script

One call maps to one call; the main differences are Python's explicit
`Session` and 0-based indexing:

```tcl
grid -12 12 0.2 -12 12 0.2
area_read "data/area1.txt" "area1"
area 10 "area1"
area_leq 20 "area6"
completer 1 1.6
surfit
```

```python
task = surfit.Session(map_name="map_area", tol=1e-6)
task.grid(-12, 12, 0.2, -12, 12, 0.2)
task.area_read("data/area1.txt", "area1")
task.area(10, "area1")
task.area_leq(20, "area6")
task.completer(1, 1.6)
task.solve()
```

Keep the order, especially for conditions. A plain `area` rule without a
following functional is a hard equality; `area_leq`/`area_geq` need the
functional after them.

## If the result looks empty

1. Check the return of every loader: `area_read`, `pnts_read`, `cntr_load_shp`
   return a list of flags or an empty list.
2. Check `area_size()` / `cntr_size()` / `curv_size()` / `pnts_size()`.
3. Confirm the data was loaded **after** `Session(...)`.
4. Check `defined_mask(grid).sum()` and the extent, not just `grid.min()`.
5. For area rules, check the returned flags; an empty list means the name did
   not match and the rule is not in the engine.

## Self-check

Before calling a change done, run the project selfcheck.  It validates the
skill frontmatter and local links, both documentation trees, and the public
Python surface:

```bash
python3 ci/selfcheck.py
```

It is fast; `ci/check.sh --full` remains the final gate.

This skill covers using the engine only; source build and release steps are
outside its scope.
