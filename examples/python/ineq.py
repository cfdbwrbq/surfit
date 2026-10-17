"""The ineq example -- examples/surfit/tests/ineq.tcl.

    python3 examples/python/ineq.py

The simplest inequality example: six points, a lower bound of 80, an upper
bound of 120, and a completer in between.  The surface passes through the
points and stays inside the band everywhere.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_ineq", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "7points"))

    task.grid_auto()

    task.leq(120)
    task.geq(80)
    task.points("7points")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
