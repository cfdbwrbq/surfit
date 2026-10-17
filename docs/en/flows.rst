Flows
=====

``freeflow`` adds pressure-field rules to the engine. Pressures are measured in
atmospheres or MPa and rates in m3/s; the result is the pressure field that
carries those rates through the formation. Three kinds of rule make the model:

* ``lcm_simple``, the law of conservation of mass, states the physics of every
  cell: permeability, viscosity and a multiplier.
* ``flow_points``, ``flow_curve``, ``flow_contour`` and ``flow_area`` attach a
  measured rate to a point, a line, a contour or a polygon.
* ``fault`` marks an impermeable line, while ``contour_add`` brings in measured
  pressure along a contour.

The task is set up like any other: load data, set the grid, add the flow rule
and the ordinary rules, then ``solve()``. What is new is that the data may be
inconsistent -- a measured pressure and a measured rate at the same well rarely
agree -- and the weights decide how far each is trusted. A boundary-value
problem cannot accept both; this is the reason the library exists.

What this is
------------

The rules solve an inverse problem: the pressure field has to reproduce the
measured rates while satisfying the conservation law in every cell. This is the
classical history-matching problem of reservoir and groundwater modelling, where
the unknown field is conditioned on production data and the weights express how
much each measurement is trusted [Oliver & Chen 2011].

* D. S. Oliver, Y. Chen (2011). Recent progress on reservoir history matching:
  a review. *Computational Geosciences*.
  `doi:10.1007/s10596-010-9194-2 <https://doi.org/10.1007/s10596-010-9194-2>`_

The examples are ports of ``examples/freeflow/press1`` and ``press2``. Each
writes the same ``.dat`` as its Tcl original (``test_examples.py`` checks that
byte for byte), and the maps below are drawn by ``make_images.py`` from the
examples themselves.

A field with one well
---------------------

All six examples describe one map: a 250-atmosphere boundary curve and one well
at the centre. They differ in what is known about the well. Each prints the
debit through the central 300 x 300 m square; the sign follows the rate
convention, so compare the magnitudes.

press_points.py
~~~~~~~~~~~~~~~

The baseline: the well pressure is 200 atmospheres and no rate is given, so the
field is interpolated between the two pressures.

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/press_points.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press1/points.tcl
         :language: tcl-src

.. figure:: ../_static/map-press-points.svg
   :alt: Pressure field from a 250-atm boundary and a 200-atm well
   :width: 80%
   :align: center

   Values run from 200 to 250 atmospheres, and the debit is 67.3 m3/day.

flow_points.py
~~~~~~~~~~~~~~

The well is given as a rate instead: -0.00159 m3/s at the centre. The pressure
at the well is now an output of the conservation law rather than an input.

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/flow_points.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press1/flow_points.tcl
         :language: tcl-src

.. figure:: ../_static/map-flow-points.svg
   :alt: Pressure field from a boundary and a rate at one point
   :width: 80%
   :align: center

   The well pulls the field down to 143.5 atmospheres, and the debit rises to
   138.1 m3/day.

flow_points2.py
~~~~~~~~~~~~~~~

Both the pressure and the rate at the well are known, and they disagree.
``points_add`` keeps the 200-atm measurement with a weight, ``flow_points`` adds
the rate, and the solution is a compromise between them.

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/flow_points2.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press1/flow_points2.tcl
         :language: tcl-src

.. figure:: ../_static/map-flow-points2.svg
   :alt: Pressure field from a boundary, a pressure and a rate at one well
   :width: 80%
   :align: center

   The field reaches 171.9 atmospheres at the well and the debit is
   103.2 m3/day, between the pressure-only and rate-only results.

flow_area.py
~~~~~~~~~~~~

The same total rate, spread over the 200 x 200 m square instead of concentrated
at a point. The pressure inside the square is almost flat.

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/flow_area.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press1/flow_area.tcl
         :language: tcl-src

