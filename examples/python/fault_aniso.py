"""The fault_aniso example -- examples/surfit/tests/fault_aniso.tcl.

    python3 examples/python/fault_aniso.py

The faults example on a coarser grid, with anisotropy added to the completer:
inside each block the surface is smoothed three times more along 45 degrees
than across.
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
    task = surfit.Session(map_name="map_faults_aniso", tol=1e-005)
    task.set_solver("cg")

    assert all(task.read_points(os.path.join(DATA, "11points.txt"), "11points"))
    for name in LINES:
        assert all(task.read_curves(os.path.join(DATA, "%s.txt" % name), name)), name

    task.grid(1, 99, 1, -50, 50, 1)

    task.points("11points")
    for name in LINES:
        task.fault(name)
    task.completer(0.5, 2, 45, 2)

    task.solve()
    return task


def main():
    task = build()
    task.save("fault_aniso.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved fault_aniso.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
