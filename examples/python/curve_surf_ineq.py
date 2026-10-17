"""The curve_surf_ineq example -- examples/surfit/tests/curve_surf_ineq.tcl.

    python3 examples/python/curve_surf_ineq.py

Inequalities with values taken from another surface: above "test_func" along
"spiral2" and below it along "spiral".  The two spirals interleave, so the
result is a surface threaded between them.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_curv_surf_ineq", tol=1e-004)
    task.set_solver("cg")

    assert all(task.read_curves(os.path.join(DATA, "spiral2.xy"), "spiral2"))
    assert all(task.read_curves(os.path.join(DATA, "spiral.xy"), "spiral"))
    assert all(task.surf_load(os.path.join(DATA, "func.func"), "test_func"))

    task.grid_auto()

    task.curve_surf_leq("test_func", "spiral")
    task.curve_surf_geq("test_func", "spiral2")
    task.completer()

    task.solve()
    return task


def main():
    task = build()
    task.save("curve_surf_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved curve_surf_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
