"""Spatial residual diagnostics.

  python3 test_spatial_diagnostics.py
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
    checker = np.indices((8, 8)).sum(axis=0) % 2
    checker = checker.astype(float)
    negative = surfit.morans_i(checker)
    assert negative["i"] < 0
    assert negative["p"] < 0.05

    smooth = np.add.outer(np.arange(8.0), np.arange(8.0))
    positive = surfit.morans_i(smooth)
    assert positive["i"] > 0

    x = np.array([0.0, 1.0, 0.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    y = np.array([0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0])
    residuals = x * 2.0
    variogram = surfit.residual_variogram(x, y, residuals, bins=4)
    assert len(variogram["lag"]) == 4
    assert np.nanmax(variogram["gamma"]) > np.nanmin(variogram["gamma"])

    distance = surfit.distance_to_data(
        [0.0, 10.0], [0.0, 0.0], [0.0], [0.0])
    assert np.allclose(distance, [0.0, 10.0])
    rows = surfit.error_by_distance(
        [0.0, 10.0, 20.0], [1.0, -1.0, 2.0], bins=2, max_distance=20.0)
    assert sum(row["count"] for row in rows) == 3

    groups = surfit.error_by_group([1.0, -1.0, 3.0], ["a", "a", "b"])
    assert groups[0]["group"] == "a"
    assert groups[0]["bias"] == 0.0
    assert groups[1]["mae"] == 3.0
    print("PASS: Moran's I, residual variogram and error by distance/group")


if __name__ == "__main__":
    main()
