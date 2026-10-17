"""Grids scattered points towards a trend supplied as a numpy array.

    python3 examples/python/trend_from_numpy.py

Shows both directions of the array boundary: add_surface() hands a grid to the
engine, values() takes the result back out.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import numpy as np  # noqa: E402

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")

# The region the scattered points live in, and the region we grid.
X0, X1 = -4.0, 8.0
Y0, Y1 = -6.0, 8.0
STEP = 0.25


def build():
    """Solves the example and returns (session, trend array)."""
    task = surfit.Session(map_name="map_trend", tol=1e-6)

    # A regional trend: a plane, sampled coarsely and handed over as an array.
    count = 10
    step_x = (X1 - X0) / (count - 1)
    step_y = (Y1 - Y0) / (count - 1)
    xs = X0 + step_x * np.arange(count)
    ys = Y0 + step_y * np.arange(count)
    trend = 100.0 + 2.0 * xs[None, :] + 3.0 * ys[:, None]

    task.add_surface(trend, start_x=X0, step_x=step_x,
                     start_y=Y0, step_y=step_y, name="regional")
    assert task.surf_index("regional") == 0, task.names()

    assert all(task.read_points(os.path.join(DATA, "7points.txt"), "wells"))

    task.grid(X0, X1, STEP, Y0, Y1, STEP)
    task.points("wells")          # honour the measurements
    task.surface("regional")      # and follow the regional trend
    task.completer(1, 2)          # without letting it kink
    task.solve()
    return task, trend


def main():
    task, trend = build()
    result = task.values()
    defined = surfit.defined_mask(result)
    print("trend %s -> result %s" % (trend.shape, result.shape))
    print("trend  min=%.3f max=%.3f" % (trend.min(), trend.max()))
    print("result min=%.3f max=%.3f" % (result[defined].min(),
                                        result[defined].max()))


if __name__ == "__main__":
    main()
