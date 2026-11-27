# 3D watch

The rule for now: **2.5D engine, 3D presentation**. The workbench may orbit,
exaggerate and inspect a surface in 3D, but it does not introduce a volume data
model or a voxel solver.

## Why

surfit represents a surface as one z value per (x, y). A 3D geological model
needs several values per (x, y), a volume/property model, or a mesh with
topology. That is a different engine, not a viewer feature.

## Triggers that would justify real 3D

Record a request here only when it cannot be solved by a better 2.5D view:

- several z values at the same (x, y) in one project;
- deviated wells / trajectories that pierce several surfaces;
- property values between horizons (not just isochores);
- volume clipping or arbitrary 3D cross-sections;
- faults that need a 3D fault network rather than a surface break;
- export to a 3D package that needs volume cells, not a surface mesh.

## Request log

| Date | Request | Workaround in 2.5D | Decision |
| --- | --- | --- | --- |
| 2026-11-26 | Initial scope review | Surface + stacked horizons + sections | Stay 2.5D; no engine work |

## Not a trigger

- orbiting the surface;
- vertical exaggeration;
- glTF/OBJ/STL export of a surface;
- several horizons viewed as a stack, as long as each remains a 2.5D grid.
