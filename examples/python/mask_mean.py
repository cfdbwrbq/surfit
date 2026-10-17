"""The mask_mean example -- examples/surfit/tests/mask_mean.tcl.

    python3 examples/python/mask_mean.py

An average under a mask: where the mask is true the surface averages -2, while
the points elsewhere are honoured exactly.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_mask_mean", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "points.txt"), "points"))
    assert all(task.mask_load(os.path.join(DATA, "mask.mask"), "test_mask"))

    task.grid(-10, 10, 0.2, -10, 10, 0.4)

    task.mask_mean(-2, "test_mask")
    task.points("points")
    task.completer(1, 10)

    task.solve()
    return task


def main():
    task = build()
    task.save("mask_mean.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved mask_mean.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("surface mean value with mask: %.4f"
          % task.surf_mask_mean("test_mask", "map_mask_mean")[0])


if __name__ == "__main__":
    main()
