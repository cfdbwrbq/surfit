# surfit capabilities

A one-page, English summary.  The [Python guide](docs/en/python.rst) and the
[development notes](docs/en/development.rst) are the detailed references.

## Core

- builds a regular 2.5D grid from scattered data;
- values are constant inside a cell;
- interpolation and approximation, not only exact through-point fitting;
- one solve produces one surface on one grid;
- undefined cells carry `UNDEF_VALUE`.

### Data

Points XYZ; 2D curves; 3D contours (Z is the value); polygonal areas;
surfaces and trends; masks; histograms; DEM through the optional `globe`
module; faults as lines that the surface can jump across.

### Rules

- points: interpolation, weighted approximation, lower/upper bounds;
- curves and contours: value along the line, bounds, faults;
- areas: constant inside/outside, `undef`, mean, weighted mean, follow a
  surface, smoothing only inside, histograms, bounds;
- surfaces: follow, trend, anisotropy;
- masks: restrict a rule, cut holes, means and bounds;
- histograms: distribution fitting;
- `completer`: smoothing through D1 (slope) and D2 (curvature);
- inequality conditions, means and penalty constraints;
- rule order defines priority.

### Solver

- CMOFS: sequential minimisation of functionals;
- multilevel ladder: 8×8, then doubling;
- penalty loop for constraints;
- five iterative methods: `cg`, `jcg`, `rf`, `jacobi`, `ssor`;
- configurable tolerance, penalty iterations and multiplier;
- `tol` is a step tolerance, not a guaranteed error bound;
- thread-local engine state; independent tasks can solve in parallel.

### Output

Regular grid in memory; native surfit data file; Surfer GRD; GMT; Grass;
ArcGIS; xyz; shapefile; BLN; JPEG/BMP; NetCDF with an optional dependency;
save/load of a whole task, grid, masks and histograms.

## Python

### Task and grid

`Session`; `grid`, `grid_auto`, `grid_get`, `grid_get2`; `values()` returns a
numpy `(count_y, count_x)` array; `defined_mask`; `add_surface`;
`add_points`/`add_curves`/`add_areas`/`add_contours` from numpy; point weights;
`strict=True` for empty rule matches; `serial=True` for one worker;
`progress()` and `viewer()`.

All Tcl commands are also module functions and `Session` methods; the regression
runner compares Tcl and Python byte-for-byte.

### Quality and validation

Residuals (RMSE, bias, weighted MSE, chi², dof), outliers, robust weights and
outer IRLS, spatial CV (random, k-fold, block, group), leave-one-group-out,
smoothing selection by CV, per-node support, declustering (nearest, mean, min,
max, IDW), 2D polygonal Voronoi weights, typed point diagnostics,
GeoJSON/CSV, provenance reports with input hashes.

### Uncertainty

Bootstrap and block bootstrap ensembles, split-conformal quantiles,
symmetric/asymmetric calibrated intervals, empirical coverage, group coverage,
group-conformal quantiles, intervals in `SurfaceStack`, interval-conflict
checks on stack relations.

### Spatial diagnostics

Moran's I, experimental residual variogram, distance to nearest data, error by
distance band, bias/MAE/RMSE by group.

### Volumes, sections and integrations

Volumes between surfaces or to a contact, volumes by mask, P10/P50/P90 over
coherent realizations, `volume_ensemble`, `volume_percentiles`, stack
cross-sections with intervals and layers, `rule_report`, dip/azimuth and
gradient points, hard slope/curvature penalty conditions, GeoPandas/Shapely
(optional), CRS checks without silent reprojection, xarray Dataset and Zarr
(optional), regression trend + residual wrapper, coherent `SurfaceEnsemble`
arithmetic, JSON/YAML recipes and `surfit run`.

### SurfaceStack

Multiple layers on one grid; crossings, thickness, pinch-outs; DAG
relations `above`/`below`; minimum thickness; topological sort and cycle
detection; several conditions per layer; parallel solve of independent layers;
pinch-out projection `merge`/`undef`; `.npy` + `manifest.json`; memory-mapped
values and chunked report; typed `validate()`; per-layer provenance; calibrated
intervals and relation conflicts; benchmark direct/sequential/parallel.

### Raster and vector exchange

`read_geotiff` (north-up and rotated/west-up via GDAL warp),
`save_geotiff`, `save_geotiff_stack`, `save_geotiff_bands`, COG via GDAL,
`tifffile` fallback without GDAL, explicit CRS errors, north-up/cell-centre
conventions.  GeoParquet read/write without GDAL (optional `pyarrow` +
`shapely`); points, curves, polygons; exterior-only polygons.

### 3D export

`grid_mesh`, `export_gltf`, `export_obj`, `export_stl`, stack variants,
optional `to_pyvista()`.  Undefined/masked corners are skipped.  glTF uses one
embedded base64 buffer and maps Z-up to Y-up; OBJ has object groups; STL takes
one layer.  This is visualisation, not CAD.

### Large data

Tiled solve with overlap; memmap mosaic; memory-mapped stack layers; chunked
report; independent `Session` objects.

## Performance

The hot matvec uses the existing `sstuff` thread pool.  OpenMP was measured and
not adopted: 2.65× on 512² and 2.19× on 1024² at 8 workers, ~328% CPU,
assembly 25–31% of the time.  `pcg` is a diagonal-preconditioned prototype and
is slower than `cg` on the 512² benchmark.  Details and measurements are in
`docs/en/development.rst`.

## Limitations

- 2.5D only, no 3D voxel/octree; no CAD/mesh topology or CAD editor;
- no ML/property prediction, no GUI/map composition;
- slope/curvature are penalty conditions, not hard projections; mask bounds are
  exercised but tested numerically on an area;
- `rule_report` shows conditional residuals and recognized inequality
  violations; non-penalty data rules show `None`;
- P10/P50/P90 cannot be obtained by adding per-cell interval bounds;
- GeoPandas, xarray, Zarr, scikit-learn, GDAL, SciPy, pyproj, tifffile,
  PyVista, pyarrow and shapely are optional;
- FlatGeobuf is not included: the Python package has no writer;
- GCV is not implemented; the holdout L-curve is a heuristic, not GCV;
- variable grid spacing, spatially varying anisotropy, drainage enforcement,
  C++ contouring, stochastic simulation, lazy Dask and coupled cross-layer
  solves are deferred;
- Linux x86_64 is the supported wheel platform; GPL-2.