.. figure:: ../_static/map-flow-area.svg
   :alt: Pressure field from a rate spread over an area
   :width: 80%
   :align: center

   Values run from 208.9 to 250 atmospheres and the debit is 141.4 m3/day.

flow_curve.py
~~~~~~~~~~~~~

The same total rate along the vertical line through the centre:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/flow_curve.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press1/flow_curve.tcl
         :language: tcl-src

.. figure:: ../_static/map-flow-curve.svg
   :alt: Pressure field from a rate along a curve
   :width: 80%
   :align: center

   Values run from 202.2 to 250 atmospheres and the debit is 123.8 m3/day.

flow_cntr.py
~~~~~~~~~~~~

The rate per unit length comes from the contour's Z value. This contour carries
-7.95e-6 m3/s per unit length, which over its 200 m is the same total as in the
point, area and curve versions:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/flow_cntr.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press1/flow_cntr.tcl
         :language: tcl-src

.. figure:: ../_static/map-flow-cntr.svg
   :alt: Pressure field from a rate along a contour
   :width: 80%
   :align: center

   Values run from 202.0 to 250 atmospheres and the debit is 123.9 m3/day.

A real field with a fracture
----------------------------

The press2 examples use the 2001 field of the Arigol oilfield: measured
pressures and rates, impermeable zones, a fault and a measured pressure contour.
The two scripts differ in one input, the direction of the fracture line, and the
pair was the original manual's way to choose that direction.

Both solve a 438 x 641 grid and leave 271736 of its 280758 nodes defined; the
rest are outside the field or behind the impermeable zones.

map_hor_frac.py
~~~~~~~~~~~~~~~

The fracture runs horizontally. The full example:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/map_hor_frac.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press2/map_hor_frac.tcl
         :language: tcl-src

.. figure:: ../_static/map-hor-frac.svg
   :alt: Pressure field with a horizontal fracture
   :width: 80%
   :align: center

   Values run from 11.2 to 21.4 MPa. The measured pressure contour and the
   impermeable zones shape the field around the fracture.

map_ver_frac.py
~~~~~~~~~~~~~~~

The same field with the vertical line:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/map_ver_frac.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/freeflow/press2/map_ver_frac.tcl
         :language: tcl-src

.. figure:: ../_static/map-ver-frac.svg
   :alt: Pressure field with a vertical fracture
   :width: 80%
   :align: center

   Values run from 10.7 to 21.4 MPa; the pressure contours tilt the other way,
   and the undefined region is the same.

Each example prints the debit through the region, the pressure at (34967,
58314), the residuals against the measured -40.3844832 m3/day and 12 MPa, and
the roughness ``surf_D1``. Printing those numbers is the comparison: the debit
and pressure residuals trade against each other, and the roughness says which
field is smoother.

Both ``surf_debit`` and ``surf_debit_rect`` answer ``undef_value`` for a point
or a rectangle outside the grid, or one that touches an undefined cell. The
rectangle used to answer ``FLT_MAX`` regardless of ``undef_value``; it now
follows the same setting as the point query.

Reading the data
----------------

The measured files are columned text, and the examples show the column arguments
in use:

.. list-table::
   :header-rows: 1
   :widths: 32 24 44

   * - File
     - Loaded as
     - Columns and scaling
   * - ``PZab_2001.txt``
     - points, ``press2001``
     - date, well, y, x, pressure: ``col1=4 col2=3 col3=5``, then ``*0.1013``
       from atmospheres to MPa
   * - ``Q_2001.txt``
     - points, ``debits2001``
     - the same columns for y, x and rate, then ``*-1`` because the rates are
       stored with the opposite sign
   * - ``VNK*.txt``, ``ZAM*.txt``
     - curves and areas
     - y then x: ``col1=2 col2=1``
   * - ``lines/P_2001_236_*.txt``
     - contour
     - the measured pressure contour, then ``cntr_mult_real(0.1013)``
   * - ``lines/frac_236_*.txt``
     - curve
     - the fracture line, with the measured rate applied by ``flow_curve``
