"""The area_surf_ineq example -- examples/surfit/tests/area_surf_ineq.tcl.

    python3 examples/python/area_surf_ineq.py

Brackets the surface between a surface: above "test_func" in areas 1, 3 and 5,
below it in areas 2, 4 and 6.  The result lies inside that sandwich and is
smooth between the areas.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_area_surf_ineq", tol=1e-005)
    task.set_solver("cg")

    for name in ("area1", "area2", "area3", "area4", "area6"):
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))
    assert all(task.read_areas(os.path.join(DATA, "area5.txt"), "area5"))

    task.grid(-12, 12, 0.1, -12, 12, 0.1)

    task.area_surf_geq("test_func", "area1")
    task.area_surf_leq("test_func", "area2")
    task.area_surf_geq("test_func", "area3")
    task.area_surf_leq("test_func", "area4")
    task.area_surf_geq("test_func", "area5")
    task.area_surf_leq("test_func", "area6")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("area_surf_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area_surf_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
