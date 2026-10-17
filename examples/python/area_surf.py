"""The area_surf example -- examples/surfit/tests/area_surf.tcl.

    python3 examples/python/area_surf.py

A surface as data inside areas: the result follows "test_func" exactly inside
area6 and approximately inside areas 1 to 4, with a separate weight for each.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area6")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_area_surf", tol=1e-005)
    task.set_solver("cg")

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-12, 12, 0.2, -12, 12, 0.2)

    task.area_surf("test_func", "area6")
    task.completer()
    task.area_surf_add("test_func", 0.07, "area1")
    task.area_surf_add("test_func", 0.1, "area2")
    task.area_surf_add("test_func", 0.1, "area3")
    task.area_surf_add("test_func", 0.05, "area4")

    task.solve()
    return task


def main():
    task = build()
    task.save("area_surf.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area_surf.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
