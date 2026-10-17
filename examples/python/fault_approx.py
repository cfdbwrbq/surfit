"""The fault_approx example -- examples/surfit/tests/fault_approx.tcl.

    python3 examples/python/fault_approx.py

The faults example without the exact condition at the points: they are added
with a weight, so the surface is allowed to miss each measurement a little.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
LINES = ("flt_line1", "flt_line2", "flt_line3", "flt_line4")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_faults_approx", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "11points.txt"), "11points"))
    for name in LINES:
        assert all(task.read_curves(os.path.join(DATA, "%s.txt" % name), name)), name

    task.grid(1, 99, 1, -50, 50, 1)

    for name in LINES:
        task.fault(name)
    task.completer(0.5, 2)
    task.points_add(1, "11points")

    task.solve()
    return task


def main():
    task = build()
    task.save("fault_approx.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved fault_approx.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
