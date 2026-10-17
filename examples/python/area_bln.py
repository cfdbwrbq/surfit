"""The area BLN round trip -- examples/surfit_io/bln/area_bln.tcl.

    python3 examples/python/area_bln.py

Reads five polygons, writes one of them as a Surfer BLN file, drops everything,
loads that file back and writes it again.  The two BLN files are the evidence
that the reader and the writer agree.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit_io", "bln")
AREAS = ("area1", "area2", "area3", "area4", "area5")


def build():
    """Runs the round trip and returns the session with the loaded area."""
    task = surfit.Session("map")

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name

    assert all(task.area_save_bln("areas.bln", "area1"))
    task.clear_data()

    assert all(task.area_load_bln("areas.bln", "area1"))
    assert all(task.area_save_bln("areas2.bln", "area1"))
    return task


def main():
    task = build()
    print("wrote areas.bln and areas2.bln; reloaded %s"
          % ", ".join(task.area_getName("area1")))
    print("%d area(s) in memory" % task.area_size())


if __name__ == "__main__":
    main()
