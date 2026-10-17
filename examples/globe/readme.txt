N00E006.hgt.zip is the SRTM tile N00E006 (0..1 N, 6..7 E) at 3 arcseconds:
1201 x 1201 samples of big-endian signed 16-bit metres, the north row first,
the sea at 0.  dem.tcl and dem_add.tcl need it in the current directory, and
run_all.tcl stops with a message when it is not there.

The repository ships the tile so that the two examples run and are compared
byte for byte with their Python ports (src/pysurfit/tests/test_examples.py).
It was built from the public 1-arcsecond terrain data at

    https://s3.amazonaws.com/elevation-tiles-prod/skadi/N00/N00E006.hgt.gz

which is a full tile (3601 x 3601, 25 MB): each 3 x 3 block was averaged down to
one sample of the 1201 x 1201 tile, with values at or below sea level counted
as 0, so the tile follows the SRTM convention of "sea is 0".

The original NASA distribution the script was written against,
ftp://e0srp01u.ecs.nasa.gov/srtm/version1/Africa/N00E006.hgt.zip, is gone.  The
same tile can be obtained from USGS EarthExplorer or OpenTopography, both of
which need an account.

The canyon/ directory needs a USA DTM and nine further tiles; see its readme.
