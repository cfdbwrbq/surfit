# Competitive review and feature plan

Research date: 2026-11-10. Sources are linked below; estimates are rough
engineer-days and assume the current 3.2.0 tree.

## What was reviewed

- **Surfer 10–30** (Golden Software), including the 2025/2026 releases;
- **Topo to Raster** — this is ESRI's implementation of ANUDEM, not a product
  called "Topo2raster"; treat it as one algorithm;
- **RockWorks**, **Leapfrog Geo**, **Petrel**, **Oasis montaj**, **Isatis.neo**;
- open-source/scientific tools: GMT, SAGA GIS, GRASS GIS, QGIS, PyKrige,
  scikit-gstat, Verde, gstools, GemPy, GDAL/rasterio;
- peer-reviewed reviews and benchmarks on spatial interpolation, validation and
  uncertainty.

## Headline findings

1. **Surfer has not added a new interpolation family since 2019.** Its
   thirteen methods are the classic set: IDW, kriging, cokriging, minimum
   curvature, natural neighbour, nearest neighbour, polynomial regression,
   RBF, modified Shepard, triangulation + linear, moving average, local
   polynomial and Data Metrics. Cokriging (v17, 2019) and kriging with external
   drift (v16, 2018) are the only new estimators in the period. The 2011–2026
   investment went into 3D views, drillholes, CRS/file formats and basemaps,
   not geostatistics.
2. **Uncertainty is thin in commercial mapping tools.** Surfer offers a kriging
   standard-deviation grid, and its own documentation documents cases where it
   is meaningless or misleading. Conditional simulation lives in specialist
   tools (Leapfrog Edge, Isatis), not in mainstream Surfer.
3. **"Topo to Raster" is worth studying for diagnostics, not for a new solver.**
   ANUDEM is an iterative thin-plate spline with drainage enforcement, lakes,
   cliffs and typed error geometries. The typed errors are the useful part:
   sink points, scaled residual points and contour-error points with error codes.
4. **RockWorks has several cheap, practical ideas**: hybrid gridding (a weighted
   blend of methods), dip/dip-direction bias, declustering, densification and a
   "faulted" distance multiplier instead of a hard barrier.
5. **Open source is stronger on honest validation and interoperability than on
   new interpolation math.** GRASS/SAGA/Verde expose cross-validation and block
   folds; GDAL provides CRS, COG, Zarr and windowed I/O; gstools/PyKrige cover
   variograms and kriging; GMT documents the need for block averaging before
   gridding.
6. **The literature does not support a universal "best" interpolator.** Method
   rankings are data-specific. The defensible gains are spatial (block) CV,
   uncertainty that respects spatial dependence, variogram/resolution
   diagnostics and standards-grade metadata.
7. **Do not chase 3D voxel/GUI/map composition, cloud or end-to-end ML.** They
   are outside surfit's headless 2.5D model, expensive, and none of the
   commercial release notes show ML interpolation as a documented gridding
   feature.

## What surfit already has

CMOFS with ordered rules, thin-plate D1/D2 energy, inequalities, faults, areas,
curves, contours, trend surfaces, anisotropy, per-point weights, threaded
parallel Sessions, tiled point solves, residuals/chi-square/MAD, Huber/Tukey
outer IRLS, bootstrap ensembles, a quality report, GeoTIFF and metadata.

What it does **not** have: variogram analysis, kriging or kriging variance, a
reusable spatial-CV API, a per-node QC attribute stack, CRS reprojection, CF
metadata, NetCDF/COG output, padding/collar, or a resolution diagnostic.

## Plan

### P0 — honest quality control and interoperability (1–2 weeks)

