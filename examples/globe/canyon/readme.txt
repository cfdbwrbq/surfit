This pipeline needs two things that are not in the repository:

* usa.hdr with usa.bin, a USA digital terrain model, which canyon_prepare.tcl
  converts to points and filters by canyon_rect.txt;
* the SRTM tiles N35W112, N35W113, N35W114, N36W112, N36W113, N36W114,
  N37W112, N37W113 and N37W114, one 1-degree tile each.

The original download, http://gridding.info/download/canyon.zip, is gone.  The
SRTM tiles can be rebuilt from a public source (see ../readme.txt for the one
used for dem.tcl), but the USA DTM is not part of the SRTM distribution, so the
three scripts are listed as deliberately not ported in
src/pysurfit/tests/test_examples.py.

What they do with the data -- dem_load_dtm, dem_to_pnts, pnts_filter_out_area,
dem_to_surf, surf_save -- is exercised by dem.tcl and dem_add.tcl next to this
directory, and by the DEM cases of test_all_commands.py.
