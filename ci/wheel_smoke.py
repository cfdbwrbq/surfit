"""Smoke test for an installed wheel.

Runs the area example from the installed package and checks the result against
the values the Tcl front end produces, so a wheel that builds but cannot solve
does not pass.

  PYTHONPATH=<install target> python3 ci/wheel_smoke.py <install target>

It deliberately does not put the build tree on the path: the point is that the
installed package finds its own shared libraries.
"""

import os
import sys

import numpy as np

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "examples", "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area5")

#: The result of this task, as the Tcl front end has produced it all along.
EXPECTED_SHAPE = (121, 121)
EXPECTED_DEFINED = 13120
EXPECTED_MIN = 10.0
EXPECTED_MAX = 39.83151821423541


def main():
    expected = sys.argv[1] if len(sys.argv) > 1 else None

    import surfit

    print("surfit from:", surfit.__file__)
    # The point is that the installed package found its own libraries, so it
    # must come from the install target and not from a build tree.
    if expected:
        target = os.path.abspath(expected) + os.sep
        if not os.path.abspath(surfit.__file__).startswith(target):
            raise SystemExit("imported from %s, expected it under %s"
                             % (surfit.__file__, expected))

    task = surfit.Session(map_name="map_area", tol=5.01187e-006)
    for name in AREAS:
        task.read_areas(os.path.join(DATA, "%s.txt" % name), name)

    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")
    task.solve()

    grid = task.values()
    defined = surfit.defined_mask(grid)
    low = float(grid[defined].min())
    high = float(grid[defined].max())

    assert grid.shape == EXPECTED_SHAPE, grid.shape
    assert int(defined.sum()) == EXPECTED_DEFINED, int(defined.sum())
    assert np.isclose(low, EXPECTED_MIN, atol=1e-9), low
    assert np.isclose(high, EXPECTED_MAX, atol=1e-9), high

    print("wheel solves: %s, %d of %d defined, %.3f .. %.3f"
          % (grid.shape, int(defined.sum()), grid.size, low, high))
    return 0


if __name__ == "__main__":
    sys.exit(main())
