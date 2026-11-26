Tcl migration
=============

Status
------

The Tcl front end is **frozen**.  The 3.7.x line is the last Tcl-capable line;
surfit 3.8 removes the Tcl module, the SWIG bindings, the Tcl examples and the
``SURFIT_BUILD_TCL`` option.  The Python package and the wheels are not affected.

What changes
------------

- Source builds no longer accept ``-DSURFIT_BUILD_TCL=ON``.
- ``libtclsurfit``, the Tcl plugins and the ``surfit`` Tcl interpreter disappear.
- The ``.tcl`` examples and the Tcl half of the parity suite disappear.
- Python commands, formats and numerical behaviour stay the same.

Porting a script
----------------

Tcl and Python use the same command names.  A Tcl task becomes a
``surfit.Session``; the command arguments do not change.

.. list-table::
   :header-rows: 1
   :widths: 38 62

   * - Tcl
     - Python
   * - ``grid_get -12 12 0.2 -12 12 0.2``
     - ``task.grid(-12, 12, 0.2, -12, 12, 0.2)``
   * - ``area_read "data/area1.txt" "area1"``
     - ``task.read_areas("data/area1.txt", "area1")``
   * - ``area 10 "area1"``
     - ``task.area(10, "area1")``
   * - ``completer 1 1.6``
     - ``task.completer(1, 1.6)``
   * - ``surfit``
     - ``task.solve()``
   * - ``surf_save "area.dat" "map_area"``
     - ``task.save("area.dat")``

The Python guide has the full API; the command reference lists the shared
command names.

What stays
----------

- All data formats and numerical rules.
- The Python names inherited from Tcl (``pnts_*``, ``area_*``, ``curv_*``).
- The 3.7.x line as the last Tcl-capable line.
