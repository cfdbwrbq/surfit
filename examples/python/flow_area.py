"""The flow_area example -- examples/freeflow/press1/flow_area.tcl.

    python3 examples/python/flow_area.py

The same rate, spread over an area: ``flow_area`` gives -0.00159 m3/s to the
whole central square instead of to a point.  The field is the pressure that
moves that much fluid out of the square.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "freeflow", "press1")
PRESS = os.path.join(DATA, "press.xyz")
DAY = 24 * 3600


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_flow_area", tol=5e-7)

    assert all(task.read_curves(PRESS, "press"))
    assert all(task.read_areas(os.path.join(DATA, "flow_area.txt"),
                               "flow_area_center"))

    task.grid(-1000, 1000, 5, -1000, 1000, 5)

    task.curve(250, "press")
    task.lcm_simple(16.4, 1, 1e-6)
    task.flow_area(-0.00159, "flow_area_center")

    task.solve()
    task.grid_unload()
    return task


def main():
    task = build()
    task.file_save("flow_area.dat")

    debit = DAY * task.surf_debit_rect(-150, -150, 150, 150, 16.4, 1, 1e-6)[0]
    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved flow_area.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("debit through the central square: %.3f m3/day" % debit)


if __name__ == "__main__":
    main()
