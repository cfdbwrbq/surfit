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

One task at a time
------------------

The engine keeps its data in process-wide globals, so creating a session resets
that state. Two sessions cannot run concurrently in one process yet.

The solve does release the GIL, so other Python threads keep running while it
computes — a progress indicator or a server stays responsive.

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

Runnable examples
-----------------

* ``examples/python/area.py`` — the area example above, end to end.
* ``examples/python/trend_from_numpy.py`` — an array used as a regional trend.
* ``examples/python/progress.py`` — the tqdm progress bar.

Development notes on how the bindings are built and checked are in
:doc:`development`.
