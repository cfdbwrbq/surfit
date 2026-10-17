First steps
===========

This page builds one small task from scratch: seven scattered points, an
explicit grid, two rules, a solve, and two ways to keep the result. The example
is ``examples/python/first_steps.py``; its source is on this page and runs as
written.

The original manual started with the Tcl shell and the ``funner`` viewer. Neither
is needed now: the task is a Python object, and the result can be written as a
page that opens in a browser.

You need Python 3 with ``numpy`` and the ``surfit`` package; :doc:`installation`
has the wheel and the build-from-source path.

What the result looks like
--------------------------

.. figure:: ../_static/map-first-steps.svg
   :alt: Filled contour map of the first steps example
   :width: 80%
   :align: center

   The seven measurements are honoured exactly. The map runs from 67 to 140,
   the range of the measurements; ``completer`` fills the space between them.

The complete example
--------------------

.. literalinclude:: ../../examples/python/first_steps.py
   :language: python

What each step does
-------------------

Load the data
~~~~~~~~~~~~~

The measurements are a columned text file: x, y and the value, one point per
line. ``read_points`` (the Tcl ``pnts_read``) returns one flag per matched file,
so ``assert all(...)`` catches a wrong path or a pattern that matched nothing:

.. code-block:: python

   assert all(task.read_points("data/7points.txt", "wells"))

When the columns are not the first three, pass them by keyword; the delimiter
and the number of header lines are arguments too:

.. code-block:: python

   task.read_points("model.txt", "wells", col1=4, col2=3, col3=5)

The other families load the same way: ``read_curves``, ``read_contours``,
``read_areas``, ``surf_load`` and ``mask_load``.

Make the grid
~~~~~~~~~~~~~

``task.grid`` is an explicit grid: start and end of x, the cell size, then the
same three numbers for y:

.. code-block:: python

   task.grid(-10, 10, 0.25, -10, 10, 0.25)

If the extent should follow the data instead, ``task.grid_auto()`` fits the grid
to everything loaded. That is the Tcl ``grid`` command; the ``grid`` method is
the explicit one.

Add the rules
~~~~~~~~~~~~~

A *gridding rule* says how the data is used. ``points`` passes the surface
through the measurements, ``completer`` keeps it smooth where there are none:

.. code-block:: python

   task.points("wells")
   task.completer()

Every rule returns one flag per data object. A result of ``[False]`` means the
name pattern matched nothing and the rule was **not** added — the Tcl front end
ignores that silently, so it is worth checking the flags. Rules can carry a
weight (``_add``) or become bounds (``_leq``, ``_geq``); the families are listed
in :doc:`python`.

Solve
~~~~~

.. code-block:: python

   task.solve()

The solver works through a sequence of grids; the number of iterations and the
residual are in the log, and :doc:`python` shows how to turn that into a
progress bar.

Save the result
~~~~~~~~~~~~~~~

There are three levels of saving, and the difference matters:

.. code-block:: python

   task.save("first_steps.dat")       # the surface, surf_save
   task.file_save("task.dat")         # the whole task: data, rules, surface
   task.surf_save_grd("map.grd")      # another format, from the plugin

``save`` is all a map needs. ``file_save`` is what keeps a task that can be
loaded and continued later. The formats plugin adds a saver for each supported
format; :doc:`formats` lists them.

Look at the result
~~~~~~~~~~~~~~~~~~

``values()`` returns the most recent surface as a ``(count_y, count_x)``
float64 array. Nodes outside the data carry ``surfit.UNDEF_VALUE``, which is
``FLT_MAX``; ``defined_mask`` selects the rest:

.. code-block:: python

   grid = task.values()
   defined = surfit.defined_mask(grid)
   print(grid.shape, grid[defined].min(), grid[defined].max())

The example writes an HTML page as well:

.. code-block:: python

   task.save_viewer("first_steps.html", title="first steps", levels=14)

The page embeds the grid and draws filled contours with a pointer readout; d3 is
loaded from a CDN when the page is opened. Pass ``d3_url`` to point at a local
copy where there is no network.

Other kinds of data
-------------------

The same four steps work for every data family. Only the loader and the rule
change:

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Data
     - Load
     - Rule
   * - scattered points
     - ``read_points``
     - ``points``, ``points_leq``, ``points_geq``
   * - curves
     - ``read_curves``
     - ``curve``, ``curve_leq``, ``curve_geq``, ``fault``
   * - contours
     - ``read_contours``
     - ``contour``, ``contour_leq``, ``contour_geq``
   * - areas
     - ``read_areas``
     - ``area``, ``area_leq``, ``area_geq``, ``area_mean``
   * - surfaces
     - ``surf_load``
     - ``surface``, ``surface_leq``, ``surface_geq``, ``trend``
   * - masks
     - ``mask_load``
     - ``mask``, ``mask_leq``, ``mask_geq``

A rule applies to every object whose name matches its pattern; ``"*"`` is the
default, so ``task.points()`` uses all points in memory. The examples under
``examples/python/`` show each family in turn, with the map it produces:
:doc:`python`.

Where to go next
----------------

* :doc:`python` — the API, all rule families, numpy in and out, the viewer.
* :doc:`flows` — pressure fields with ``freeflow``, the rules and the maps.
* :doc:`formats` — the native file, BLN, shapefiles and the rest.
