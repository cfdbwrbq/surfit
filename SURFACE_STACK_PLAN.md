# Generalising surfit: layered surface systems

## Why

surfit currently has one primary shape:

```
one Session -> one grid -> one surface
```

That is a good solver boundary, but many real workflows are a **system of
related surfaces**: roofs and bases, stacked horizons, bathymetric surfaces,
soil horizons, or a time series of regional fields.  The missing generality is
not another interpolation kernel; it is the data, validation and orchestration
around several surfaces.

This plan generalises surfit without turning it into a GIS, a 3D modeller or a
domain application.

## Capability ladder

| Plane | Current | General target |
|---|---|---|
| Ingestion | columned text files | arrays, tables and rasters |
| Model | independent Sessions | an ordered surface stack |
| Constraints | within one surface | relations between surfaces |
| Validation | random / block CV | grouped and hierarchical CV |
| Uncertainty | ensemble spread | calibrated quantiles and coverage |
| Exchange | one grid | raster stack + manifest |
| Execution | one solve | batch/memory-mapped stack |

The solver stays 2.5D and keeps producing one regular grid per layer.

## P0 — thin, high-value additions

### P0.1 Array and table ingestion

- `Session.add_points(x, y, z, weights=None, name=...)`
- `Session.add_curves(x, y, name=...)`
- `Session.add_areas(x, y, name=...)`
- `Session.add_contours(x, y, z, name=...)`
- an optional DataFrame/Arrow adapter at the edges, not in the core

Acceptance: a caller can build a task from numpy arrays without writing an
intermediate text file, and the data survives `file_save`/`file_load`.

### P0.2 Raster input/output

- `read_geotiff(path, band=1)` returning values, extent and CRS;
- explicit north-up/cell-centre/tiepoint convention;
- `save_geotiff_stack` for several layers: one file per layer or a multi-band
  file with band descriptions;
- optional GDAL, with a clear ImportError; no mandatory GDAL.

Acceptance: a round trip preserves values, extent, CRS, nodata and layer names;
a stack can be written and read back without a private format.

### P0.3 Group-aware validation

- `cross_validate(..., mode="group", groups=...)`;
- leave-one-group-out when `folds=None`;
- per-group RMSE, median, p90, MAE and coverage;
- worst-group report;
- `select_parameter` passes groups through.

Acceptance: no group appears in both train and test; a deliberately bad group is
visible in the report.

### P0.4 Surface stack orchestrator

A Python-level `SurfaceStack` over independent Sessions:

```python
stack = surfit.SurfaceStack("site", extent=..., step=...)
stack.add_layer("roof", session_factory)
stack.add_layer("base", session_factory)
stack.solve()
stack.report()
```

It must provide:

- stable layer order;
- a shared extent/step contract;
- per-layer support and diagnostics;
- crossings before/after;
- thickness statistics;
- pinch-out/absent-layer counts;
- a manifest with inputs, parameters and versions.

Acceptance: a stack of three synthetic surfaces solves and reports crossings,
thickness and pinch-outs without hand-written post-processing.

## P1 — constraints and uncertainty

### P1.1 Relations between surfaces

- `above` / `below` relations;
- minimum thickness;
- soft versus hard constraints;
- explicit absent-layer semantics.

These are geometry constraints, not a domain model.  They complement
`surface_leq/geq`, which only compare one surface to a constant or another
surface.

### P1.2 Pinch-out semantics

- zero-thickness merge;
- explicit undefined mask;
- reporting which cells are absent because of geometry and which because of
  missing data.

### P1.3 Calibrated uncertainty

- combine block bootstrap with conformal calibration from spatial/group CV;
- p05/p50/p95 and empirical coverage;
- label as calibrated ensemble interval, not posterior.

### P1.4 Batch and stack execution

- solve many layers and many extents with a shared grid;
- memory-mapped stack;
- deterministic ordering and per-layer progress;
- benchmark against a full in-memory solve.

### P1.5 Diagnostics and docs

- group ids in point diagnostics and per-group summaries;
- a “layered surfaces” tutorial;
- an honest scope note: what is a 2.5D stack and what is not.

## Non-goals

- 3D voxel/octree models;
- mesh/CAD export;
- property prediction or multimodal fusion;
- kriging covariance as a required feature;
- a GUI or map-composition tool;
- domain-specific classification.

Those belong to adapters or downstream tools, not to the gridding core.

## Design rules

1. Keep the solver and its 2.5D contract unchanged.
2. A stack is orchestration over Sessions, not a second solver.
3. Every new object must have a typed failure path and a manifest entry.
4. Optional dependencies remain optional and raise a clear ImportError.
5. Independent `Session` remains the primitive; the stack must not become
   mandatory.
6. Tests use synthetic layered fields, so the plan does not depend on a
   particular dataset.
