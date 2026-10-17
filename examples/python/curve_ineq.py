"""The curve_ineq example -- examples/surfit/tests/curve_ineq.tcl.

    python3 examples/python/curve_ineq.py

The curve example with inequalities: the values along the four isolines become
lower and upper bounds instead of equalities, so the result only has to respect
their order.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
CURVES = ("iso1", "iso2", "iso3", "iso4")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_curve_ineq", tol=5e-005)
    task.set_solver("cg")

    for name in CURVES:
        assert all(task.read_curves(os.path.join(DATA, "%s.xy" % name), name)), name

    task.grid_auto(10, 10)

    task.curve_leq(10, "iso1")
    task.curve_geq(50, "iso3")
    task.curve_leq(30, "iso4")
    task.curve_leq(40, "iso2")
    task.completer(1, 1.6)

    task.solve()
    return task


def main():
    task = build()
    task.save("curve_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved curve_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
