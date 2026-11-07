---
name: surfit
description: >
  Use when writing or running a surfit gridding task: loading points, curves,
  contours, areas, surfaces or masks; defining rules; solving; reading the
  resulting grid; or debugging an empty/no-op result. This is the usage skill,
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

**Order matters:** `Session` resets the engine's process-wide state. Anything
loaded before the constructor is gone. `grid()` may be called before or after
the rules, but all data and rules must be created on that session.

## Grid and result conventions

- `grid(x0, x1, dx, y0, y1, dy)`; the result is `(count_y, count_x)` row-major.
- Row 0 is `min_y` (south edge), the last row is `max_y`.
- Undefined nodes carry `surfit.UNDEF_VALUE` (`FLT_MAX`). Select defined nodes
  with `surfit.defined_mask(grid)`; do not compare to `FLT_MAX` by hand.
- `task.values()` without a name returns the **most recently created surface**
  (normally the solve result). Use `task.values("name")` when the task holds
  several surfaces.
- `surf_extent(name)` returns the matching `min_x/max_x/min_y/max_y/step_x/step_y`.

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

task.set_metadata(crs="EPSG:32637", x_units="m", y_units="m")
task.save_metadata("result.meta.json")
```

`viewer()` is a 2-D filled contour map; `save_viewer(path)` writes it. For a
headless check, inspect `task.values()` and `defined_mask`, not the HTML.

## Files and examples

- Example data: `examples/surfit/tests/data`.
- Python examples: `examples/python`; each has a Tcl original in
  `examples/surfit/tests` (except `trend_from_numpy`, `progress`, `viewer`).
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

This skill covers using the engine only; source build and release steps are
outside its scope.
