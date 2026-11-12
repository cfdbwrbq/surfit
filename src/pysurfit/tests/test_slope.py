"""Global slope and curvature bounds after the solve.

  python3 test_slope.py
"""

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def build(bound):
    task = surfit.Session(map_name="bound", tol=1e-7)
    task.add_points([0.5, 0.4, 0.6, 0.5, 0.5],
                    [0.5, 0.5, 0.5, 0.4, 0.6],
                    [10.0, 0.0, 0.0, 0.0, 0.0], name="p")
    task.grid(0, 1, 0.1, 0, 1, 0.1)
    task.points("p")
    if bound == "slope":
        task.slope_max(5.0)
    else:
        task.curvature_max(1.0)
    task.completer(1, 1.6)
    task.solve()
    return task


def main():
    slope = build("slope")
    values = slope.values()
    step = 1.0 / (values.shape[0] - 1)
    dx = np.abs(np.diff(values, axis=1)) / step
    dy = np.abs(np.diff(values, axis=0)) / step
    assert np.nanmax(dx) <= np.tan(np.deg2rad(5.0)) + 0.01
    assert np.nanmax(dy) <= np.tan(np.deg2rad(5.0)) + 0.01
    assert any(rule["name"] == "f_slope"
               for rule in slope.rule_report()["rules"])
    slope.close()

    curvature = build("curvature")
    values = curvature.values()
    step = 1.0 / (values.shape[0] - 1)
    second = np.abs(values[1:-1, :-2] - 2.0 * values[1:-1, 1:-1] +
                     values[1:-1, 2:]) / (step * step)
    assert np.nanmax(second) <= 1.1
    curvature.close()
    print("PASS: global slope and curvature bounds")


if __name__ == "__main__":
    main()
