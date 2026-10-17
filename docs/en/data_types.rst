Data types
==========

surfit works on a small set of data types. Every object in a task is named,
kept in memory, selected by a shell pattern, and written to the native task
file; a gridding rule names the type it applies to. This page describes the
types and points to the rule families; :doc:`commands` has every command with
its arguments.

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

Scattered samples are what most tasks start from. The ``points`` rule passes
the surface through them; ``points_add`` adds the same condition with a weight,
and ``points_leq`` / ``points_geq`` turn the measured values into bounds:

.. code-block:: python

   task.read_points("wells.txt", "wells")
   task.points("wells")

A points file is a columned text file; ``col1``..``col4``, the delimiter and the
number of header lines are arguments. ``points_add`` is the rule to reach for
when the measurements are noisy and the surface should approximate rather than
interpolate.

Curves
------

A curve is a 2D polyline: the line itself carries no value, so the rule supplies
one. ``curve 10 iso1`` means the surface equals 10 along ``iso1``.
``curve_leq`` / ``curve_geq`` make that a bound, and ``curve_surf`` takes the
value from another surface instead of a constant:

.. code-block:: python

   task.read_curves("iso1.xy", "iso1")
   task.curve(10, "iso1")

The same data with the ``fault`` rule is a line the surface may jump across.
A fault does not add data; it changes how the neighbouring cells are coupled.

Contours
--------

A contour is a 3D polyline: every node has x, y and z, and the z is the measured
value. That is why the contour rules take no value argument: ``contour``
interpolates the values along the line, and ``contour_leq`` / ``contour_geq``
use them as bounds:

.. code-block:: python

   task.read_contours("isolines.xyz", "iso")
   task.contour("iso")

A contour is the natural input for anything digitised from a map: the line is
where the value is known, and the space between the lines is filled by
``completer``.

Areas
-----

An area is a polygon. ``area`` sets a constant value inside it,
``area_mean`` / ``area_wmean`` an average, ``area_surf`` makes the surface
follow another surface there, and ``area_completer`` applies the smoothing rule
inside the polygon only. The value ``undef`` leaves the area out of the result:

.. code-block:: python

   task.read_areas("zone.txt", "zone")
   task.area(10, "zone")

Surfaces
--------

A surface is a regular grid of z values. The result of every task is one, and a
surface can also be an input: loaded from the native format, from one of the
grid formats, or handed over as a numpy array. ``add_surface`` takes the array
plus the origin and step of its grid:

.. code-block:: python

   task.surf_load("regional.dat", "regional")
   task.surface("regional")

The array form is described in :doc:`python`; it is the shortest path from a
model grid to a trend surface.

Masks
-----

A mask is a grid of true and false values. It is not a surface: it restricts
another rule to the true cells. ``mask``, ``mask_leq``, ``mask_geq``,
``mask_mean``, ``mask_wmean`` and ``mask_surf`` are the variants; ``mask`` with
the value ``undef`` cuts a hole in the result:

.. code-block:: python

   task.mask_load("mask.mask", "limit")
   task.mask("undef", "limit")

Masks are read from the native file and can be saved as a Surfer grid
(``mask_save_grd``) or xyz (``mask_save_xyz``).

Grid
----

The grid is the set of cells every rule is defined on, and a task has one.
``grid`` creates an explicit grid, ``grid_auto`` fits it to the loaded data
(the Tcl ``grid`` command), ``grid_get2`` rounds the node counts up to powers of
two, and ``grid_get_for_pnts`` fits a points dataset. The grid can be saved and
loaded on its own, or stored with the task:

.. code-block:: python

   task.grid(-10, 10, 0.25, -10, 10, 0.25)

Histograms
----------

A histogram is a distribution of values. ``hist_read`` reads one from a
columned text file with a value range, ``hist_from_surf`` and
``hist_from_pnts`` build one from data, and ``hist_write`` saves it. The
``hist`` rule adjusts the surface so that its histogram matches. Histograms are
part of the native task file, so ``file_save`` and ``file_load`` keep them with
the rest of the task:

.. code-block:: python

   task.hist_read("eq10.txt", 10, 40)
   task.hist("*")

Digital elevation models
------------------------

A DEM comes from the ``globe`` library: a raster with a georeference, so it can
be projected onto the task grid. ``dem`` makes the surface follow it and
``dem_add`` adds it with a weight. The model itself can be decomposed into
coarser levels and reconstructed: ``dem_decomp`` adds the next coarser level,
``dem_recons`` steps back one level and ``dem_full_recons`` returns to the
original. The levels are kept, so the original values come back exactly.

.. code-block:: python

   task.dem_load_hgt("N00E006.hgt")
   task.dem("N00E006.hgt")

Two things are worth knowing: the DEM loaders take a file *pattern* rather than
one path, and ``dem_load_hgt_zip`` needs zlib (the CMake build enables it when
found). DEMs also
live outside the Session state and are shared by all tasks in the process;
:doc:`python` explains why. :doc:`terrain` reads an SRTM tile in both front ends
and shows what the two rules produce.

What they have in common
------------------------

* Every object is named, and every command selects objects by a shell pattern;
  ``"*"`` is the default, so ``task.points()`` uses all points in memory.
* Every rule returns one flag per matched object, and ``[False]`` means the
  pattern matched nothing.
* The order in which rules are added is their priority; :doc:`how_it_works`
  describes what the solver does with that order.
* The result is a surface named by ``map_name``. ``file_save`` stores the whole
  task — data, rules and result — while ``surf_save`` stores one surface;
  :doc:`formats` lists the file formats.

This is the data side of the five features the engine is built around: several
data types, a gridding rule per dataset, priorities between them, and rules for
interpolation, approximation, inequalities and averages. The method behind them
is CMOFS (:doc:`how_it_works`).
