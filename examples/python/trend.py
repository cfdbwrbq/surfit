"""The trend example -- examples/surfit/tests/trend.tcl.

    python3 examples/python/trend.py

Faults under a regional trend: seven points and two fault lines, with the result
required to look like "test_func" at a large scale.  The faults keep the trend
from being continuous across them.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_trend", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "7points"))
    assert all(task.read_curves(os.path.join(DATA, "1fault2.txt"), "1fault2"))
    assert all(task.read_curves(os.path.join(DATA, "1fault.txt"), "1fault"))
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-10, 10, 0.2, -10, 10, 0.2)

    task.points("7points")
    task.fault("1fault")
    task.fault("1fault2")
    task.trend(1, 10, "test_func")

    task.solve()
    return task


def main():
    task = build()
    task.save("trend.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved trend.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
