"""The curve_surf example -- examples/surfit/tests/curve_surf.tcl.

    python3 examples/python/curve_surf.py

Curves take their values from another surface: the result follows "test_func"
along "spiral" and does so with a weight of 0.5 along "spiral2".  The grid is
derived from the data, so it covers both spirals.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_curv_surf", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_curves(os.path.join(DATA, "spiral.xy"), "spiral"))
    assert all(task.read_curves(os.path.join(DATA, "spiral2.xy"), "spiral2"))
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid_auto()

    task.curve_surf("test_func", "spiral")
    task.completer()
    task.curve_surf_add("test_func", 0.5, "spiral2")

    task.solve()
    return task


def main():
    task = build()
    task.save("curve_surf.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved curve_surf.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
