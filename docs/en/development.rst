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
     - the DEM and flow libraries; the Tcl plugins that wrap them are separate
       modules built from the checked-in SWIG wrappers
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

The two plugin libraries follow the same split as the formats. ``libglobe_core``
and ``libfreeflow_core`` hold the code and have no Tcl dependency; ``libglobe.so``
and ``libfreeflow.so`` are the Tcl plugins, built from the ``*_wrap.cxx`` files
that SWIG 1.3.28 generated. Python links the core libraries, so a wheel carries
them and ``import surfit`` registers their data managers — the same thing
``load libglobe.so`` does under Tcl. Compare their exported symbols with the
engine's before linking them together; the check above applies unchanged.

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
   * - ``python3 src/pysurfit/tests/test_all_commands.py``
     - every command of both front ends, the plugins included, is run through
       both from one table; the values, the warnings and the files written must
       agree, and the command list itself is read from tclsh so a command Python
       lacks cannot go unnoticed
   * - ``python3 src/pysurfit/tests/check_stringmatch.py``
     - the local name matcher agrees with Tcl on every well-formed pattern
   * - ``python3 gil_check.py``
     - the solve really releases the GIL
   * - ``python3 stress_check.py``
     - repeated runs in one process do not leak

The runner can also check a build that has no Tcl front end at all. The Tcl side
is run once and its output kept, and later runs compare the Python side against
that stored reference:

.. code-block:: bash

   python3 src/pysurfit/tests/run_tcl_suite.py --sequential \
       --save-references refs examples/surfit/realworld     # with Tcl
   python3 src/pysurfit/tests/run_tcl_suite.py --sequential \
       --use-references refs examples/surfit/realworld      # without Tcl

Name matching
-------------

Objects are selected by name with wildcards, and the engine implements the
matching itself. It used to call ``Tcl_StringMatch``, which was the last thing
tying the core to Tcl.

The rules were read off Tcl rather than guessed, and
``src/pysurfit/tests/check_stringmatch.py`` compares the two over a few thousand
pattern and string pairs, including ``[]]``, reversed ranges such as ``[c-a]``
and escapes:

* ``*`` and ``?`` behave as expected;
* a range matches either way round, so ``[c-a]`` matches ``a``, ``b`` and ``c``;
* a ``]`` straight after ``[`` closes the set, so ``[]]`` is an empty set;
* ``!`` and ``^`` are ordinary members — Tcl's string match has no negation;
* there is no escaping inside a set: a backslash is a member like any other.

Patterns with an **unterminated** ``[`` are excluded from that comparison. Tcl's
answer there depends on the memory after the string: ``string match {a[b} {ab}``
returns 1 on its own and 0 once another string has been allocated after it. The
local matcher takes the deterministic reading, treating the set as running to
the end of the pattern, which is what Tcl returns in the ordinary case.

Continuous integration
----------------------

``ci/check.sh`` builds from scratch in ``build-ci`` and runs every check: the 35
test scripts with Tcl and Python side by side, parity, the name matcher against
Tcl, two tasks in one process, the viewer, and a wheel that installs into an
isolated directory and solves there without ``LD_LIBRARY_PATH``.

It takes about twenty minutes, which is the cost of testing against the Tcl
front end rather than against itself. ``ci/check.sh --full`` adds the 29
realworld pipelines, another hour, and is what the nightly job runs.

GitHub Actions calls exactly this script, so what runs on a push is what you can
run locally. Windows and MSVC are not covered.

Documentation figures
---------------------

The maps under *Runnable examples* are real output, committed as SVG so that building the documentation needs neither node
nor a browser. They are drawn by the same ``surfit/viewer.js`` the page uses, so
a figure cannot drift from what ``save_viewer()`` produces. Regenerate them with
``docs/make_images.py`` after changing the viewer or an example; it needs node,
d3 and jsdom.

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

* **One active state.** A session installs its state before each call, which
  is what lets two tasks share a process; but the install itself is not
  protected, so two sessions cannot be driven from two threads at once.
  Thread-local storage would not fix it either - the solver's own worker
  threads read the same globals.
* **The plugin is linked whole.** ``libsurfit_io`` should be built with hidden
  visibility and export only its public API, instead of relying on the helper
  names not colliding.
* ``surf_plot`` still writes PostScript through CreEPS for the Tcl front end.
  It is not bound in Python, where the viewer covers output.

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
