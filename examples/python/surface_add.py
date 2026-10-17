"""The surface_add example -- examples/surfit/tests/surface_add.tcl.

    python3 examples/python/surface_add.py

A surface added with a small weight: the completer alone would give a plane,
and "test_func" bends it slightly towards its own shape.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_surface_add", tol=1e-005)
    task.set_solver("cg")

    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid(-10, 10, 0.2, -10, 10, 0.2)

    task.completer()
    task.surface_add(0.01, "test_func")

    task.solve()
    return task


def main():
    task = build()
    task.save("surface_add.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved surface_add.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
