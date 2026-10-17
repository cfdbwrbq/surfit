"""The contour example -- examples/surfit/tests/contour.tcl, written in Python.

    python3 examples/python/contour.py

Builds a surface from three contours: it passes through the small and the centre
contour exactly, and follows the big one with a weight of 0.5.  A contour is a
3D polyline -- the value along it is part of the data, which is what separates
it from a curve.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
CONTOURS = ("cntr_small_circle", "cntr_big_circle", "cntr_center")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_cntr", tol=1e-005)
    task.set_solver("cg")

    for name in CONTOURS:
        assert all(task.read_contours(os.path.join(DATA, "%s.xyz" % name), name)), name

    task.grid(-1000, 1000, 20, -1000, 1000, 20)

    task.contour("cntr_small_circle")
    task.contour("cntr_center")
    task.completer()
    task.contour_add(0.5, "cntr_big_circle")

    task.solve()
    return task


def main():
    task = build()
    task.save("contour.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved contour.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
