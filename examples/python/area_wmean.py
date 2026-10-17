"""The area_wmean example -- examples/surfit/tests/area_wmean.tcl.

    python3 examples/python/area_wmean.py

The area_mean example with a weighted average: inside area6 the surface should
average 40 with "test_func" as the weight, so the average is pulled towards the
places where the weight surface is high.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area5", "area6")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_area_wmean", tol=1e-006)
    task.set_solver("cg")

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-12, 12, 0.1, -12, 12, 0.1)

    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.area_wmean(30, "area6", "test_func")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")

    task.solve()
    return task


def main():
    task = build()
    task.save("area_wmean.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area_wmean.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("surface weighted mean value in area6: %.4f"
          % task.surf_area_wmean("area6", "test_func", "map_area_wmean")[0])


if __name__ == "__main__":
    main()
