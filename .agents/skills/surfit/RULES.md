# surfit result rules

The surface is shaped by two kinds of rules:

- **data rules** pull the surface towards measurements (`points`, `contour`,
  `area`, `surface`, ...);
- **condition rules** put an equality or an inequality on the result
  (`leq`, `area_geq`, `mask_mean`, ...). Python calls them rules too, but they
  are conditions in the engine and are applied by the penalty loop.

## Equality and min/max, by target

| target | equality rule | lower / upper bound | mean |
|---|---|---|---|
| whole grid | `value(value)` | `geq(value)`, `leq(value)` | `mean(value)`, `wmean(value, surf)` |
| points | `points(name)` | `points_geq(name)`, `points_leq(name)` | — |
| area | `area(value, name)`, `area_add(value, weight, name)` | `area_geq(value, name)`, `area_leq(value, name)` | `area_mean(value, name)`, `area_wmean(value, name, surf)` |
| contour | `contour(name)`, `contour_add(weight, name)` | `contour_geq(name)`, `contour_leq(name)` | — |
| curve | `curve(value, name)`, `curve_add(value, weight, name)` | `curve_geq(value, name)`, `curve_leq(value, name)` | — |
| mask | `mask(value, name)`, `mask_add(value, weight, name)` | `mask_geq(value, name)`, `mask_leq(value, name)` | `mask_mean(value, name)`, `mask_wmean(value, name, surf)` |
| other surface | `surface(name)`, `surface_add(weight, name)` | `surface_geq(name)`, `surface_leq(name)` | — |
| area vs surface | `area_surf(surf, area)`, `area_surf_add(surf, weight, area)` | `area_surf_geq(surf, area)`, `area_surf_leq(surf, area)` | — |
| curve vs surface | `curve_surf(surf, curve)`, `curve_surf_add(...)` | `curve_surf_geq(surf, curve)`, `curve_surf_leq(surf, curve)` | — |
| mask vs surface | `mask_surf(surf, mask)`, `mask_surf_add(...)` | `mask_surf_geq(surf, mask)`, `mask_surf_leq(surf, mask)` | — |

`value` is a real number; `name="*"` selects all datasets of that type. Area
and mask conditions accept `inside` (default `1`); `inside=0` applies the
condition outside the polygon/mask.

## What the direction means

- `geq` / `area_geq` / `mask_geq`: result at the target is **greater than or
  equal** to the value (a floor).
- `leq` / `area_leq` / `mask_leq`: result at the target is **lower than or
  equal** to the value (a ceiling).
- `points_geq` / `points_leq` compare the surface with the loaded point values,
  not with a literal: the surface stays above/below the measurements.
- `contour_geq` / `contour_leq` compare the surface with the contour values
  along the loaded contour lines.
- `surface_geq` / `surface_leq`, `area_surf_*`, `curve_surf_*`,
  `mask_surf_*` compare the result with **another loaded surface**.
- `*_mean` constrains the mean over the target, not every node; `*_wmean`
  weights that mean by another surface.

## Penalty, not a hard clip

All `*_leq` / `*_geq` calls are conditions solved by penalties. They are not a
post-processing clamp: the final surface can still violate a bound slightly.
`penalty_factor` controls the penalty multiplier; the default `0` means "use
the engine's default", not "disabled". Check the result:

```python
task.solve()
print(task.surf_area_minz("area6", "result"))
print(task.surf_area_maxz("area6", "result"))
```

For an exact value use the equality rule (`area`, `area_add`), not an
inequality. `area_add` is a weighted equality, so it is approximate by design.

## Conditions need a functional after them

In the engine a condition is attached to the next functional rule by the
penalty pass. Put the condition before the rule that should carry it:

```python
task.area(30, "area3")
task.area_leq(20, "area6")     # condition
task.area_geq(15, "area6")     # condition
task.area(10, "area1")         # functional that carries the two conditions
task.completer(1, 0)
```

A condition left at the end, or called after all functionals, may never be
solved. The log is the evidence: look for `creating gridding rule ...` and
`inequality for area ...` during the solve.

## Area conditions are silent on a bad name

`area_leq` / `area_geq` / `area_mean` return one flag per matched area and an
empty list when the name matches nothing. They do not raise. Create the
`Session` first, load areas through it, and check the return:

```python
task = surfit.Session(map_name="result", tol=1e-6)
task.area_read("area6.txt", "area6")
assert task.area_leq(20, "area6")   # not []
assert task.area_geq(15, "area6")
```

`task.names()` is surfaces only. Areas are `surfit.area_size()` and
`surfit.area_getName("*")`.

## Minimal working sets

```python
# global floor and ceiling
task = surfit.Session(map_name="bounds", tol=1e-6)
task.grid(0, 100, 1, 0, 100, 1)
task.points("wells")
task.geq(0)          # result >= 0
task.leq(100)        # result <= 100
task.solve()

# area band: area6 stays in [15, 20]
task = surfit.Session(map_name="band", tol=1e-6)
task.area_read("area6.txt", "area6")
task.grid(0, 100, 1, 0, 100, 1)
task.area_leq(20, "area6")
task.area_geq(15, "area6")
task.area(10, "area1")     # a functional after the conditions
task.completer(1, 0)
task.solve()

# floor where a mask is true
task.mask_read("mask.txt", "m")
task.mask_geq(-10, "m")
```

Worked examples: `examples/python/area_ineq.py`, `mask_ineq.py`,
`points_ineq.py`, `surface_ineq.py`, `area_mean.py`, `area_wmean.py`,
`mask_mean.py`, `mask_wmean.py`, `mean.py`, `wmean.py`.

## Rules that are not min/max

`completer`, `trend`, `fault`, `area_completer`, `mask_completer` and
`area_hist` shape the result but are not bounds. Keep them in the same order as
the Tcl original when porting.
