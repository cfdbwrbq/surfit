"""The curve shapefile round trip -- examples/surfit_io/shp/curv_shp.tcl.

    python3 examples/python/curv_shp.py

Four isolines go into one shapefile and three come back by pattern.  The writer
produces ``.shp``, ``.shx`` and ``.dbf`` from the base name; loading the
``.shp`` file gives the curves back with their names in the DBF records.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit_io", "shp")
CURVES = ("iso1", "iso2", "iso3", "iso4")


def build():
    """Runs the round trip and returns the session with the loaded curves."""
    task = surfit.Session("map")

    for name in CURVES:
        assert all(task.read_curves(os.path.join(DATA, "%s.xy" % name), name)), name

    assert all(task.curv_save_shp("curvs.shp", "iso*"))
    task.clear_data()

    assert all(task.curv_load_shp("curvs.shp", "iso[1-3]"))
    task.curvs_info()
    return task


def main():
    task = build()
    print("wrote curvs.{shp,shx,dbf} and loaded %d curve(s): %s"
          % (task.curv_size(), ", ".join(task.curv_getName("iso*"))))


if __name__ == "__main__":
    main()
