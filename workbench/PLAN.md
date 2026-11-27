# surfit surface workbench — MVP plan

A local, single-user web workbench around the surfit engine.  No QGIS, no
PostGIS, no map server: drop points, contours, faults, areas and optional
surfaces, choose grid and rule settings, solve, inspect in 3D, download the
result.

The MVP scope below is implemented, except where explicitly listed as out of
scope.  Native `.mask` files are not supported; polygonal masks use area
`undef`.

## Scope

- upload points CSV/XYZ, contours, fault lines, polygons and surfaces;
- auto or manual extent;
- cell size, tolerance, solver;
- points + completer + optional lower/upper bounds;
- solve in a worker thread with one Session per job;
- 3D surface, points and faults in the browser;
- vertical exaggeration and colour ramp;
- download `.dat` and glTF;
- save/load local projects with sources, settings and result;
- enable/disable individual source files without deleting them;
- delete individual points from CSV/XYZ and GeoJSON sources;
- delete contour/fault lines from CSV/XYZ and GeoJSON sources;
- cross-section profile along user-specified A/B endpoints;
- JSON report download with settings, sources, metrics and section;
- portable project archive export/import;
- SHP via bundled pyshp (direct .shp or zipped sidecars) with field selection;
- schema endpoint and dropdowns for DBF/GeoJSON fields;
- polygon areas with constant/bounds/undef/mean/add rules and reordering;
- global mean, weighted mean and trend rules using uploaded surfaces;
- explicit ordering of all rule groups, not only areas;
- inclusive value range and optional zero exclusion;
- automatic cell size (about 200 cells across the longest extent);
- quality panel for the rule report (residual, penalty iterations, violations);
- limits and TTL cleanup.

Out of scope for MVP: users/auth, polygon editing, PostGIS, jobs surviving
restart, large-data streaming, WASM.  Local projects and their archives are in
scope.

## Architecture

```text
browser (three.js)
   |  multipart upload + JSON
FastAPI
   |  job registry, limits, TTL
worker thread
   |  surfit.Session
grid + mesh JSON / .dat / glTF
```

- one process;
- `ThreadPoolExecutor(max_workers=1)` by default: the engine has its own thread
  pool, so avoid nested oversubscription;
- one temporary directory per job;
- no database;
- `GET /api/jobs/{id}` is polled by the page.

## API

- `POST /api/preview` — source summary for the map and field dropdowns.
- `POST /api/schema` — fields per source role.
- `POST /api/jobs` — points/contours/faults/areas/surfaces, grid settings,
  area/global rules and rule order; returns id.
- `GET /api/jobs/{id}` — status, timings, limits, errors, metrics.
- `GET /api/jobs/{id}/mesh` — vertices/faces and source geometry for three.js.
- `GET /api/jobs/{id}/download.dat` — native surfit result.
- `GET /api/jobs/{id}/download.gltf` — glTF export.
- `GET /api/projects` and project CRUD/archive/import endpoints.
- `GET /api/health`.

See `backend/app.py` for the complete route list.

## Acceptance

- a 5k-point dataset solves and renders in under a minute on a laptop;
- 3D orbit works without a build step;
- undefined cells are holes, not zero;
- the page shows the real residual/undefined count, not only a picture;
- a malformed/oversized upload returns a clear error.
