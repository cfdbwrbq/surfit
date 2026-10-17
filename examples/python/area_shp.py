"""The area shapefile round trip -- examples/surfit_io/shp/area_shp.tcl.

    python3 examples/python/area_shp.py

One polygon is written as an ESRI shapefile, loaded back and written again.  The
writer creates three files from the base name -- ``.shp``, ``.shx`` and
``.dbf`` -- and the loader takes a file pattern, so the script names the
``.shp`` file on both sides.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit_io", "shp")
AREAS = ("area1", "area2", "area3", "area4", "area5")


def build():
    """Runs the round trip and returns the session with the loaded area."""
    task = surfit.Session("map")

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name

    assert all(task.area_save_shp("areas.shp", "area1"))
    task.clear_data()

    assert all(task.area_load_shp("areas.shp", "area1"))
    assert all(task.area_save_shp("areas2.shp", "area1"))
    return task


def main():
    task = build()
    print("wrote areas.{shp,shx,dbf} and areas2.{shp,shx,dbf}; "
          "reloaded %s" % ", ".join(task.area_getName("area1")))
    print("%d area(s) in memory" % task.area_size())


if __name__ == "__main__":
    main()
