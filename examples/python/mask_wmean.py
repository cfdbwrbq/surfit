"""The mask_wmean example -- examples/surfit/tests/mask_wmean.tcl.

    python3 examples/python/mask_wmean.py

A weighted average under a mask: the surface averages 2 where "mask_not" is
true, weighted by "test_func", while the points are honoured exactly.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_mask_wmean", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "points.txt"), "points"))
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))
    assert all(task.mask_load(os.path.join(DATA, "mask_not.mask"), "test_mask"))

    task.grid(-10, 10, 0.2, -10, 10, 0.4)

    task.points("points")
    task.mask_wmean(2, "test_mask", "test_func")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("mask_wmean.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved mask_wmean.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("surface weighted mean value for test_mask: %.4f"
          % task.surf_mask_wmean("test_mask", "test_func",
                                 "map_mask_wmean")[0])


if __name__ == "__main__":
    main()
