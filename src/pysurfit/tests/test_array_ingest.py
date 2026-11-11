"""Build a task from numpy arrays, without a user-written text file.

  python3 test_array_ingest.py
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


def main():
    x = np.array([0.1, 0.2, 0.8, 0.9])
    y = np.array([0.1, 0.2, 0.8, 0.9])
    z = np.array([1.0, 2.0, 3.0, 4.0])
    task = surfit.Session(map_name="array", tol=1e-7)
    assert all(task.add_points(x, y, z, weights=[1, 1, 1, 1], name="p"))
    assert task.pnts_size() == 1
    task.grid(0, 1, 0.25, 0, 1, 0.25)
    assert all(task.points("p"))
    task.completer(1, 1.6)
    task.solve()
    assert task.values().shape == (8, 8)

    curves = surfit.Session(map_name="curve")
    assert all(curves.add_curves([0, 1, 2], [0, 1, 0], name="c"))
    assert curves.curv_size() == 1

    areas = surfit.Session(map_name="area")
    assert all(areas.add_areas([0, 1, 1, 0, 0], [0, 0, 1, 1, 0], name="a"))
    assert areas.area_size() == 1

    contours = surfit.Session(map_name="contour")
    assert all(contours.add_contours([0, 1, 2], [0, 1, 0], [1, 2, 3],
                                     name="ct"))
    assert contours.cntr_size() == 1
    print("PASS: array ingestion for points, curves, areas and contours")


if __name__ == "__main__":
    main()
