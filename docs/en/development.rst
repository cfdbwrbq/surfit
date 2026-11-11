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
   * - ``python3 src/pysurfit/tests/test_examples.py``
     - every Python example in ``examples/python`` runs as the reader runs it
       and writes the same ``.dat`` as its Tcl original, byte for byte; a Tcl
       script with no port fails the check unless it is listed as deliberately
       unported
   * - ``python3 src/pysurfit/tests/test_parity.py``
     - the saved file matches the Tcl one, ``values()`` matches the coefficient
       block inside that file, and an array survives the round trip
   * - ``python3 src/pysurfit/tests/test_robust.py``
     - four outer IRLS iterations down-weight a 100-among-zeros outlier and
       move the cell from 4.76 to about 1.43
   * - ``python3 src/pysurfit/tests/test_uncertainty.py``
     - ensemble mean/spread on two fields, then four real bootstrap surfaces
       from resampled points
   * - ``python3 src/pysurfit/tests/test_cross_validation.py``
     - four rotating held-out folds predict every point from a surface that
       did not see it; the mean RMSE is checked against the field span
   * - ``python3 src/pysurfit/tests/test_cross_validation_api.py``
     - spatial CV folds do not overlap; block folds stay together; metrics are
       JSON-ready
   * - ``python3 src/pysurfit/tests/test_metadata.py``
     - CRS/units/source survive on the task and in the JSON sidecar
   * - ``python3 src/pysurfit/tests/test_diagnostic_geometry.py``
     - typed point codes, GeoJSON/CSV output and Session wrappers
   * - ``python3 src/pysurfit/tests/test_padding.py``
     - collar extent and crop preserve the node spacing
   * - ``python3 examples/python/quality_workflow.py``
     - the runnable end-to-end quality example: residuals, spatial CV,
       variogram, support, diagnostics and provenance
   * - ``python3 src/pysurfit/tests/test_psf.py``
     - impulse-response half-width and Gaussian sigma recover a known PSF
   * - ``python3 src/pysurfit/tests/test_resolution.py``
     - Nyquist/support report and the fine-grid warning
   * - ``python3 src/pysurfit/tests/test_smoothing.py``
     - spatial CV selects a candidate smoothing parameter
   * - ``python3 src/pysurfit/tests/test_crs.py``
     - optional pyproj point/extent helpers (SKIP without pyproj)
   * - ``python3 src/pysurfit/tests/test_variogram.py``
     - spherical fit, experimental/directional variogram and the anisotropy
       suggestion
   * - ``python3 src/pysurfit/tests/test_block_bootstrap.py``
     - block bootstrap samples complete blocks; block labels and auto labels
       agree
   * - ``python3 src/pysurfit/tests/test_voronoi_weights.py``
     - 2D polygonal declustering: known cell areas, duplicate splitting,
       collinearity and bounds errors (SKIP without scipy)
   * - ``python3 src/pysurfit/tests/test_quality_attributes.py``
     - per-cell support arrays and the report coverage; declustering methods
       reduce blocks while preserving the total weight
   * - ``python3 src/pysurfit/tests/test_file_errors.py``
     - a missing or malformed file reports a warning instead of an empty task
   * - ``python3 src/pysurfit/tests/test_diagnostics.py``
     - residuals, MAD outlier, Huber/Tukey and the JSON quality report
   * - ``python3 src/pysurfit/tests/test_tiled_geometry.py``
     - generic tiled driver solves curve, contour and area rules against a full
       solve; tile geometry and halo are checked
   * - ``python3 src/pysurfit/tests/test_tiled.py``
     - a 41x41 synthetic field is solved in nine overlapping tiles and written
       to a memmap; the mosaic has no undefined inner nodes
   * - ``python3 src/pysurfit/tests/test_array_ingest.py``
     - points, curves, areas and contours can be registered from numpy arrays
   * - ``python3 src/pysurfit/tests/test_stack.py``
     - ordered layers share a grid; crossings, thickness and pinch-outs are
       reported
   * - ``python3 src/pysurfit/tests/test_geotiff.py``
     - GeoTIFF values, geotransform, CRS and nodata (skips without GDAL)
   * - ``python3 src/pysurfit/tests/test_strict.py``
     - opt-in strict mode turns an empty area match into a ValueError
   * - ``python3 src/pysurfit/tests/test_serial.py``
     - serial mode forces this task's pool to one worker and restores it
   * - ``python3 ci/selfcheck.py``
     - skills have valid frontmatter and local links, the docs trees are in
       step, and the public Python surface imports
   * - ``python3 src/pysurfit/tests/test_sstuff_state.py``
     - worker pool, log, file search, datafile mode and RNG are per task
   * - ``python3 src/pysurfit/tests/test_plugin_state.py``
     - globe/freeflow state is per task; two Sessions may use different DEMs
       under one name without mixing
   * - ``python3 src/pysurfit/tests/test_context.py``
     - each Session owns its data manager; clear_data in one does not touch the
       other, and grid_auto uses the task's own manager
   * - ``python3 src/pysurfit/tests/test_threadlocal_state.py``
     - two real solves in two threads give the solo hashes, overlap in time,
       and keep their DEMs; a task released by one thread is safe in another
   * - ``python3 src/pysurfit/tests/test_weights.py``
     - per-point weights change the cell average; a zero weight drops a point
       and a short vector is rejected
   * - ``python3 src/pysurfit/tests/test_synthetic.py``
     - a plane, a Gaussian and a sinusoid are sampled, solved and compared with
       the known truth, including a held-out 30% of the points; this is an
       accuracy/bias check, not a parity check
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
test scripts with Tcl and Python side by side, the 49 Python examples against
their Tcl originals, parity, the name matcher against Tcl, two tasks in one
process, the viewer, the documentation (the two trees against each other and a
warning-free Sphinx build of each, when Sphinx is installed), and a wheel that
installs into an isolated directory and solves there without
``LD_LIBRARY_PATH``.

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

