File formats
============

The native format is the surfit data file. ``file_save`` and ``file_load``
write and read the whole task -- data, rules and the result; ``surf_save`` and
``surf_load`` store one surface, and every data type has its own ``<type>_save``
and ``<type>_load``. Everything else comes from the ``surfit_io`` plugin, which
the Tcl front end loads separately and the Python package includes.

Grids and surfaces
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 34 36

   * - Format
     - Load
     - Save
   * - surfit native
     - ``surf_load``
     - ``surf_save``
   * - Surfer ASCII and binary grids (v6, v7)
     - ``surf_load_grd``
     - ``surf_save_grd``
   * - GMT grd
     - ``surf_load_gmt``
     - ``surf_save_gmt``
   * - Grass ASCII
     - ``surf_load_grass``
     - ``surf_save_grass``
   * - ArcGIS ASCII grid
     - ``surf_load_arcgis``
     - ``surf_save_arcgis``
   * - Three column xyz
     - ``surf_load_xyz``
     - ``surf_save_xyz``
   * - JPEG (pixels become heights)
     - ``surf_load_jpg``
     - ``surf_save_jpg``
   * - BMP (pixels become heights)
     - ``surf_load_bmp``
     - ``surf_save_bmp``

Points, curves, contours and areas
----------------------------------

The command names follow the data type: ``pnts_``, ``curv_``, ``cntr_`` and
``area_``. Not every format exists for every type:

* **surfit native** -- all four: ``<type>_load`` and ``<type>_save``.
* **Columned text** -- all four: ``<type>_read`` and ``<type>_write``.
* **Surfer BLN** -- curves, contours and areas: ``curv_*_bln``, ``cntr_*_bln``,
  ``area_*_bln``. Points have no BLN reader or writer.
* **ESRI shapefile** -- all four: ``<type>_load_shp`` and ``<type>_save_shp``.

``<type>_read`` and ``<type>_write`` work on columned text files and take the
column numbers and the delimiter, which default to the first columns and
whitespace:

.. code-block:: tcl

   pnts_read "model.txt" "model" 3 4 8 2 "\t" 1

That reads x, y and z from columns 3, 4 and 8, with column 2 carried along, a
tab delimiter and one header line skipped. In Python the same call is:

.. code-block:: python

   surfit.pnts_read("model.txt", "model", col1=3, col2=4, col3=8, col4=2,
                    delimiter="\t", skip_lines=1)

Digital elevation models
------------------------

DEMs come from the ``globe`` library, which the Tcl front end loads separately
and the Python package includes. They are georeferenced rasters, not surfaces:
the loader keeps the tile's origin and step.

.. list-table::
   :header-rows: 1
   :widths: 34 33 33

   * - Format
     - Load
     - Save
   * - surfit native
     - ``dem_load``
     - ``dem_save``
   * - Surfer grid (ASCII, ``DSAA``)
     - ``dem_load_grd``
     - ``dem_save_grd``
   * - DTM
     - ``dem_load_dtm``
     - ``dem_save_dtm`` (not implemented)
   * - SRTM HGT tile
     - ``dem_load_hgt``
     - --
   * - zipped SRTM HGT tile
     - ``dem_load_hgt_zip``
     - --
   * - GTOPO30 / GLOBE
     - ``dem_load_globe``
     - --
   * - Three column xyz
     - --
     - ``dem_save_xyz``

Two caveats belong to the formats themselves. ``dem_load_hgt_zip`` needs zlib:
the CMake build detects it with ``find_package(ZLIB)`` and enables the loader; a
build without zlib reports "zlib not detected" and returns nothing.
``dem_save_dtm`` is declared in the headers, but the implementation logs
"Not implemented!" and returns false, so a DTM tile can be read and not
written.

The DEM loaders take a file pattern and find the tile by its name; for an HGT
tile the name also carries the coordinates. :doc:`python` has the details, and
:doc:`terrain` walks through a real tile in both front ends.

Masks
-----

``mask_save`` writes a mask to the native file; ``mask_save_grd`` and
``mask_save_xyz`` write a Surfer grid or three-column xyz. ``mask_load`` reads
one back from a surfit data file.

Reading a directory
-------------------

Most loaders -- the formats plugin and the DEM loaders alike -- accept a shell
pattern in the file name rather than a single path, and return one flag per
matched file:

.. code-block:: python

   flags = surfit.area_read("zones/*.c*")
   assert all(flags)

In this case the names are derived from the file names, since no explicit name
was given.

Worked examples
---------------

Six round trips under ``examples/python/`` show the plugin from the Python side.
Each reads text data, writes a file, drops the data and reads the file back, so
the second write is the evidence that the reader and the writer agree.
``test_examples.py`` runs each of them and its Tcl original and compares every
file they write, byte for byte.

The BLN writer appends to the file it is given instead of overwriting it, so an
example is meant to run in a directory where its output does not exist yet; the
test gives both sides a fresh directory.

area_bln.py
~~~~~~~~~~~

The five polygons are read, ``area1`` is written to ``areas.bln``, the data is
dropped, the file is read back and written again as ``areas2.bln``:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/area_bln.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/bln/area_bln.tcl
         :language: tcl-src

cntr_bln.py
~~~~~~~~~~~

Five contours, with their Z values, go into one BLN file and come back:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/cntr_bln.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/bln/cntr_bln.tcl
         :language: tcl-src

curv_bln.py
~~~~~~~~~~~

Four curves are written and three are loaded back by name pattern -- the file
pattern and the name pattern are independent:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/curv_bln.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/bln/curv_bln.tcl
         :language: tcl-src

area_shp.py
~~~~~~~~~~~

A shapefile is three files. The saver takes a base name and writes ``.shp``,
``.shx`` and ``.dbf``; the loader takes a file pattern, so both calls name the
``.shp`` file:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/area_shp.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/shp/area_shp.tcl
         :language: tcl-src

curv_shp.py
~~~~~~~~~~~

The same for four curves, loading three back:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/curv_shp.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/shp/curv_shp.tcl
         :language: tcl-src

cntr_shp.py
~~~~~~~~~~~

Five contours are read and the three named ``cntr_*`` are written to one
shapefile and loaded back with their Z values. The set mixes flat contours with
a varying-Z one, which is the case the saver used to fail on:

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/cntr_shp.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/surfit_io/shp/cntr_shp.tcl
         :language: tcl-src

One shipped script is not ported: ``const_cntr.tcl`` reads a shapefile that is
not part of the repository. Two of the shapefile examples above were repaired as
well: ``area_shp`` and ``curv_shp`` named the output ``.bln``, and because the
loader treats the name as a file pattern they silently loaded nothing. Both now
name the ``.shp`` file, and a generated ``curvs.bln`` that the distribution
carried was removed so the BLN example starts clean.

``cntr_shp.py`` also exercises a fix in the saver. It used to choose the shape
type from the first contour, so a set that mixes flat contours with a varying-Z
one failed halfway and left a partial file. ``cntr_save_shp`` now decides the
type over all matched contours first -- ARCZ if any of them varies -- and then
writes them all with that type; a flat contour is written as ARCZ with its
constant Z. Loading such a file needs no ``zfield``; the argument remains for 2D
files written by older versions.