| # | Feature | Why | Effort | Acceptance |
|---|---|---|---|---|
| 1 | **Spatial CV API** | Random k-fold overstates accuracy for clustered data; every serious peer exposes a CV mode. | 2–4 d | `Session.cross_validate(mode="random"\|"kfold"\|"block", blocks=...)` returns per-fold RMSE, bias, coverage and geometry; report includes it; tested on a clustered synthetic field. |
| 2 | **Standards-grade provenance** | A JSON sidecar is not enough for GIS/NetCDF pipelines. | 2–4 d | `report()`/sidecar records EPSG/WKT2, units, `grid_mapping`, nodata, engine version, solver parameters, input SHA-256 and CV scores; GeoTIFF carries the CRS. |
| 3 | **Per-node QC stack** | Users need to know where the grid is unreliable, not only a global RMSE. | 3–5 d | Optional arrays: data count per cell, min/mean distance to data, sum of weights, sum of negative weights; returned in `quality()` and written to the report. |
| 4 | **Duplicate/decluster policy** | Line and cluster sampling silently biases the fit. | 2–3 d | `points_decluster(method="mean"\|"nearest"\|"idw"\|"min"\|"max")`; raw points remain available for residual statistics; report states the policy. |

### P1 — geostatistical diagnostics and honest uncertainty (2–4 weeks)

| # | Feature | Why | Effort | Acceptance |
|---|---|---|---|---|
| 5 | **Variogram front-end** | Turns `alpha`/`w` and grid step from guesses into measurements; does not require a second solver. | 5–8 d | Experimental/directional/robust variogram, model fit, range/sill/nugget/anisotropy; helper proposes `alpha`/`w` and CV block size. No kriging yet. |
| 6 | **Block bootstrap + conformal calibration** | i.i.d. bootstrap breaks spatial dependence and understates spread. | 4–6 d | `bootstrap_uncertainty(..., block=...)`; split-conformal intervals from spatial CV; empirical coverage test; docs say "ensemble spread / calibrated interval", not posterior. |
| 7 | **Typed diagnostic geometry** | Surfer/ANUDEM-style "which contour or point is wrong" is more useful than a boolean mask. | 3–5 d | Residual points scaled by local error, contour-error points with codes, direction-conflict codes for curves/faults; CSV/GeoJSON output. |
| 8 | **CRS/reprojection helper** | Silent lon/lat gridding is a real failure mode; the engine stays Cartesian. | 2–4 d | Optional `pyproj` helper for points/extent (densify corners); refuse degree units where anisotropy matters; GeoTIFF/NetCDF carry the result. |

### P2 — scale and novelty (4–10 weeks)

| # | Feature | Why | Effort | Acceptance |
|---|---|---|---|---|
| 9 | **Padding/collar and scale-aware thinning** | Edge artifacts and density contrasts are known bathymetry problems; "stacked" splines are the reference. | 3–5 d | `padding` setting with taper; tests show lower edge RMSE on a synthetic field; optional weighted block thinning before solve. |
| 10 | **Tiled solver beyond points** | Curves/contours/areas with halo would beat point-only tiling; faults are hardest. | 2–4 wk | Curves/contours solve tiled and match the non-tiled hash; faults explicitly deferred until alignment is proven. |
| 11 | **Resolution diagnostic (PSF)** | The most genuinely new idea: report what the actual estimator can resolve. | 2–4 wk | Impulse-response or stochastic estimate of point-spread characteristic length; report warns when grid step is below resolution. |
| 12 | **Automatic smoothing selection** | Manual `tol`/weights are the main tuning burden; REML/GCV is standard in `mgcv`. | 2–4 wk | Outer search over the common "points + completer" case, selected by spatial CV; no refactor of CMOFS required for the first version. |

### Explicitly deferred or rejected

- **Kriging as a core solver.** Spline/kriging equivalence covers common
  covariance choices, Surfer's kriging has been frozen since 2019, and a second
  solver would duplicate CMOFS. Revisit only if users bring a covariance model
  that CMOFS cannot express; variogram diagnostics and CV come first.
- **Surfer's thirteen named methods.** Moving average, local polynomial,
  modified Shepard and polynomial regression are already expressible as rules;
  adding names would be imitation, not capability.
- **3D voxel grids, sections, map composition, GUI, cloud, end-to-end ML.**
  Different products; high cost, poor fit.
