"""The mask_completer example -- examples/surfit/tests/mask_completer.tcl.

    python3 examples/python/mask_completer.py

The completer applied inside a mask only, with anisotropy: the surface is
smoothed three times more along 30 degrees where the mask is true.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_mask_completer", tol=1e-007)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "points.txt"), "points"))
    assert all(task.mask_load(os.path.join(DATA, "mask.mask"), "test_mask"))

    task.grid(-10, 10, 0.2, -10, 10, 0.4)

    task.points("points")
    task.mask_completer("test_mask", 1, 2, 30, 2)
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("mask_completer.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved mask_completer.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
