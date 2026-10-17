"""The curve example -- examples/surfit/tests/curve.tcl.

    python3 examples/python/curve.py

Four isolines used as data: three carry an exact value, one is added with a
weight of 0.5.  A curve is 2D, so the value comes from the rule, not from the
line -- which is what separates it from a contour.
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
    task = surfit.Session(map_name="map_curve", tol=1e-005)
    task.set_solver("cg")

    for name in CURVES:
        assert all(task.read_curves(os.path.join(DATA, "%s.xy" % name), name)), name

    task.grid_auto(10, 10)

    task.curve(10, "iso1")
    task.curve(50, "iso3")
    task.curve(30, "iso4")
    task.completer(1, 1.6)
    task.curve_add(40, 0.5, "iso2")

    task.solve()
    return task


def main():
    task = build()
    task.save("curve.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved curve.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
