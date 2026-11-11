# Roadmap: layered surface systems

This is the product roadmap for generalising surfit from one surface per task
to an ordered system of related surfaces.  The detailed design is in
[SURFACE_STACK_PLAN.md](SURFACE_STACK_PLAN.md).

## Vision

surfit remains a 2.5D gridding engine.  Around the solver it gains a small data
and orchestration layer:

```
data -> one or more Sessions -> SurfaceStack -> report / raster stack / manifest
```

The solver is unchanged.  The new layer makes several surfaces usable together:
ordered layers, relations, grouped validation, calibrated uncertainty and a
reproducible exchange format.

## Done

| Capability | Status |
|---|---|
| array ingestion (`add_points`, curves, areas, contours) | done |
| GeoTIFF reader, stack writer, manifest | done |
| grouped cross-validation and per-group metrics | done |
| ordered `SurfaceStack`, crossings, thickness, pinch-outs | done |
| solver-level `SurfaceRelation` with minimum thickness | done |
| pinch-out projection (`merge`/`undef`) | done |
| parallel stack solve and timings | done |
| split-conformal quantile and calibrated interval | done |
| direct/sequential/parallel benchmark | done |
| stack persistence (`.npy` layers + `manifest.json`) | done |

## Next

### 1. Coverage report and group-conformal calibration

Add:

- empirical coverage of calibrated intervals;
- asymmetric intervals;
- group-conformal calibration from the same groups used by CV;
- per-layer coverage in the stack report.

Why: an interval that is not checked for coverage is only a number.

### 2. Constraint graph

The current relation is linear (`above` the next lower layer).  Generalise to a
small DAG:

- a layer may be above one surface and below another;
- non-adjacent relations;
- cycle detection and topological solve;
- soft relations with weights.

Why: real stacks contain lenses, wedges and non-neighbour constraints.

### 3. Memory-mapped stack

Keep layer values on disk:

- `SurfaceStack` values backed by `memmap`;
- report crosses/thickness without loading everything;
- benchmark 20–50 layers;
- explicit `close()` for the mapping.

Why: the current stack holds every layer in RAM.

### 4. Native array constructors

`add_points`/`add_curves` currently use a temporary columned file.  A native
C++/pybind path would remove the I/O and preserve names/weights without a round
trip.

### 5. Raster polish

- `tifffile` fallback when GDAL is absent;
- multi-band stack without the per-layer manifest workaround;
- COG/overviews.

### 6. Release

After coverage and persistence are stable, cut a minor release; keep the
versioning honest about the new public API.

## Non-goals

- 3D voxel/octree models;
- mesh/CAD export;
- property prediction or multimodal fusion;
- a GUI or map-composition tool;
- a second interpolation solver;
- mandatory heavy dependencies.

## Milestones

1. **M1 — usable stack**: persistence, coverage, docs, tests.
2. **M2 — general relations**: DAG, cycle checks, soft weights.
3. **M3 — scale**: memory-mapped stack, batch benchmark.
4. **M4 — release**: version bump, release notes, wheels, docs archive.
