"""The pressure field example -- examples/freeflow/press1/points.tcl.

    python3 examples/python/press_points.py

The baseline of the flow examples: the boundary curve is fixed at 250
atmospheres and the well at the centre at 200.  No rate is given, so the field
is interpolated between the two pressures under the conservation law.
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
    task = surfit.Session(map_name="map_points", tol=5e-7)

    assert all(task.read_curves(PRESS, "press"))
    assert all(task.read_points(os.path.join(DATA, "press_c.xyz"),
                                "center_press_point"))

    task.grid(-1000, 1000, 5, -1000, 1000, 5)

    task.points("center_press_point")
    task.curve(250, "press")
    task.lcm_simple(16.4, 1, 1e-6)

    task.solve()
    task.grid_unload()
    return task


def main():
    task = build()
    task.file_save("points.dat")

    debit = DAY * task.surf_debit_rect(-150, -150, 150, 150, 16.4, 1, 1e-6)[0]
    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved points.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("debit through the central square: %.3f m3/day" % debit)


if __name__ == "__main__":
    main()
