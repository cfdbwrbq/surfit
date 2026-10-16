Tcl
===

The original front end is a Tcl module. Every command is a plain C++ function
that SWIG turns into a Tcl command, with argument defaults taken from the C++
signature — which is why a script can write ``grid_get -12 12 0.2 -12 12 0.2``
and leave the grid name out.

The front end is optional and off by default; build it with
``-DSURFIT_BUILD_TCL=ON``, which needs ``tcl-dev`` and SWIG.

Running a script
----------------

.. code-block:: tcl

   load libtclsurfit[info sharedlibextension]

   clear_data
   set map_name "map_area"
   set tol 5.01187e-006

   area_read "data/area1.txt" "area1"

   grid_get -12 12 0.2 -12 12 0.2

   area 10 "area1"
   completer 1 1.6

   surfit
   surf_save "area.dat" "map_area"

.. code-block:: bash

   export LD_LIBRARY_PATH="$PWD/bin:$LD_LIBRARY_PATH"
   cd examples/surfit/tests
   tclsh area.tcl

The format plugin is a separate module and has to be loaded as well:

.. code-block:: tcl

   load libsurfit_io[info sharedlibextension]
   surf_save_grd "surface.grd" "map_area"

``map_name``, ``tol`` and a dozen other settings are variables traced into the
engine's globals, so ``set tol 1e-6`` changes the solver tolerance rather than a
script-local variable.

Examples
--------

``examples/surfit/tests`` holds 35 small scripts, one per rule family, and
``examples/surfit/realworld`` holds 29 larger ones over real data. Some
directories are pipelines: ``04_thickness_surface.tcl`` reads files that
``02_top_surface.tcl`` wrote, and ``00_run_all.tcl`` runs them in order.

Relationship to Python
----------------------

The Python bindings expose the same commands under the same names, so a script
maps one call to one call. ``src/pysurfit/tests/run_tcl_suite.py`` performs that
translation mechanically and compares the output files byte for byte; see
:doc:`development`.

Two things do not translate literally:

* Tcl performs backslash substitution inside quotes, so ``"\t"`` is a tab
  character. A translator has to do the same or the columns are misread.
* ``set`` on a traced variable is a call into the engine, not an assignment.

Rough edges
-----------

* ``surf_plot`` writes PostScript through the bundled CreEPS library. There is
  no Python binding for it; a web based viewer would fit the Python side better.
* The ``Hints`` file recommends Tcl 8.5. That advice is obsolete: 8.6 is what
  current distributions ship and the code builds against it.
* The ``globe`` and ``freeflow`` subprojects have no Python bindings yet.
