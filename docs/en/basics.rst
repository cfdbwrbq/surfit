Basics: what the words mean
===========================

This page is for a first reading. It says, in plain words, what each piece of
surfit is and where the same idea appears in real work. The links are DOI
references from :doc:`references`; where something is a design decision of
surfit rather than a research method, the source is the code and the tests, and
the text says so.

Grid, node, cell
----------------

**What it is.** A regular lattice of values, like a chessboard where every
square carries a height. A *node* is one square, a *cell* is one value.

**In surfit.** ``grid()`` sets the extent and the step; ``values()`` returns the
array; :doc:`data_types` has the exact conventions.

**Where it is used.** Every raster map: terrain models, geophysical fields,
climate grids. The step is a choice, not a property of the data.

**Read more.** Hengl (2006), *Finding the right pixel size*,
`doi:10.1016/j.cageo.2005.11.008 <https://doi.org/10.1016/j.cageo.2005.11.008>`_.

Points
------

**What it is.** Measurements at arbitrary places: wells, sample sites, sensors.

**In surfit.** ``read_points()`` loads a table, ``points()`` puts the surface
through the values, ``points_add()`` approximates them with a weight.

**Where it is used.** Environmental and soil sampling, geochemistry, meteorology
— anywhere a few measurements must become a map.

**Read more.** Li & Heap (2014), a review of interpolation in the environmental
sciences,
`doi:10.1016/j.envsoft.2013.12.008 <https://doi.org/10.1016/j.envsoft.2013.12.008>`_;
Shepard (1968), the inverse-distance method,
`doi:10.1145/800186.810616 <https://doi.org/10.1145/800186.810616>`_.

Curves and contours
-------------------

**What it is.** Lines that carry a value: an isoline, a river, a boundary. A
*contour* is a closed curve of constant value.

**In surfit.** ``curve()`` and ``contour()`` say that the surface equals a value
along the line; the same objects with ``fault()`` become discontinuities.

**Where it is used.** Digitised contour maps are still a major source of
elevation models; the interpolation must keep the shape between the lines.

**Read more.** Bek & Ježek (2011), *Optimization of interpolation parameters
when deriving DEM from contour lines*,
`doi:10.1007/s00477-011-0482-8 <https://doi.org/10.1007/s00477-011-0482-8>`_.

Surfaces and trends
-------------------

**What it is.** An existing grid used as a source of values, or as a large-scale
tilt under the local detail.

**In surfit.** ``surf_load()`` reads a surface, ``surface()`` makes the result
follow it, ``trend()`` fits a low-order surface and removes it.

**Where it is used.** Combining regional fields, geological and geophysical
mapping, where a broad trend is known before local data are added.

**Read more.** Hutchinson (1995), thin-plate smoothing splines for mean
rainfall,
`doi:10.1080/02693799508902045 <https://doi.org/10.1080/02693799508902045>`_;
Agterberg (2023), *Trend Surface Analysis*,
`doi:10.1007/978-3-030-85040-1_461 <https://doi.org/10.1007/978-3-030-85040-1_461>`_.

Areas
-----

**What it is.** A closed polygon that says "inside here, the surface is 10" (or
"undefined", or "pull it towards 20 with a weight").

**In surfit.** ``read_areas()``, ``area()``, ``area_add()``, ``area_mean()`` and
``area_wmean()``; the polygon is filled by rasterising its boundary onto the
grid, not by testing every cell against every edge.

**Where it is used.** Thematic maps: geological and soil units, land cover, zones
with a known value. The fill rule is a geometric problem, the "set a value here"
part is a design choice of the engine.

**Read more.** de Berg et al. (2008), point-in-polygon and triangulation,
`doi:10.1007/978-3-540-77974-2_1 <https://doi.org/10.1007/978-3-540-77974-2_1>`_;
Neteler & Mitasova (2008), raster and vector operations in a GIS,
`doi:10.1007/978-0-387-68574-8 <https://doi.org/10.1007/978-0-387-68574-8>`_.

Masks
-----

**What it is.** A stencil: apply a rule only where the mask says "yes".

**In surfit.** ``mask_load()`` reads a raster mask, ``mask()`` and the
``*_mask`` rules restrict other rules to it.

**Where it is used.** Limiting a model to a study area, excluding invalid or
missing data, combining several surveys with different footprints.

**Read more.** Neteler & Mitasova (2008), the GIS view of masks and rasters,
`doi:10.1007/978-0-387-68574-8 <https://doi.org/10.1007/978-0-387-68574-8>`_.

Faults
------

**What it is.** A line across which the surface may jump, like a cliff in a
terrain or a fault in a geological layer.

**In surfit.** ``fault()`` changes how neighbouring cells are coupled; the two
sides are interpolated independently and meet at the line.

**Where it is used.** Geological horizons cut by faults, seismic surfaces,
any field that is discontinuous but smooth on each side.

