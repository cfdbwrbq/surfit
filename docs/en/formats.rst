File formats
============

The native format is the surfit data file, written and read by ``surf_save`` and
``surf_load`` and friends; it stores the whole task, not just a grid. Everything
else comes from the ``surfit_io`` plugin, which the Tcl front end loads
separately and the Python package includes.

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

These four families share the same set of formats, with the command names
following the data type: ``pnts_``, ``curv_``, ``cntr_`` and ``area_``.

.. list-table::
   :header-rows: 1
   :widths: 30 35 35

   * - Format
     - Load
     - Save
   * - surfit native
     - ``<type>_load``
     - ``<type>_save``
   * - Columned text
     - ``<type>_read``
     - ``<type>_write``
   * - Surfer BLN
     - ``<type>_load_bln``
     - ``<type>_save_bln``
   * - ESRI shapefile
     - ``<type>_load_shp``
     - ``<type>_save_shp``

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

Masks
-----

``mask_save_grd`` and ``mask_save_xyz`` write raster masks;

``mask_load`` reads one back from a surfit data file.

Reading a directory
-------------------

The loaders accept a shell pattern in the file name rather than a single path,
and return one flag per matched file:

.. code-block:: python

   flags = surfit.area_read("zones/*.c*")
   assert all(flags)

In this case the names are derived from the file names, since no explicit name
was given.