Command reference
-----------------

The page under *Command reference* is generated, not written:
``docs/make_command_reference.py`` reads the command list from the SWIG
interface files under ``src`` and the syntax, description, parameters and
examples from the Doxygen comments in the headers. ``docs/check_docs.py`` fails
when the page is stale, so a new command or an edited header cannot leave the
reference behind. The command names and the descriptions are the same in both
languages; only the title and the introduction are translated.

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

Why the solver stays in C++
----------------------------

A separate prototype reimplemented the core problem in numpy/scipy: the same
``d1·D1 + d2·D2`` system, the same five-point and fourth-order stencils, the
same grid ladder, direct and conjugate-gradient solvers. It is a measurement
tool, not a second engine.

The formulation reproduces. Seven points and a completer agree with the engine
to ``4·10⁻⁵`` of the value range at ``tol=1e-8``, a surface used as data agrees
to ``10⁻¹⁵``, and the ``.dat`` writer round-trips byte for byte. The speed does
not: the direct solve is competitive only up to about 160x160 (81x81: 0.15 s
against 0.31 s; 161x161: 1.0 s against 0.68 s), at 321x321 it is 6.7 s against
1.4 s, and at 641x641 the sparse factorisation does not fit while the engine
takes 2.2 s. Conjugate gradients in numpy/scipy is 20-130 times slower (about
10 ms per iteration against 0.1 ms at 321x321; 290 s against 2.2 s at
641x641). The penalty loops (``mean``, ``wmean``, ``ineq``) stop on a change of
the solution norm, not on a residual, and at the examples' ``tol=1e-6`` leave
14-21% of the range; at ``1e-10`` they agree with the exact penalty solution.

So the prototype stays a reference and a playground, not a replacement.
Reimplementing 35 functional classes, CMOFS and the data managers would create
a second semantics to keep in sync, for no speed. The measurements are useful
for the engine itself: ``tol`` is a step of the CG, not an error bound (see the
known issues below), and the penalty loops need a stopping rule tied to the
residual.

Known issues
------------

* **Per-thread library state is not freed at thread exit.** The globals and the
  installed task are thread-local, so every thread that uses a Session gets its
  own library state (the state module-level commands run on).  A worker thread
  that exits leaves that small state behind; a thread pool therefore costs one
  state per thread, not one per task.
* **Module-level commands belong to their thread.** ``surfit.area(...)`` and the
  other module functions use the calling thread's library state, so two threads
  calling them at the same time still share nothing but the process.  Use a
  Session in each thread for parallel work.
* **A task released by another thread loses that thread's globals.** Releasing
  clears the released task out of every thread's active slot, and the next
  Session call in that thread installs its own state; a module-level command
  called before that would still see the freed task's globals.
* **The plugin is linked whole.** ``libsurfit_io`` should be built with hidden
  visibility and export only its public API, instead of relying on the helper
  names not colliding.
* ``surf_plot`` still writes PostScript through CreEPS for the Tcl front end.
  It is not bound in Python, where the viewer covers output.
* **``tol`` is not an error bound.** The CG stops on ``max|alpha·p|``, so at
  ``tol=1e-6`` the result can be off by about 0.7% of the value range; the
  penalty loops (``mean``, ``wmean``, ``ineq``) stop on a change of the norm and
  can leave 14-21% at the same tolerance. Compare solutions by the residual, or
  use a tolerance well below the accuracy that is needed.

Working on the project
----------------------

The project keeps a catalogue of mistakes and the rules derived from them in
``.agents/skills/error-to-skill/LESSONS.md``, together with the practice that
produces it. Read it before working on a subsystem it covers, and add to it
after any non-trivial failure.

License
-------

surfit is free software under the GNU General Public License, version 2.

The triangulation code is CDT (Constrained Delaunay Triangulation), vendored in
``src/surfit/src/third_party/cdt/`` under the Mozilla Public License 2.0. Its
files keep their MPL notices; unlike Triangle, there is no commercial-use
restriction. The rest of the engine remains GPL-2.
