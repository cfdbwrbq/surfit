"""The contour BLN round trip -- examples/surfit_io/bln/cntr_bln.tcl.

    python3 examples/python/cntr_bln.py

Five contours go into one BLN file and come back out of it.  A contour carries
its Z value, so the round trip also has to preserve the third coordinate.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit_io", "bln")
CONTOURS = ("cntr_small_circle", "cntr1", "cntr2", "cntr_big_circle",
            "cntr_center")


def build():
    """Runs the round trip and returns the session with the loaded contours."""
    task = surfit.Session("map")

    for name in CONTOURS:
        assert all(task.read_contours(os.path.join(DATA, "%s.xyz" % name), name)), name

    assert all(task.cntr_save_bln("cntrs.bln", "cntr_*"))
    task.clear_data()

    assert all(task.cntr_load_bln("cntrs.bln", "cntr_*"))
    return task


def main():
    task = build()
    print("wrote cntrs.bln and loaded %d contour(s): %s"
          % (task.cntr_size(), ", ".join(task.cntr_getName("cntr_*"))))


if __name__ == "__main__":
    main()
