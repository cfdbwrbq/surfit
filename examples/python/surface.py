"""The surface example -- examples/surfit/tests/surface.tcl, written in Python.

    python3 examples/python/surface.py

Interpolates a surface from another surface: the result follows "test_func" in
least squares and tends to a plane where the data gives no guidance.  A surface
as data is what makes this different from the points and contours examples.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_surface", tol=1e-005)
    task.set_solver("cg")

    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-10, 10, 0.2, -10, 10, 0.2)

    task.surface("test_func")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("surface.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved surface.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
