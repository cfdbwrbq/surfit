"""The flow_points2 example -- examples/freeflow/press1/flow_points2.tcl.

    python3 examples/python/flow_points2.py

Both the pressure and the rate at the well are known.  ``points_add`` keeps the
200-atm measurement with a weight and ``flow_points`` adds the rate, so the
result sits between the pressure-only and the rate-only fields.
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
    task = surfit.Session(map_name="map_flow_points2", tol=5e-7)

    assert all(task.read_curves(PRESS, "press"))
    assert all(task.read_points(os.path.join(DATA, "flow_point.txt"),
                                "center_flow_point"))
    assert all(task.read_points(os.path.join(DATA, "press_c.xyz"),
                                "center_press_point"))

    task.grid(-1000, 1000, 5, -1000, 1000, 5)

    task.curve(250, "press")
    task.lcm_simple(16.4, 1, 1e-6)
    task.points_add(1, "center_press_point")
    task.flow_points("center_flow_point")

    task.solve()
    task.grid_unload()
    return task


def main():
    task = build()
    task.file_save("flow_points2.dat")

    debit = DAY * task.surf_debit_rect(-150, -150, 150, 150, 16.4, 1, 1e-6)[0]
    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved flow_points2.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("debit through the central square: %.3f m3/day" % debit)


if __name__ == "__main__":
    main()
