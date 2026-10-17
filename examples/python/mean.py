"""The mean example -- examples/surfit/tests/mean.tcl.

    python3 examples/python/mean.py

An average as a gridding condition: the surface passes through seven points and
its mean value over the whole map is 30.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_mean", tol=1e-006)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "7points"))

    task.grid(-10, 10, 0.1, -10, 10, 0.1)

    task.points("7points")
    task.mean(30, 0)
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("mean.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved mean.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("surface mean value is %.4f" % task.surf_mean("map_mean")[0])


if __name__ == "__main__":
    main()
