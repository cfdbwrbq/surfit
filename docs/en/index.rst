surfit
======

**surfit** calculates a regular grid from scattered data — points, curves,
contours, surfaces and areas — under conditions called *gridding rules*.

The rules are what makes it more than an interpolator. A task can say that the
surface must equal a value inside a polygon, stay between two bounds elsewhere,
follow a trend, respect fault lines, match a histogram, and stay smooth in
between — all at once, each with its own weight and priority.

Features
--------

* Interpolation and approximation of scattered points, 2D curves, 3D contours,
  surfaces and polygonal areas.
* Fault lines, trend surfaces, anisotropy, inequalities, average and weighted
  average conditions, histogram matching, masks.
* Fast multithreaded solver with several iterative methods.
* Many data formats: the native surfit data file, Surfer grids, GMT, Grass,
  ArcGIS, xyz, shapefile, BLN, JPEG and BMP.
* Two front ends over the same engine: the original Tcl commands and a Python
  package with numpy in and out.

Two front ends, one engine
--------------------------

The Python bindings call the same C++ functions the Tcl commands are generated
from, so the two agree by construction. That is not a claim, it is checked:
the test suite runs every Tcl example through the Python front end and compares
the resulting data files byte for byte.

.. toctree::
   :maxdepth: 2

   installation
   first_steps
   python
   how_it_works
   flows
   tcl
   formats
   development

Where to start
--------------

* New to surfit? Read :doc:`installation`, then :doc:`first_steps`; the examples
  with their maps are in :doc:`python`.
* Want to know why the result is what it is? :doc:`how_it_works` describes the
  method, the penalty loop and the solvers.
* Migrating an existing Tcl script? :doc:`tcl` explains the mapping, and
  ``src/pysurfit/tests/run_tcl_suite.py`` does the translation mechanically.
* Looking for a file format? :doc:`formats` lists them all.
* Reconstructing a pressure field? :doc:`flows` runs the flow examples.
* Building or extending the engine? :doc:`development`.

License
-------

surfit is distributed under the GNU General Public License, version 2. See
:doc:`development` for the one third-party file whose licence differs.
