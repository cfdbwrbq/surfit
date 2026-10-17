"""The contour shapefile round trip -- examples/surfit_io/shp/cntr_shp.tcl.

    python3 examples/python/cntr_shp.py

Five contours are read and the three whose names match ``cntr_*`` are written to
one shapefile; they come back with their Z values.  The set mixes flat contours
with a varying-Z one, so the saver chooses the 3D shape (ARCZ) for the whole
file: a flat contour must not create an ARC file that the next contour cannot
join.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit_io", "shp")
CONTOURS = ("cntr_small_circle", "cntr1", "cntr2", "cntr_big_circle",
            "cntr_center")


def build():
    """Runs the round trip and returns the session with the loaded contours."""
    task = surfit.Session("map")

    for name in CONTOURS:
        assert all(task.read_contours(os.path.join(DATA, "%s.xyz" % name), name)), name

    assert all(task.cntr_save_shp("cntrs.shp", "cntr_*"))
    task.clear_data()

    # No zfield: the whole file is ARCZ, so the Z values are in the shapes.
    assert all(task.cntr_load_shp("cntrs.shp", "cntr_*"))
    return task


def main():
    task = build()
    print("wrote cntrs.{shp,shx,dbf} and loaded %d contour(s): %s"
          % (task.cntr_size(), ", ".join(task.cntr_getName("cntr_*"))))


if __name__ == "__main__":
    main()
