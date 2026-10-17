"""The mask_add example -- examples/surfit/tests/mask_add.tcl.

    python3 examples/python/mask_add.py

A value rule restricted to a mask: where the mask is true the surface is pulled
towards 3 with a weight of 0.2, and elsewhere it follows "test_func" as before.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_mask_add", tol=1e-005)
    task.set_solver("cg")

    assert all(task.mask_load(os.path.join(DATA, "mask.mask"), "test_mask"))
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-10, 10, 0.2, -10, 10, 0.4)

    task.surface("test_func")
    task.mask_add(0.2, 3, "test_mask")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("mask_add.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved mask_add.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
