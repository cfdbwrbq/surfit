"""The wmean example -- examples/surfit/tests/wmean.tcl.

    python3 examples/python/wmean.py

A weighted average: the surface passes through seven points and its average is
30 with "test_func" as the weight, so the average is biased towards the places
where that surface is high.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_wmean", tol=1e-006)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "7points"))
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-10, 10, 0.1, -10, 10, 0.1)

    task.points("7points")
    task.wmean(30, "test_func", 0)
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("wmean.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved wmean.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("surface weighted mean value is %.4f"
          % task.surf_wmean("test_func", "map_wmean")[0])


if __name__ == "__main__":
    main()
