"""The area example -- examples/surfit/tests/area.tcl, written in Python.

    python3 examples/python/area.py

Builds a surface from five polygonal areas: inside area1 it equals 10, inside
area3 it equals 30, area5 stays undefined, and the other two are approximated
with a weight.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area5")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_area", tol=5.01187e-006)

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name

    task.grid(-12, 12, 0.2, -12, 12, 0.2)

    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")

    task.solve()
    return task


def main():
    task = build()
    task.save("area.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
