Python
======

.. code-block:: python

   import surfit

   task = surfit.Session(map_name="map_area", tol=5.01187e-06)

   for name in ("area1", "area2", "area3", "area4", "area5"):
       task.read_areas("data/%s.txt" % name, name)

   task.grid(-12, 12, 0.2, -12, 12, 0.2)

   task.area(10, "area1")             # equal to 10 inside area1
   task.area(30, "area3")
   task.area("undef", "area5")        # leave area5 undefined
   task.completer(1, 1.6)             # tend to a constant or a plane
   task.area_add(20, 0.07, "area2")   # approximate, with a weight
   task.area_add(40, 0.07, "area4")

   task.solve()
   task.save("area.dat")

   grid = task.values()               # numpy, (count_y, count_x), float64

The shape of the API
--------------------

A task has three phases, and they must happen in this order:

#. **Load data.** ``read_areas``, ``read_points``, ``read_curves``,
   ``read_contours``, ``surf_load``, ``mask_load``, or an array through
   ``add_surface``.
#. **Set the grid** with ``grid`` for an explicit extent, or ``grid_auto`` to fit
   it to the loaded data (Tcl's ``grid``), and then add rules.
#. **Solve** with ``solve``, then read or save the result.

Every command of the Tcl front end is also a method on the session, under the
same name, so ``task.points("wells")`` means the same as ``points("wells")``.
The one exception is ``grid``: the method of that name builds an explicit grid
(Tcl's ``grid_get``), and ``grid_auto`` is Tcl's ``grid``.

Rules
-----

A rule states something about the resulting surface. The families differ by
where the condition applies:

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Family
     - Meaning
   * - ``points``
     - the surface passes through, or near, the measured points
   * - ``curve``, ``contour``
     - the surface equals a value along a curve or contour
   * - ``area``
     - the surface equals a value inside a polygon
   * - ``surface``, ``trend``
     - the surface follows another surface, or a fitted trend
   * - ``mask``
     - the rule applies only where a raster mask says so
   * - ``fault``
     - the surface may be discontinuous along a line
   * - ``completer``
     - the surface stays smooth between the other conditions
   * - ``leq``, ``geq``, ``mean``, ``wmean``, ``hist``
     - global bounds, averages and histogram matching

Most families come in variants: the plain command adds a rule, ``_add`` adds it
with a weight so it is combined with the previous one, and ``_leq`` / ``_geq``
turn it into an inequality.

Every command returns a list of per-object flags. A result of ``[False]`` means
the name pattern matched nothing and the rule was **not** added — the original
Tcl front end ignores that silently, so it is worth checking when a result looks
unexpected.

Arrays in and out
-----------------

``values()`` returns the most recently created surface as a
``(count_y, count_x)`` float64 array. Without a pattern that is the result of
the last solve; a trend added along the way would otherwise be picked up
instead. Pass a name pattern to select one explicitly:

.. code-block:: python

   grid = task.values()               # the result
   trend = task.values("regional")    # a named surface

Nodes outside the data are undefined and carry ``surfit.UNDEF_VALUE``, which is
``FLT_MAX``. ``surfit.defined_mask(grid)`` selects the defined ones:

.. code-block:: python

   defined = surfit.defined_mask(grid)
   print(grid[defined].min(), grid[defined].max())

An array goes the other way through ``add_surface``. It is registered as a named
surface and can then be used as a trend or as a source of inequalities:

.. code-block:: python

   import numpy as np

   trend = np.linspace(100.0, 120.0, 40 * 50).reshape(40, 50)
   task.add_surface(trend, start_x=0.0, step_x=25.0,
                    start_y=0.0, step_y=25.0, name="regional")
   task.surface("regional")

The node count comes from the array shape: the extent is computed from the
origin and the spacing, so the grid matches exactly.

File formats
------------

The loaders and savers of the format plugin are available under their Tcl
names:

.. code-block:: python

   surfit.area_load_shp("zones.shp", "zones")
   surfit.cntr_load_shp("isolines.shp", "iso")
   surfit.surf_load_grd("surface.grd", "top")
   surfit.surf_save_grd("smoothed.grd", "top")

See :doc:`formats` for the full list.

Digital elevation models and flows
----------------------------------

The two libraries the Tcl front end loads as plugins, ``globe`` (DEM) and
``freeflow`` (flows), are linked into the extension, so their commands are
there after ``import surfit``, under the same names:

.. code-block:: python

   surfit.surf_to_dem("top")            # a DEM made from a solved surface
   surfit.dem_getCountX("top")
   surfit.dem_minz("top")
   surfit.dem_save_grd("top.grd", "top")

   surfit.dem_load_hgt("N00E006.hgt")   # a DEM from an SRTM tile
   surfit.grid_get(6.4, 6.8, 0.0005, 0.0, 0.48, 0.0005)
   surfit.dem("N00E006.hgt")            # rule: follow the DEM
   surfit.completer()
   surfit.surfit()

   surfit.lcm_simple(1, 1, 1)           # rule: conservation of mass
   surfit.flow_points("wells")          # attach flow data to that rule
   surfit.surf_debit(0.0, 0.0, 1, 1, 1, "pressure")

Two things are worth knowing:

* ``dem_load_hgt_zip`` needs a build with zlib headers. Without them it reports
  "zlib not detected" and returns nothing.
* DEMs live in a container of their own, outside the state a Session owns, so
  two Sessions in one process share them. The finite-element rules the
  ``freeflow`` commands create are ordinary rules and are per-Session.

The flow examples, with maps and the story of what each rule does, are on the
:doc:`flows` page.

More than one task
------------------

Each Session owns its state, so two tasks can live in one process and neither
disturbs the other:

.. code-block:: python

   first = surfit.Session("first")
   second = surfit.Session("second")

   first.read_areas("data/area1.txt", "area1")
   second.read_areas("data/area2.txt", "area1")

   first.solve()
   second.solve()

   first_grid = first.values()
   second_grid = second.values()

Every call through a Session installs that task's state first, so the calls can
be interleaved in any order; the results are the same as running each task
alone. ``src/pysurfit/tests/test_sessions.py`` checks exactly that, comparing
the interleaved grids byte for byte against solo runs in fresh processes.

Only one state is active at a time, which is what keeps the switch cheap. Two
Sessions can therefore be interleaved but not driven from two threads at once:
the switch itself is not protected. The solve does release the GIL, so other
Python threads keep running while it computes.

Progress
--------

A solve can be watched while it runs:

.. code-block:: python

   with surfit.progress():
       task.solve()

The engine reports every solve and every iteration through its logging, and the
context manager turns that into progress: the phase and the grid size, the
iteration count, and the current residual.

Where that progress is shown depends on where the output goes, which is worth
knowing because the two cases are genuinely different:

``style="bar"``
    a tqdm bar, redrawn in place with carriage returns. This is what you want on
    a terminal, and it needs tqdm (``pip install surfit[progress]``).
``style="lines"``
    one line per event, throttled by ``every`` seconds. Use it in CI logs,
    notebooks, and anywhere the output is **captured** rather than displayed.
``style=None`` (default)
    a bar when stderr is a terminal, lines otherwise.

A redrawn bar survives only in a terminal. In a captured stream the carriage
returns collapse the frames into each other and only the last one is left, so
the default switches to lines automatically:

.. code-block:: text

   -- cg (65536 cells)
      cg (65536 cells): iter 33, err 4.92211E-06
   -- cg (231361 cells)
      cg (231361 cells): iter 17, err 4.63839E-06

The observer sees whatever the current log level lets through, so a silent log
means silent progress.

The same hook is available directly, for logging of your own:

.. code-block:: python

   surfit.set_log_handler(lambda level, message: print(level, message))
   task.solve()
   surfit.clear_log_handler()

It is called while the solve runs with the GIL released, so it may be reached
from another thread; keep it short, because it runs inside the solver.

Viewer
------

A result can be written as a page that opens in a browser:

.. code-block:: python

   task.save_viewer("map.html", title="area example", levels=14)

The page draws a filled contour map with real coordinates on the axes, a pointer
readout showing x, y and the value, and the undefined region clipped out. The
grid is embedded in the page as float64, so the file is a lossless record of the
result and can be moved around on its own.

d3 is loaded from a CDN when the page is opened. That is the only thing the page
needs from outside; pass ``d3_url`` to point at a local copy where there is no
network.

.. code-block:: python

   task.save_viewer("map.html", d3_url="d3.v7.min.js")

The contour code is in ``surfit/viewer.js`` and is the same code the tests run,
so it is checked without a browser: ``src/pysurfit/tests/test_viewer.py`` decodes
the embedded payload back to the original grid, runs the contour computation
under node, and renders into a real DOM with jsdom.

Runnable examples
-----------------

All of these live under ``examples/python/`` and run as written. Each map is that
example's own output: ``docs/make_images.py`` imports the example and renders the
grid it produces, so a figure cannot drift from the code.

Thirty-three of them are ports of the scripts under ``examples/surfit/tests``,
and each writes a ``.dat`` file byte-identical to the one its Tcl script writes:
``src/pysurfit/tests/test_examples.py`` runs both and compares them. The two
scripts the original manual never documented, ``aniso.tcl`` and
``area_hist.tcl``, are the only ones without a port. ``trend_from_numpy``,
``progress`` and ``viewer`` have no Tcl original.

The headings follow the grouping of the original manual.

Areas
~~~~~

area.py
^^^^^^^

Five polygons: the surface equals 10 inside ``area1``, 30 inside ``area3`` and
stays undefined inside ``area5``; ``area2`` and ``area4`` are approximated with a
weight, and ``completer`` smooths the space between them.

.. figure:: ../_static/map-area.svg
   :alt: Filled contour map of the area example
   :width: 80%
   :align: center

   Values run from 10 to 39.8. The white square in the middle is ``area5``,
   undefined on purpose, and the cells outside every area are undefined too.

area_completer.py
^^^^^^^^^^^^^^^^^

The same smoothing rule, applied inside one polygon: ``area_completer`` puts the
completer with anisotropy (angle 30 degrees, ``w=2``) inside ``some_area``, while
the plain ``completer`` covers the rest. Eleven points keep the surface tied to
the data.

.. figure:: ../_static/map-area-completer.svg
   :alt: Filled contour map of the area_completer example
   :width: 80%
   :align: center

   Values run from -10 to 35.5. Inside the central area the contours stretch
   along one direction, because the smoothing there prefers it.

area_ineq.py
^^^^^^^^^^^^

The area example with bounds added: ``area6`` asks for 15 to 20, but it also
overlaps ``area1`` and ``area3``, whose exact values (10 and 30) take precedence.
The inequality bends the rest of ``area6``, and the script's own report of the
maximum inside it is 30.

.. figure:: ../_static/map-area-ineq.svg
   :alt: Filled contour map of the area_ineq example
   :width: 80%
   :align: center

   Values run from 10 to 39.3. The banding that the inequality adds is visible
   between the exact areas, while the maximum inside ``area6`` is still set by
   ``area3``.

area_mean.py
^^^^^^^^^^^^

Averages instead of exact values: the surface should average 40 inside ``area6``
and 30 over the whole map. Both conditions leave the value at any single node
free, so the map is smoother than the exact-value version.

.. figure:: ../_static/map-area-mean.svg
   :alt: Filled contour map of the area_mean example
   :width: 80%
   :align: center

   Values run from 6.3 to 61.7. Both averages are met, and ``area6`` is no
   longer pinned to one number.

area_wmean.py
^^^^^^^^^^^^^

The same average with a weight surface: inside ``area6`` the surface averages 30
with ``test_func`` as the weight, so the average is biased towards the places
where that surface is high.

.. figure:: ../_static/map-area-wmean.svg
   :alt: Filled contour map of the area_wmean example
   :width: 80%
   :align: center

   Values run from 10 to 45.2; the weighted average sits lower than the
   unweighted one because the weight is large where ``test_func`` is high.

area_surf.py
^^^^^^^^^^^^

A surface as data inside areas: the result follows ``test_func`` exactly inside
``area6`` and approximately inside areas 1 to 4, with a separate weight for each
polygon.

.. figure:: ../_static/map-area-surf.svg
   :alt: Filled contour map of the area_surf example
   :width: 80%
   :align: center

   Values run from -22.7 to 82.3, the range of ``test_func`` itself.

area_surf_ineq.py
^^^^^^^^^^^^^^^^^

Brackets the surface between two copies of ``test_func``: above it in areas 1, 3
and 5, below it in areas 2, 4 and 6. The result lies inside that sandwich and is
smooth between the areas.

.. figure:: ../_static/map-area-surf-ineq.svg
   :alt: Filled contour map of the area_surf_ineq example
   :width: 80%
   :align: center

   Values run from -22.8 to 82.9. The two halves of the map are pushed in
   opposite directions, and the completer joins them.

Contours
~~~~~~~~

contour.py
^^^^^^^^^^

Three contours: the small one and the centre one are honoured exactly, the big
one follows with a weight of 0.5. A contour carries its value along the line,
which is what separates it from a curve.

.. figure:: ../_static/map-contour.svg
   :alt: Filled contour map of the contour example
   :width: 80%
   :align: center

   Values run from -0.7 to 1. The three rings are the contours themselves; the
   space between them is filled in by ``completer``.

contour_ineq.py
^^^^^^^^^^^^^^^

Two sets of contours instead of one: the lower set is a lower bound and the upper
set, shifted by 0.2, an upper bound, so the surface only has to stay between them
rather than touch either.

.. figure:: ../_static/map-contour-ineq.svg
   :alt: Filled contour map of the contour_ineq example
   :width: 80%
   :align: center

   Values run from -0.9 to 1.1, a wider range than the equality version: the
   bounds let the surface go past each ring by the distance between the sets.

Curves
~~~~~~

curve.py
^^^^^^^^

Four isolines used as data: three carry an exact value (10, 50 and 30), and the
fourth is added with a weight of 0.5. A curve is 2D, so the value comes from the
rule, not from the line, which separates it from a contour.

.. figure:: ../_static/map-curve.svg
   :alt: Filled contour map of the curve example
   :width: 80%
   :align: center

   Values run from 8.8 to 50. The surface reaches the highest curve and is
   pulled towards the weighted one without being forced onto it.

curve_ineq.py
^^^^^^^^^^^^^

The curve example with inequalities: the values along the same four isolines
become lower and upper bounds, so the result only has to respect their order.

.. figure:: ../_static/map-curve-ineq.svg
   :alt: Filled contour map of the curve_ineq example
   :width: 80%
   :align: center

   Values run from 9.1 to 50.2, close to the equality version, but the surface is
   free to avoid the lines instead of passing through them.

curve_surf.py
^^^^^^^^^^^^^

Curves take their values from another surface: the result follows ``test_func``
along ``spiral`` and does so with a weight of 0.5 along ``spiral2``. The grid is
derived from the data, so it covers both spirals.

.. figure:: ../_static/map-curve-surf.svg
   :alt: Filled contour map of the curve_surf example
   :width: 80%
   :align: center

   Values run from -21.2 to 81.8. The spiral is the ridge where ``test_func`` is
   followed exactly.

curve_surf_ineq.py
^^^^^^^^^^^^^^^^^^

Inequalities with values taken from another surface: above ``test_func`` along
``spiral2`` and below it along ``spiral``. The two spirals interleave, so the
result is threaded between them.

.. figure:: ../_static/map-curve-surf-ineq.svg
   :alt: Filled contour map of the curve_surf_ineq example
   :width: 80%
   :align: center

   Values run from -21.2 to 81.4. The surface passes between the spirals rather
   than on them.

Faults
~~~~~~

faults.py
^^^^^^^^^

Eleven points and four fault lines. The surface has to jump across each line
instead of smoothing over it.

.. figure:: ../_static/map-faults.svg
   :alt: Filled contour map of the faults example
   :width: 80%
   :align: center

   The jumps are the abrupt colour changes along the polygon edges.

fault_aniso.py
^^^^^^^^^^^^^^

The faults example on a coarser grid, with anisotropy added to the completer:
inside each block the surface is smoothed along 45 degrees rather than uniformly
(the anisotropy angle is 45 degrees, its weight argument 2).

.. figure:: ../_static/map-fault-aniso.svg
   :alt: Filled contour map of the fault_aniso example
   :width: 80%
   :align: center

   Values run from -14.1 to 38.8. The jumps along the fault lines are still
   sharp, while the smoothing inside each block prefers one direction.

fault_approx.py
^^^^^^^^^^^^^^^

The faults example without the exact condition at the points: they are added
with a weight, so the surface may miss each measurement a little.

.. figure:: ../_static/map-fault-approx.svg
   :alt: Filled contour map of the fault_approx example
   :width: 80%
   :align: center

   Values run from -6.6 to 33.3. Compared with the exact version the surface is
   flatter, and the points no longer sit exactly on it.

Inequalities
~~~~~~~~~~~~

ineq.py
^^^^^^^

The simplest inequality example: seven points, a lower bound of 80, an upper
bound of 120, and a completer in between. The surface passes through the points
and stays inside the band everywhere.

.. figure:: ../_static/map-ineq.svg
   :alt: Filled contour map of the ineq example
   :width: 80%
   :align: center

   Values run from 80 to 120: both bounds are reached but never exceeded.

points_ineq.py
^^^^^^^^^^^^^^

Two sets of measured points used as bounds: the surface has to stay above every
point of one set and below every point of the other.

.. figure:: ../_static/map-points-ineq.svg
   :alt: Filled contour map of the points_ineq example
   :width: 80%
   :align: center

   Values run from -0.2 to 1. The two point sets bracket the surface, which stays
   between them without passing through either.

Masks
~~~~~

mask.py
^^^^^^^

A raster mask cuts a hole in the surface: where the mask is true the surface is
left undefined, everywhere else it follows ``test_func``.

.. figure:: ../_static/map-mask.svg
   :alt: Filled contour map of the mask example
   :width: 80%
   :align: center

   Values run from -3.3 to 61.6 over 3031 of 5151 nodes: the missing nodes are
   the mask, not a failed solve.

mask_add.py
^^^^^^^^^^^

A value rule restricted to a mask: where the mask is true the surface is pulled
towards 3 with a weight of 0.2, and elsewhere it follows ``test_func`` as before.

.. figure:: ../_static/map-mask-add.svg
   :alt: Filled contour map of the mask_add example
   :width: 80%
   :align: center

   Values run from -6.7 to 61.6. The weighted rule lowers the surface inside the
   mask without erasing the underlying shape.

mask_completer.py
^^^^^^^^^^^^^^^^^

The completer applied inside a mask only, with anisotropy: where the mask is true
the surface is smoothed along 30 degrees rather than uniformly (the anisotropy
angle is 30 degrees, its weight argument 2).

.. figure:: ../_static/map-mask-completer.svg
   :alt: Filled contour map of the mask_completer example
   :width: 80%
   :align: center

   Values run from 0 to 0.5. The points alone would give a noisy map; inside the
   mask the anisotropic completer smooths it out.

mask_ineq.py
^^^^^^^^^^^^

An inequality under a mask: where the mask is true the surface has to be at least
-10, and elsewhere it follows ``test_func``.

.. figure:: ../_static/map-mask-ineq.svg
   :alt: Filled contour map of the mask_ineq example
   :width: 80%
   :align: center

   Values run from -10.0 to 82.3. The floor is reached exactly inside the mask,
   while the rest of the map follows ``test_func``.

mask_mean.py
^^^^^^^^^^^^

An average under a mask: where the mask is true the surface averages -2, while
the points elsewhere are honoured exactly.

.. figure:: ../_static/map-mask-mean.svg
   :alt: Filled contour map of the mask_mean example
   :width: 80%
   :align: center

   Values run from -7.6 to 0.6. The points sit near zero, and the mask drags the
   average down to -2.

mask_surf.py
^^^^^^^^^^^^

A surface rule under a mask: where the mask is true the result equals
``test_func``, elsewhere the completer fills in.

.. figure:: ../_static/map-mask-surf.svg
   :alt: Filled contour map of the mask_surf example
   :width: 80%
   :align: center

   Values run from -27.5 to 82.3. The mask keeps ``test_func``, and the completer
   extends it smoothly over the rest of the grid.

mask_surf_add.py
^^^^^^^^^^^^^^^^

A weighted surface rule under a mask: the completer comes first and ``test_func``
is added to it with a weight of 1 where the mask is true.

.. figure:: ../_static/map-mask-surf-add.svg
   :alt: Filled contour map of the mask_surf_add example
   :width: 80%
   :align: center

   Values run from -26.3 to 78.5, slightly less extreme than the exact rule,
   because the completer still has a say.

mask_surf_ineq.py
^^^^^^^^^^^^^^^^^

An inequality against a surface under a mask: where the mask is true the result
stays at or below ``test_func``, and the points pin it down elsewhere.

.. figure:: ../_static/map-mask-surf-ineq.svg
   :alt: Filled contour map of the mask_surf_ineq example
   :width: 80%
   :align: center

   Values run from -27.5 to 1.9. The masked region is capped by ``test_func``
   while the points hold the rest near zero.

mask_wmean.py
^^^^^^^^^^^^^

A weighted average under a mask: the surface averages 2 where ``mask_not`` is
true, weighted by ``test_func``, while the points are honoured exactly.

.. figure:: ../_static/map-mask-wmean.svg
   :alt: Filled contour map of the mask_wmean example
   :width: 80%
   :align: center

   Values run from 0 to 6.2. The weighted average lifts the near-zero points
   towards 2.

Averages
~~~~~~~~

mean.py
^^^^^^^

An average as a gridding condition: the surface passes through seven points and
its mean value over the whole map is 30.

.. figure:: ../_static/map-mean.svg
   :alt: Filled contour map of the mean example
   :width: 80%
   :align: center

   Values run from -57.0 to 140. The wide range is what it takes to average 30
   while still passing through the points.

wmean.py
^^^^^^^^

A weighted average: the surface passes through seven points and its average is 30
with ``test_func`` as the weight, so the average is biased towards the places
where that surface is high.

.. figure:: ../_static/map-wmean.svg
   :alt: Filled contour map of the wmean example
   :width: 80%
   :align: center

   Values run from -71.7 to 140. The weighted average reaches further down than
   the unweighted one, to compensate for the high values where the weight is
   large.

Surfaces
~~~~~~~~

surface.py
^^^^^^^^^^

A surface used as data: the result follows ``test_func`` in least squares and
tends to a plane where the surface gives no guidance.

.. figure:: ../_static/map-surface.svg
   :alt: Filled contour map of the surface example
   :width: 80%
   :align: center

   The surface is smooth but not flat: the contour lines bunch up where
   ``test_func`` changes fastest, and the map runs from -27.5 to 82.3.

surface_add.py
^^^^^^^^^^^^^^

A surface added with a small weight: the completer alone would give a plane, and
``test_func`` bends it slightly towards its own shape.

.. figure:: ../_static/map-surface-add.svg
   :alt: Filled contour map of the surface_add example
   :width: 80%
   :align: center

   Values run from -12.5 to 27.7, a much narrower range than ``test_func``
   itself: the weight of 0.01 keeps the result close to the plane.

surface_ineq.py
^^^^^^^^^^^^^^^

The surface example with an inequality: ``test_func`` shifted up by 80 is a lower
bound, so the result sits above that floor while seven points are honoured
exactly. A second copy shifted up by 90 is loaded by the script but no rule uses
it.

.. figure:: ../_static/map-surface-ineq.svg
   :alt: Filled contour map of the surface_ineq example
   :width: 80%
   :align: center

   Values run from 72.4 to 162.3. The floor is ``test_func`` plus 80, and the
   highest point of the result lies exactly on it.

Trends
~~~~~~

trend.py
^^^^^^^^

Faults under a regional trend: seven points and two fault lines, with the result
required to look like ``test_func`` at a large scale. The faults keep the trend
from being continuous across them.

.. figure:: ../_static/map-trend.svg
   :alt: Filled contour map of the trend example
   :width: 80%
   :align: center

   Values run from 29.0 to 142.7. The trend dominates the shape, and the two
   fault lines show up as steps in it.

trend_from_numpy.py
^^^^^^^^^^^^^^^^^^^

A regional trend handed over as a numpy array, seven wells honoured exactly, and
the result read back into an array.

.. figure:: ../_static/map-trend-from-numpy.svg
   :alt: Filled contour map of the numpy trend example
   :width: 80%
   :align: center

   The plane runs from 67 to 140. The small dark diamonds are the wells: their
   measurements sit off the plane, so each pulls the surface down locally rather
   than being smoothed away.

Other
~~~~~

progress.py
^^^^^^^^^^^

Reports the solver's progress while it runs; the Progress section above explains
the two styles. Its output is text, not a map:

.. code-block:: text

   -- cg (65536 cells)
      cg (65536 cells): iter 33, err 4.92211E-06

viewer.py
^^^^^^^^^

Writes the interactive HTML page. It is the same solve as ``area.py`` — only the
output differs — so the first map above is what it draws, with a pointer readout
and the undefined cells clipped out.

Development notes on how the bindings are built and checked are in
:doc:`development`.
