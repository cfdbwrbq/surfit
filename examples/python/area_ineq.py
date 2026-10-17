"""The area_ineq example -- examples/surfit/tests/area_ineq.tcl.

    python3 examples/python/area_ineq.py

The area example with bounds added: inside area6 the surface has to stay
between 15 and 20, so the other areas pull it into that band rather than
through it.
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
    task = surfit.Session(map_name="map_area_ineq", tol=1e-006)

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name

    task.grid(-12, 12, 0.2, -12, 12, 0.2)

    task.area(30, "area3")
    task.area_leq(20, "area6")         # area6 stays at or below 20
    task.area_geq(15, "area6")         # and at or above 15
    task.area(10, "area1")
    task.area("undef", "area5")
    task.completer(1, 0)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")

    task.solve()
    return task


def main():
    task = build()
    task.save("area_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("maximum value in area6: %.4f"
          % task.surf_area_maxz("area6", "map_area_ineq")[0])


if __name__ == "__main__":
    main()
