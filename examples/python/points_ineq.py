"""The points_ineq example -- examples/surfit/tests/points_ineq.tcl.

    python3 examples/python/points_ineq.py

Two sets of measured points used as bounds: the surface has to stay above every
point of one set and below every point of the other.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_points_ineq", tol=1e-004)

    assert all(task.read_points(os.path.join(DATA, "points_geq.txt"), "points_geq"))
    assert all(task.read_points(os.path.join(DATA, "points_leq.txt"), "points_leq"))

    task.grid_auto()

    task.points_geq("points_geq")
    task.points_leq("points_leq")
    task.completer(0, 1)

    task.solve()
    return task


def main():
    task = build()
    task.save("points_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved points_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
