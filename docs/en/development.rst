Development
===========

Repository layout
-----------------

.. list-table::
   :header-rows: 1
   :widths: 26 74

   * - Path
     - Contents
   * - ``src/sstuff``
     - utility library: vectors, containers, logging, file IO, threads
   * - ``src/surfit``
     - the engine: data types, functionals, matrix operators, solvers
   * - ``src/surfit_io``
     - the file format plugin
   * - ``src/globe``, ``src/freeflow``
     - global DEM tiles and streamline subprojects
   * - ``src/tclsurfit``
     - SWIG interface that turns the engine's functions into Tcl commands
   * - ``src/pysurfit``
     - the Python bindings and their tests
   * - ``examples``
     - Tcl examples and the regression corpus
   * - ``doc``
     - the original Doxygen sources; ``docs`` is this Sphinx documentation

How the bindings work
---------------------

The public API of the engine is a set of free C++ functions. SWIG reads
``src/tclsurfit/src/*.i`` and generates one Tcl command per function; the Python
bindings call the same functions directly through pybind11.

That is why the two front ends cannot disagree: there is no second
implementation of anything. It is also why the binding layer is thin — the work
is in translating argument and result conventions, not in reimplementing
behaviour.

pybind11 was chosen over pointing SWIG at Python because the binding needs to
hand numpy buffers across and to raise Python exceptions instead of returning
Tcl error codes.

Some care is needed where the engine and the plugin meet. ``libsurfit`` and
``libsurfit_io`` both define helper structs, and two of them used to share a
name. Since both libraries are now linked into one module, such a collision is
resolved silently by the dynamic linker and the wrong implementation is called;
the plugin's copies are therefore suffixed with ``_io``. Before linking another
library in, compare the exported symbols:

.. code-block:: bash

   nm -DC --defined-only bin/libsurfit.so | sed 's/^[0-9a-f]* [A-Za-z] //' | sort -u > /tmp/a
   nm -DC --defined-only bin/libsurfit_io.so | sed 's/^[0-9a-f]* [A-Za-z] //' | sort -u > /tmp/b
   comm -12 /tmp/a /tmp/b

Inline methods from shared headers appear in both lists and are harmless, since
their definitions are identical. A plain type name that appears in both is not.

Testing
-------

.. list-table::
   :header-rows: 1
   :widths: 34 66

   * - Command
     - What it establishes
   * - ``./run_baseline.sh``
     - the original Tcl front end still passes all 35 regression scripts
   * - ``python3 src/pysurfit/tests/run_tcl_suite.py``
     - the same scripts, translated into binding calls, produce byte-identical
       data files
   * - ``... run_tcl_suite.py --sequential examples/surfit/realworld``
     - the same for the 29 real-world scripts, run as pipelines
   * - ``python3 src/pysurfit/tests/test_parity.py``
     - the saved file matches the Tcl one, ``values()`` matches the coefficient
       block inside that file, and an array survives the round trip
   * - ``python3 gil_check.py``
     - the solve really releases the GIL
   * - ``python3 stress_check.py``
     - repeated runs in one process do not leak

Why byte equality
-----------------

A wrong result does not always raise an error. During the port, a missing
backslash substitution made a loader misread its columns; the solve then
produced a surface of ``nan`` values, with no error, no warning, and an output
file of exactly the right size. Comparing against the reference byte for byte is
what caught it, and it has caught every silent divergence since.

Scripts that need a command the bindings do not expose are reported as
``SKIP`` with the name of that command. Coverage is stated as a count, never as
a bare "all good".

Known issues
------------

* **Tcl is a hard dependency of the engine.** ``StringMatch`` calls
  ``Tcl_StringMatch``. This keeps a wheel from being portable: manylinux allows
  only a fixed list of system libraries and ``libtcl`` is not on it. Replacing
  the matcher with a local implementation would remove the last coupling.
* **Global state.** The data manager, the functional list and the grid are
  process-wide singletons. A session resets them, but two cannot coexist.
* **The plugin is linked whole.** ``libsurfit_io`` should be built with hidden
  visibility and export only its public API, instead of relying on the helper
  names not colliding.
* ``surf_plot`` renders through CreEPS; a web based viewer would suit the Python
  side better.

Working on the project
----------------------

The project keeps a catalogue of mistakes and the rules derived from them in
``.agents/skills/error-to-skill/LESSONS.md``, together with the practice that
produces it. Read it before working on a subsystem it covers, and add to it
after any non-trivial failure.

License
-------

surfit is free software under the GNU General Public License, version 2.

One file does not share that licence. ``src/surfit/src/triangle.cpp`` is
Shewchuk's Triangle: it may be redistributed freely, but commercial use requires
a separate arrangement with the author. Because it is compiled into the engine
by default, anyone distributing a binary should decide what to do about it —
either obtain the arrangement or replace the triangulation.
