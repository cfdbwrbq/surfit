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
#. **Set the grid** with ``grid`` (or ``grid_get`` for an explicit extent) and
   then add rules.
#. **Solve** with ``solve``, then read or save the result.

Every command of the Tcl front end is also a method on the session, under the
same name, so ``task.points("wells")`` means the same as ``points("wells")``.

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

Each of these four is a port of a Tcl script under ``examples/surfit/tests``, and
the grid it produces is byte-identical to the one that script produces.

area.py
~~~~~~~

Five polygons: the surface equals 10 inside ``area1``, 30 inside ``area3`` and
stays undefined inside ``area5``; ``area2`` and ``area4`` are approximated with a
weight, and ``completer`` smooths the space between them.

.. figure:: ../_static/map-area.svg
   :alt: Filled contour map of the area example
   :width: 80%
   :align: center

   Values run from 10 to 39.8. The white square in the middle is ``area5``,
   undefined on purpose, and the cells outside every area are undefined too.

faults.py
~~~~~~~~~

Eleven points and four fault lines. The surface has to jump across each line
instead of smoothing over it.

.. figure:: ../_static/map-faults.svg
   :alt: Filled contour map of the faults example
   :width: 80%
   :align: center

   The jumps are the abrupt colour changes along the polygon edges.

surface.py
~~~~~~~~~~

A surface used as data: the result follows ``test_func`` in least squares and
tends to a plane where the surface gives no guidance.

.. figure:: ../_static/map-surface.svg
   :alt: Filled contour map of the surface example
   :width: 80%
   :align: center

   The surface is smooth but not flat: the contour lines bunch up where
   ``test_func`` changes fastest, and the map runs from -27.5 to 82.3.

contour.py
~~~~~~~~~~

Three contours: the small one and the centre one are honoured exactly, the big
one follows with a weight of 0.5. A contour carries its value along the line,
which is what separates it from a curve.

.. figure:: ../_static/map-contour.svg
   :alt: Filled contour map of the contour example
   :width: 80%
   :align: center

   Values run from -0.7 to 1. The three rings are the contours themselves; the
   space between them is filled in by ``completer``.

trend_from_numpy.py
~~~~~~~~~~~~~~~~~~~

A regional trend handed over as a numpy array, seven wells honoured exactly, and
the result read back into an array.

.. figure:: ../_static/map-trend.svg
   :alt: Filled contour map of the trend example
   :width: 80%
   :align: center

   The plane runs from 67 to 140. The small dark diamonds are the wells: their
   measurements sit off the plane, so each pulls the surface down locally rather
   than being smoothed away.

progress.py
~~~~~~~~~~~

Reports the solver's progress while it runs; the Progress section above explains
the two styles. Its output is text, not a map:

.. code-block:: text

   -- cg (65536 cells)
      cg (65536 cells): iter 33, err 4.92211E-06

viewer.py
~~~~~~~~~

Writes the interactive HTML page. It is the same solve as ``area.py`` — only the
output differs — so the first map above is what it draws, with a pointer readout
and the undefined cells clipped out.

Development notes on how the bindings are built and checked are in
:doc:`development`.
