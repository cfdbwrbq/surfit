"""The surface_ineq example -- examples/surfit/tests/surface_ineq.tcl.

    python3 examples/python/surface_ineq.py

Inequalities against surfaces: "test_func" shifted up by 80 becomes a lower
bound, shifted up by 90 an upper bound, and seven points are honoured exactly.
The result is squeezed between the two copies of the surface.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
FUNC = os.path.join(DATA, "func.func")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_surface_ineq", tol=1e-005)
    task.set_solver("cg")

    # Two copies of the same surface, one shifted up by 80 and one by 90.
    assert all(task.surf_load(FUNC, "test_func"))
    task.surf_plus_value(80, "test_func")
    task.surf_setName("test_func_geq", "test_func")

    assert all(task.surf_load(FUNC, "test_func"))
    task.surf_plus_value(90, "test_func")
    task.surf_setName("test_func_leq", "test_func")

    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "7points"))

    task.grid(-10, 10, 0.2, -10, 10, 0.2)

    task.surface_geq("test_func_geq")
    task.points("7points")
    task.completer(2, 1)

    task.solve()
    return task


def main():
    task = build()
    task.save("surface_ineq.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved surface_ineq.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
