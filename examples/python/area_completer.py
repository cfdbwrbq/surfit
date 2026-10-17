"""The area_completer example -- examples/surfit/tests/area_completer.tcl.

    python3 examples/python/area_completer.py

Applies the "completer" rule inside one area only: anisotropy with a factor of
3 at 30 degrees inside "some_area", the ordinary smoothing everywhere else.
Eleven points pin the surface down.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_area_completer", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "11points.txt"), "11points"))
    assert all(task.read_areas(os.path.join(DATA, "some_area.txt"), "some_area"))

    task.grid_auto()

    task.points("11points")
    task.area_completer("some_area", 1, 2, 30, 2, 1)
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("area_completer.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved area_completer.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
