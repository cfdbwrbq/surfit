"""First steps: seven points, a grid, two rules, a solve and a result.

    python3 examples/python/first_steps.py

The smallest complete task, and the one the "First steps" page walks through.
It writes the surface to ``first_steps.dat`` and to an HTML page that opens in a
browser, so the whole path from data to a map is in one file.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="first_steps", tol=1e-006)

    # The measurements: x, y and the value, one point per line.
    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "wells"))

    # A regular grid over the region, with a cell of 0.25 in both directions.
    task.grid(-10, 10, 0.25, -10, 10, 0.25)

    # Two rules: pass through the measurements, stay smooth between them.
    task.points("wells")
    task.completer()

    task.solve()
    return task


def main():
    task = build()

    # Two ways to keep the result: the surface on its own, and a page for the
    # browser.  file_save() would store the whole task instead.
    task.save("first_steps.dat")
    task.save_viewer("first_steps.html", title="first steps", levels=14)

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved first_steps.dat and first_steps.html, grid %s, "
          "%d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))


if __name__ == "__main__":
    main()
