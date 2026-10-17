Terrain
=======

``globe`` adds digital elevation models to the engine. A DEM is a raster with a
georeference: it knows its corner coordinates and its step, so it can be sampled
at any point and projected onto the task grid. Two rules consume it:

* ``dem`` makes the surface follow the DEM — a hard condition, like ``area`` with
  a value at every node;
* ``dem_add`` adds the DEM with a weight on top of the previous rules, so the
  result is a compromise between the trend and the measured relief.

The examples are ports of ``examples/globe/dem.tcl`` and ``dem_add.tcl``. Each
writes the same ``.dat`` as its Tcl original (``test_examples.py`` checks that
byte for byte), and the maps below are drawn by ``make_images.py`` from the
examples themselves.

The tile
--------

Both examples read ``N00E006.hgt.zip``: a one-degree SRTM tile at 3 arcseconds,
1201 x 1201 cells, inside a zip. The HGT format has no header at all:

* the name carries the georeference — ``N00E006`` is the tile whose south-west
  corner is 0 N, 6 E, and it covers one degree north and east;
* the length carries the resolution — 1201 x 1201 samples is SRTM-3 (3
  arcseconds), 3601 x 3601 is SRTM-1 (1 arcsecond);
* the samples are big-endian signed 16-bit metres, row by row from the north
  edge, with ``-32768`` for a void and 0 for the sea.

That is why the loaders take a file *pattern* and why a cropped tile cannot be
read: ``_dem_load_hgt`` derives the extent from the name and checks the sample
count against the file length. The zip variant needs zlib; the CMake build
enables it when it finds the library. The uncompressed ``.hgt`` is read by
``dem_load_hgt``, the zip by ``dem_load_hgt_zip``.

The tile shipped with the examples is the whole N00E006 square, averaged from
the public 1-arcsecond terrain data on AWS (``elevation-tiles-prod/skadi``) down
to SRTM-3 resolution with the sea floor set to 0, so it reads like an SRTM tile:
Sao Tome rises from a flat sea, and the peak at 0.27 N is Pico de Sao Tome. It
is 164 KB, which is why the repository can carry it; a full 1-arcsecond tile is
25 MB, and those are neither committed nor downloaded by the checks.

The examples
------------

Both examples build the same grid — 6.4 E to 6.8 E and 0 to 0.48 N in steps of
0.0005 degrees, 801 x 961 nodes — and differ only in the rule.

dem.py
~~~~~~

The DEM is a hard condition: every node of the grid is set from the tile, so
the solver has nothing to minimise and says so. This is the shortest way to
bring measured relief into a task.

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/dem.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/globe/dem.tcl
         :language: tcl-src

.. figure:: ../_static/map-dem.svg
   :alt: Filled contour map of Sao Tome from the SRTM tile
   :width: 80%
   :align: center

   Values run from 0 at sea level to 1956 m; the average is 127 m. The whole
   island sits inside the window, and every node is defined.

dem_add.py
~~~~~~~~~~

Here ``completer`` comes first and the DEM is added with a weight, so the
surface is a trend that is pulled towards the measured relief. With weight 1 the
two conditions are comparable and the result is close to, but not equal to, the
tile — the peak loses about 40 m and the sea is no longer exactly flat.

.. tabs::

   .. tab:: Python

      .. literalinclude:: ../../examples/python/dem_add.py
         :language: python

   .. tab:: Tcl

      .. literalinclude:: ../../examples/globe/dem_add.tcl
         :language: tcl-src

.. figure:: ../_static/map-dem-add.svg
   :alt: Filled contour map of the weighted DEM example
   :width: 80%
   :align: center

   The same window, from -0.1 to 1917 m. The solver needs up to 51 iterations
   per phase, against no iterations at all for the hard rule.

What else the DEM commands do
-----------------------------

A DEM is not only a source of data: ``surf_to_dem`` makes one from a solved
surface, ``dem_to_surf`` projects one onto the grid, ``dem_save_dtm`` and
``dem_load_dtm`` write and read the DTM pair (a text header plus a binary of
16-bit samples), ``dem_save_grd`` and ``dem_load_grd`` round-trip the ASCII grid
format of Golden Software Surfer (``.grd``, the ``DSAA`` header), and
``dem_decomp``/``dem_recons`` walk the coarse levels of the storage.
:doc:`data_types` describes what each of them keeps, and :doc:`commands` has the
full list.

Not ported: the canyon pipeline
-------------------------------

``examples/globe/canyon`` holds three scripts that build a model of the Grand
Canyon from a USA DTM (``usa.hdr`` with ``usa.bin``) and nine SRTM tiles: they
convert the DTM to points, cut them with ``canyon_rect.txt`` and grid what is
left. Neither the DTM nor the tiles are in the repository and the readme's
download link is dead, so the three scripts are listed as deliberately not
ported in ``test_examples.py``. Everything they use is exercised by the two
examples above and by the DEM cases of ``test_all_commands.py``; only the data is
missing.
