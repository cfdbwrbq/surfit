"""Faults: a surface that must break along given lines.

    python3 examples/python/faults.py [output.html]

The Tcl original is examples/surfit/tests/fault.tcl.

Eleven points and four fault lines.  Without the faults the surface would be
smooth; with them it jumps across each line, which is the point of the feature
and why the map below the code in the documentation has visible steps.
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
    task = surfit.Session(map_name="map_faults", tol=1e-005)
    task.set_solver("cg")

    task.pnts_read(os.path.join(DATA, "11points.txt"), "11points")
    for name in LINES:
        task.curv_read(os.path.join(DATA, "%s.txt" % name), name)

    task.grid(1, 99, 0.5, -50, 50, 0.5)

    task.points("11points")
    for name in LINES:
        task.fault(name)
    task.completer(0.5, 2)

    task.solve()
    return task


def main(output="faults.html"):
    task = build()
    task.save("fault.dat")
    grid = task.values()
    print("saved fault.dat, %s, %d of %d nodes defined"
          % (grid.shape, surfit.defined_mask(grid).sum(), grid.size))

    task.save_viewer(output, title="fault example")


if __name__ == "__main__":
    main(*sys.argv[1:])