- **Full Bayesian SPDE/INLA and deep-learning interpolation.** Large
  integration, weak auditability; not a 3.x priority.

## Sequencing

1. P0.1 + P0.2 (CV and provenance) — these make every later claim measurable.
2. P0.3 + P0.4 (QC stack and declustering) — visible quality.
3. P1.5 + P1.6 (variogram and block bootstrap) — the highest-value pair.
4. P1.7 + P1.8 (typed errors, CRS) — interoperability.
5. P2.9 + P2.10 (padding/collar, tiled curves) — scale.
6. P2.11 + P2.12 (resolution, smoothing) — research bets.

## Sources

Commercial:

- [Surfer gridding methods summary](https://support.goldensoftware.com/hc/en-us/articles/226628127-Summary-of-gridding-methods-available-in-Surfer)
- [Surfer version history](https://support.goldensoftware.com/hc/en-us/articles/228069868-Surfer-Version-History)
- [Surfer kriging options](https://surferhelp.goldensoftware.com/griddata/idd_grid_data_kriging.htm)
- [Surfer cross-validation](https://surferhelp.goldensoftware.com/griddata/grid_data_cross_validation.htm)
- [Surfer Python automation policy](https://support.goldensoftware.com/hc/en-us/articles/226625748-Use-Python-to-automate-Surfer)
- [How Topo to Raster works](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/3d-analyst/how-topo-to-raster-works.html)
- [RockWorks gridding methods](http://help.rockware.com/rockworks/WebHelp/grid_methods.htm)
- [Leapfrog Geo manual](https://help.seequent.com/Geo/4.3/en-GB/LeapfrogGeoUserManual.pdf)

Open source:

- [GMT surface](https://docs.generic-mapping-tools.org/6.7/surface.html)
- [SAGA kriging](https://saga-gis.sourceforge.io/saga_tool_doc/9.12.0/statistics_kriging_0.html)
- [GRASS v.surf.rst](https://grass.osgeo.org/grass85/manuals/v.surf.rst.html)
- [QGIS interpolation](https://docs.qgis.org/3.44/en/docs/user_manual/processing_algs/qgis/interpolation.html)
- [PyKrige](https://geostat-framework.readthedocs.io/projects/pykrige/en/stable/)
- [scikit-gstat](https://scikit-gstat.readthedocs.io/en/latest/)
- [Verde](https://www.fatiando.org/verde/latest/)
- [gstools](https://geostat-framework.readthedocs.io/projects/gstools/en/stable/)
- [GDAL COG](https://gdal.org/en/stable/drivers/raster/cog.html)

Literature:

- Li & Heap (2011), [doi:10.1016/j.ecoinf.2010.12.003](https://doi.org/10.1016/j.ecoinf.2010.12.003)
- Li & Heap (2014), [doi:10.1016/j.envsoft.2013.12.008](https://doi.org/10.1016/j.envsoft.2013.12.008)
- Roberts et al. (2017), [doi:10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881)
- Pohjankukka et al. (2017), [doi:10.1080/13658816.2017.1346255](https://doi.org/10.1080/13658816.2017.1346255)
- Wadoux et al. (2021), [doi:10.1016/j.ecolmodel.2021.109692](https://doi.org/10.1016/j.ecolmodel.2021.109692)
- Chiao et al. (2014), [doi:10.1002/2013JB010364](https://doi.org/10.1002/2013JB010364)
- Hell & Jakobsson (2011), [doi:10.1007/s11001-011-9141-1](https://doi.org/10.1007/s11001-011-9141-1)
- Wood (2011), [doi:10.1111/j.1467-9868.2010.00749.x](https://doi.org/10.1111/j.1467-9868.2010.00749.x)
- CF Conventions 1.13, [cfconventions.org](https://cfconventions.org/Data/cf-conventions/cf-conventions-1.13/cf-conventions.html)
- OGC GeoTIFF 1.1, [docs.ogc.org](https://docs.ogc.org/is/19-008r4/19-008r4.html)
