"""The contour_ineq example -- examples/surfit/tests/contour_ineq.tcl.

    python3 examples/python/contour_ineq.py

Two sets of contours, one shifted up by 0.2 against the other.  Each contour
becomes an inequality, so the surface is only required to stay between the
lower and the upper line instead of touching either.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
CONTOURS = ("cntr_big_circle2", "cntr_big_circle", "cntr_center2",
            "cntr_center", "cntr_small_circle2", "cntr_small_circle")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_cntr_ineq", tol=1e-005)
    task.set_solver("cg")

    for name in CONTOURS:
        assert all(task.read_contours(os.path.join(DATA, "%s.xyz" % name), name)), name

    task.grid(-1000, 1000, 20, -1000, 1000, 20)

    task.contour_geq("cntr_big_circle")
    task.contour_leq("cntr_big_circle2")
    task.contour_geq("cntr_center")
    task.contour_leq("cntr_center2")
    task.contour_geq("cntr_small_circle")
    task.contour_leq("cntr_small_circle2")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("contour_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved contour_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
