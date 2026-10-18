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

---

.. image:: ../_static/cover.svg
   :alt: A surface built from five polygonal areas
   :width: 100%

Getting started
---------------

Installation and one complete task:

.. toctree::
   :maxdepth: 2

   installation
   first_steps

Guides
------

Task-oriented pages:

.. toctree::
   :maxdepth: 2

   python
   terrain
   flows

Concepts
--------

What the terms mean and how the engine works:

.. toctree::
   :maxdepth: 2

   basics
   how_it_works

Reference
---------

Data types, commands, file formats, the Tcl front end:

.. toctree::
   :maxdepth: 2

   data_types
   commands
   formats
   tcl

Background
----------

References and development notes:

.. toctree::
   :maxdepth: 2

   references
   development

License
-------

surfit is distributed under the GNU General Public License, version 2. See
:doc:`development` for the one third-party file whose licence differs.
