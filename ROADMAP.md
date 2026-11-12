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
| constraint DAG, `add_relation`, cycle detection | done |
| pinch-out projection (`merge`/`undef`) | done |
| parallel stack solve and timings | done |
| split-conformal quantile and calibrated interval | done |
| coverage report and group-conformal quantiles | done |
| direct/sequential/parallel benchmark | done |
| stack persistence (`.npy` layers + `manifest.json`) | done |
| memory-mapped stack values and `load(..., mmap=True)` | done |

## Next

### 1. Native array constructors

`add_points`/`add_curves` currently use a temporary columned file.  A native
C++/pybind path would remove the I/O and preserve names/weights without a round
trip.

### 2. Raster polish

- `tifffile` fallback when GDAL is absent;
- multi-band stack without the per-layer manifest workaround;
- COG/overviews.

### 3. Release

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
