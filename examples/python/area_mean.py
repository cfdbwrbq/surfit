"""The area_mean example -- examples/surfit/tests/area_mean.tcl.

    python3 examples/python/area_mean.py

The area example with two averages instead of exact values: the surface should
average 40 inside area6 and 30 over the whole map, which leaves the value
inside area6 free to vary.
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
    task = surfit.Session(map_name="map_area_mean", tol=1e-006)

    for name in AREAS:
        assert all(task.read_areas(os.path.join(DATA, "%s.txt" % name), name)), name

    task.grid(-12, 12, 0.1, -12, 12, 0.1)

    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.area_mean(40, "area6")        # average 40 inside area6
    task.mean(30)                      # average 30 over the whole surface
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")

    task.solve()
    return task


def main():
    task = build()
    task.save("area_mean.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area_mean.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("surface mean value in area6: %.4f"
          % task.surf_area_mean("area6", "map_area_mean")[0])
    print("surface mean value: %.4f" % task.surf_mean("map_area_mean")[0])


if __name__ == "__main__":
    main()
