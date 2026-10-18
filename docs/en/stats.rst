Port statistics
===============

These numbers describe the port itself: how long it took, how much code it
produced, and what the AI-assisted sessions consumed. They are measurements, not
guarantees; the section at the end says how to reproduce them.

Timeline
--------

* First port commit: 2026-10-16, ``60fdf62`` ("Build and run surfit on 64-bit
  Linux").
* Latest commit at the time of writing: 2026-10-18, ``1cd004a``.
* Calendar span: three days, 74 commits.
* Diff against the parent of the first port commit: 273 files changed,
  25,382 insertions and 2,734 deletions.

What was built
--------------

.. list-table::
   :header-rows: 1
   :widths: 30 20 20

   * - Kind
     - Files
     - Lines
   * - C++ sources
     - 172
     - 80,525
   * - C/C++ headers
     - 179
     - 22,750
   * - Python
     - 70
     - 7,568
   * - reStructuredText
     - 28
     - 12,716
   * - Tcl
     - 93
     - 5,185

The test suite runs 49 examples byte-identically against the Tcl front end and
504 command steps; ``examples/surfit/tests`` has 35 Tcl scripts, and
``src/pysurfit/tests`` has 7 Python test modules. The documentation has 15 pages
in English and Russian; the built HTML is about 65 MB.

AI-assisted work
----------------

The port was driven through eight logged sessions between 2026-10-16 14:45 and
2026-10-18 05:17 UTC:

.. list-table::
   :header-rows: 1
   :widths: 55 45

   * - Measure
     - Value
   * - Model requests
     - 3,998
   * - Tool calls
     - 4,378
   * - User messages
     - 155
   * - Generated tokens (output)
     - 2,831,583
   * - Uncached prompt tokens
     - 5,867,210
   * - Cache-read tokens
     - 1,309,106,560
   * - Total tokens reported by the provider
     - 1,317,802,745
   * - Peak context in one request
     - 677,961 tokens
   * - Session wall-clock, summed
     - 38.6 h

Machine cost
------------

* Full CI (``./ci/check.sh``): 2 min 52 s wall-clock, 718 MB peak resident.
* Documentation build, both languages, clean: 10.4 s, 98 MB peak resident.
* Working copies: ``.git`` 22 MB, ``docs/_build/html`` 65 MB, ``build-ci``
  111 MB.

How these are measured
----------------------

* Timeline and diff: ``git log --since=2026-10-15`` and
  ``git diff --shortstat 60fdf62^ HEAD``.
* Code lines: ``git ls-files`` filtered by extension and counted with ``wc -l``.
* AI usage: the DSH session logs (``session.v4.jsonl.zstd`` under
  ``~/.dsh/sessions/--home-gisolog-dev-surfit--/``) are decompressed with
  ``zstd -dc`` and the provider's ``usage`` records are summed per request.
* CI and build times: ``/usr/bin/time -v`` around the command.

Caveats
-------

* Token totals are provider usage, not human effort. Cache reads repeat the
  context on every request, so the total is far larger than the amount of unique
  text the model ever saw.
* Session wall-clock is the first-to-last event time of each session. Sessions
  may overlap, and the number includes idle time between events.
* The three-day calendar span comes from commit dates; work before the first
  commit is not counted.