**Read more.** Maréchal (1984), kriging seismic data in the presence of faults,
`doi:10.1007/978-94-009-3699-7_17 <https://doi.org/10.1007/978-94-009-3699-7_17>`_;
Xue, Wu & Fomel (2018), spreading information across faults,
`doi:10.1190/int-2017-0171.1 <https://doi.org/10.1190/int-2017-0171.1>`_.

Inequalities
------------

**What it is.** A bound: "not below 80, not above 120", everywhere or at the
measured points.

**In surfit.** ``leq()``, ``geq()``, and the ``*_leq`` / ``*_geq`` variants,
solved by the penalty loop.

**Where it is used.** Physical limits: concentrations cannot be negative,
saturation has a ceiling, a detection limit is a bound rather than a
measurement.

**Read more.** Michalak (2008), inequality-constrained geostatistical
interpolation,
`doi:10.1029/2007WR006645 <https://doi.org/10.1029/2007WR006645>`_.

Averages and weights
--------------------

**What it is.** A condition on an average rather than on a cell: "the mean over
this area is 30"; with a weight surface, "the weighted mean is 30".

**In surfit.** ``mean()``, ``wmean()``, ``area_mean()``, ``area_wmean()``; they
are soft conditions, not hard values.

**Where it is used.** Mass balance and budgets, block averages over a region,
where a sum or a mean is known but the individual cells are not.

**Read more.** Cressie (2006), block kriging,
`doi:10.1007/s11004-005-9022-8 <https://doi.org/10.1007/s11004-005-9022-8>`_.

Histograms
----------

**What it is.** Match the distribution of the result to a target distribution,
instead of matching individual values.

**In surfit.** ``hist()`` takes a histogram and a weight, and adjusts the
surface so that its values follow that distribution.

**Where it is used.** Bias correction and quantile mapping: satellite or
climate-model fields are adjusted to the distribution of ground measurements.

**Read more.** Themeßl, Gobiet & Leuprecht (2011), empirical-statistical
downscaling and error correction,
`doi:10.1002/joc.2168 <https://doi.org/10.1002/joc.2168>`_; Maraun (2016), a
critical review of bias correction,
`doi:10.1007/s40641-016-0050-x <https://doi.org/10.1007/s40641-016-0050-x>`_.

Completer and smoothness
------------------------

**What it is.** Fill the gaps as smoothly as possible, as if a thin elastic
plate were bent through the data.

**In surfit.** ``completer(D1, D2)`` is the default between other rules; D1
penalises slope, D2 penalises curvature.

**Where it is used.** Everywhere between data; it is what makes the result a
surface rather than a patchwork.

**Read more.** Wessel & Bercovici (1998), splines in tension,
`doi:10.1023/A:1021713421882 <https://doi.org/10.1023/A:1021713421882>`_;
Briggs (1974), minimum curvature,
`doi:10.1190/1.1440410 <https://doi.org/10.1190/1.1440410>`_.

Priority and the order of rules
--------------------------------

**What it is.** Rules are applied in the order they are added; a rule does not
overwrite cells that an earlier rule has already solved.

**In surfit.** This is CMOFS, described in :doc:`how_it_works`. It is a design
decision of the engine, so the source is the code and the tests, not a paper; the
measured consequences are in :doc:`references`.

**Where it is used.** When conditions conflict: a hard area value versus a soft
completer, or a measured point versus a global bound.

Solvers and tolerance
---------------------

**What it is.** The rule system becomes one large sparse linear system; the
solver finds its vector of cell values.

**In surfit.** ``set_solver()`` chooses conjugate gradients or another method;
``tol`` is the step limit of that solver, not the error of the map.

**Where it is used.** Every solve; the choice matters for large grids and for
how close the result is to the exact solution.

**Read more.** Hestenes & Stiefel (1952), conjugate gradients,
`doi:10.6028/jres.049.044 <https://doi.org/10.6028/jres.049.044>`_; Saad (2003),
iterative methods for sparse systems,
`doi:10.1137/1.9780898718003 <https://doi.org/10.1137/1.9780898718003>`_.

Files and data sources
----------------------

**What it is.** surfit has its own ``.dat`` container; Surfer, GMT, GeoTIFF,
shapefile and others are exchange formats; SRTM is a source of elevation tiles.

**In surfit.** ``save()``/``load()`` for the native file, the ``*_save`` /
``*_load`` commands for the formats, ``dem_load_hgt()`` for SRTM tiles.

**Where it is used.** Moving data between surfit, a GIS and a plotting tool;
starting a terrain model from public elevation data.

**Read more.** Farr et al. (2007), the Shuttle Radar Topography Mission,
`doi:10.1029/2005RG000183 <https://doi.org/10.1029/2005RG000183>`_; Wessel & Smith
(1998), GMT,
`doi:10.1029/98EO00426 <https://doi.org/10.1029/98EO00426>`_; Rew & Davis (1990),
NetCDF,
`doi:10.1109/38.56302 <https://doi.org/10.1109/38.56302>`_.
