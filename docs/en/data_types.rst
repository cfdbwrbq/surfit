Data types
==========

A task is a set of named objects — points, curves, contours, areas, surfaces,
masks, histograms and DEMs — solved on one grid. This page is the reference for
those types: what each one is, how it is loaded, and which rules accept it.
:doc:`commands` has the syntax of every command; :doc:`how_it_works` explains how
the rules are combined.

.. list-table::
   :header-rows: 1
   :widths: 15 26 37 22

   * - Type
     - What it is
     - Loaded with
     - Rule family
   * - points
     - irregularly spaced XYZ samples
     - ``read_points``, ``pnts_load``, ``pnts_load_shp``
     - ``points``, ``points_leq``, ``points_geq``
   * - curves
     - 2D polyline
     - ``read_curves``, ``curv_load``, ``curv_load_bln``, ``curv_load_shp``
     - ``curve``, ``curve_leq``, ``curve_geq``, ``fault``
   * - contours
     - 3D polyline; Z is part of the data
     - ``read_contours``, ``cntr_load``, ``cntr_load_bln``, ``cntr_load_shp``
     - ``contour``, ``contour_leq``, ``contour_geq``
   * - areas
     - polygon
     - ``read_areas``, ``area_load``, ``area_load_bln``, ``area_load_shp``
     - ``area``, ``area_leq``, ``area_geq``, ``area_mean``, ``area_wmean``, ``area_surf``
   * - surfaces
     - regular grid of Z values
     - ``surf_load``, ``surf_load_grd``, ``add_surface``
     - ``surface``, ``surface_leq``, ``surface_geq``, ``trend``
   * - masks
     - boolean grid
     - ``mask_load``
     - ``mask``, ``mask_leq``, ``mask_geq``, ``mask_mean``, ``mask_wmean``, ``mask_surf``
   * - grid
     - the cells the task is solved on
     - ``grid``, ``grid_auto``, ``grid_get``, ``grid_get2``
     - not a rule
   * - histograms
     - distribution of values
     - ``hist_read``, ``hist_from_surf``, ``hist_from_pnts``
     - ``hist``
   * - DEM
     - georeferenced raster from ``globe``
     - ``dem_load_hgt``, ``dem_load_grd``, ``dem_load_globe``, ``dem_load_dtm``
     - ``dem``, ``dem_add``

Points
------

Irregularly spaced XYZ samples. The ``points`` rule passes the surface through
them; ``points_add`` approximates them with a weight; ``points_leq`` and
``points_geq`` turn the measured values into bounds.

.. code-block:: python

   task.read_points("wells.txt", "wells")
   task.points("wells")

A points file is columned text; ``col1``..``col4``, the delimiter and the number
of header lines are arguments. Use ``points_add`` when the measurements are
noisy and the surface should approximate rather than interpolate.

Curves
------

A 2D polyline. The line itself carries no value, so the rule supplies one:
``task.curve(10, "iso1")`` makes the surface equal 10 along ``iso1``.
``curve_leq`` and ``curve_geq`` make that a bound, and ``curve_surf`` takes the
value from another surface instead of a constant.

.. code-block:: python

   task.read_curves("iso1.xy", "iso1")
   task.curve(10, "iso1")

The same data with the ``fault`` rule is a line the surface may jump across. A
fault adds no data; it changes how the neighbouring cells are coupled.

Contours
--------

A 3D polyline: every node has x, y and z, and the z is the measured value. The
contour rules therefore take no value argument — ``contour`` interpolates the
values along the line, and ``contour_leq`` / ``contour_geq`` use them as bounds.

.. code-block:: python

   task.read_contours("isolines.xyz", "iso")
   task.contour("iso")

A contour is the natural input for a digitised map: the value is known on the
line, and ``completer`` fills the space between the lines.

Areas
-----

A polygon. ``area`` sets a constant value inside it, ``area_mean`` and
``area_wmean`` an average, ``area_surf`` makes the surface follow another surface
there, and ``area_completer`` applies the smoothing rule inside the polygon only.
The value ``undef`` leaves the area out of the result.

.. code-block:: python

   task.read_areas("zone.txt", "zone")
   task.area(10, "zone")

Surfaces
--------

A regular grid of z values. The result of every task is one, and a surface can
also be an input: loaded from the native format, from a grid format, or handed
over as a numpy array. ``add_surface`` takes the array plus the origin and step
of its grid.

.. code-block:: python

   task.surf_load("regional.dat", "regional")
   task.surface("regional")

The array form is described in :doc:`python`; it is the shortest path from a
model grid to a trend surface.

Masks
-----

A grid of true and false values. It is not a surface: it restricts another rule
to the true cells. ``mask``, ``mask_leq``, ``mask_geq``, ``mask_mean``,
``mask_wmean`` and ``mask_surf`` are the variants; ``mask`` with the value
``undef`` cuts a hole in the result.

.. code-block:: python

   task.mask_load("mask.mask", "limit")
   task.mask("undef", "limit")

Masks are read from the native file and can be saved as a Surfer grid
(``mask_save_grd``) or xyz (``mask_save_xyz``).

Grid
----

The set of cells every rule is defined on. A task has one. ``grid`` creates an
explicit grid, ``grid_auto`` fits it to the loaded data (the Tcl ``grid``
command), ``grid_get2`` rounds the node counts up to powers of two, and
``grid_get_for_pnts`` fits a points dataset. The grid can be saved and loaded on
its own, or stored with the task.

.. code-block:: python

   task.grid(-10, 10, 0.25, -10, 10, 0.25)

Histograms
----------

A distribution of values. ``hist_read`` reads one from a columned text file with
a value range, ``hist_from_surf`` and ``hist_from_pnts`` build one from data, and
``hist_write`` saves it. The ``hist`` rule adjusts the surface so that its
histogram matches. Histograms are part of the native task file, so ``file_save``
and ``file_load`` keep them with the rest of the task.

.. code-block:: python

   task.hist_read("eq10.txt", 10, 40)
   task.hist("*")

Digital elevation models
------------------------

A DEM comes from the ``globe`` library: a raster with a georeference, so it can
be projected onto the task grid. ``dem`` makes the surface follow it and
``dem_add`` adds it with a weight. The model can be decomposed into coarser levels
and reconstructed: ``dem_decomp`` adds the next coarser level, ``dem_recons``
steps back one level and ``dem_full_recons`` returns to the original. The levels
are kept, so the original values come back exactly.

.. code-block:: python

   task.dem_load_hgt("N00E006.hgt")
   task.dem("N00E006.hgt")

DEM loaders take a file pattern rather than one path, and ``dem_load_hgt_zip``
needs zlib (the CMake build enables it when found). DEMs belong to the task: each
Session owns a container, so two tasks may load different rasters under the same
name, and the module-level calls use the library's own container;
:doc:`python` has the details. :doc:`terrain` reads an SRTM tile in both front
ends and shows what the two rules produce.

What they have in common
------------------------

* Every object is named, and every command selects objects by a shell pattern;
  ``"*"`` is the default, so ``task.points()`` uses all points in memory.
* Most rule families have three variants: the plain command adds a rule,
  ``_add`` adds it with a weight, and ``_leq`` / ``_geq`` turn it into an
  inequality.
* Every rule returns one flag per matched object, and ``[False]`` means the
  pattern matched nothing.
* The order in which rules are added is their priority; :doc:`how_it_works`
  describes what the solver does with that order.
* The result is a surface named by ``map_name``. ``file_save`` stores the whole
  task — data, rules and result — while ``surf_save`` stores one surface;
  :doc:`formats` lists the file formats.
