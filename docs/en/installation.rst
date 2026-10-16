Installation
============

Requirements
------------

Building the engine needs:

* CMake 3.10 or newer
* a C++ compiler
* the Tcl development headers (``tcl-dev`` on Debian and Ubuntu)

The engine itself links Tcl: name matching between objects uses
``Tcl_StringMatch``. The Tcl *front end* is optional and is the only part that
needs SWIG.

These are optional and enable extra features:

* ``zlib`` — the ``globe`` module for global DEM tiles
* ``libjpeg`` — JPEG grids
* ``netcdf`` — GMT and netCDF grids

Python
------

The package drives the engine and needs numpy:

.. code-block:: bash

   pip install .

The same command works from a checkout. It builds only the engine and the
bindings; see `Build options`_ if you also want the Tcl front end. The wheel
carries every shared library inside the package, so nothing needs to be on
``LD_LIBRARY_PATH``.

From source
-----------

.. code-block:: bash

   mkdir -p build && cd build
   cmake ../src
   make -j"$(nproc)"
   export LD_LIBRARY_PATH="$PWD/bin:$LD_LIBRARY_PATH"

That produces the shared libraries, the Tcl module ``libtclsurfit.so``, the
``surfit`` command line interpreter, and — when pybind11 is available — the
Python extension inside ``bin/surfit/``.

To install into a prefix, ``make install`` puts the libraries in ``lib`` and the
interpreter in ``bin``. There is no RPATH, so ``lib`` has to be on the loader
path; that is why the commands above use ``LD_LIBRARY_PATH``.

Build options
-------------

.. list-table::
   :header-rows: 1
   :widths: 28 12 60

   * - Option
     - Default
     - Meaning
   * - ``SURFIT_BUILD_TCL``
     - ``ON``
     - Build the Tcl module, the command line interpreter, ``globe`` and
       ``freeflow``. Needs SWIG.
   * - ``SURFIT_BUILD_PYTHON``
     - ``ON``
     - Build the Python extension. Skipped with a message when pybind11 is
       missing.
   * - ``SURFIT_PYTHON_WHEEL``
     - ``OFF``
     - Install every shared library inside the ``surfit`` package instead of
       ``lib``. Set by the wheel build.
   * - ``SURFIT_LIBDIR``
     - ``lib``
     - Where the shared libraries are installed. Becomes ``surfit`` for a
       wheel.

For example, a build with only the Python bindings:

.. code-block:: bash

   cmake -DSURFIT_BUILD_TCL=OFF ../src

Documentation
-------------

The documentation is built with Sphinx in both English and Russian:

.. code-block:: bash

   pip install -r docs/requirements.txt
   docs/build.sh

The result is ``docs/_build/html/index.html``, which redirects to the English
tree; the Russian one is one click away through the switcher at the bottom of
every page.
