"""Variogram redundancy weights downweight a dense cluster."""

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
    rng = np.random.default_rng(12)
    cluster = rng.normal(0.2, 0.01, (10, 2))
    isolated = rng.uniform(0.1, 0.9, (10, 2))
    points = np.vstack((cluster, isolated))
    weights = surfit.variogram_weights(
        points[:, 0], points[:, 1], np.sin(points[:, 0]) + points[:, 1])
    assert np.isclose(weights.mean(), 1.0)
    assert weights[:10].mean() < weights[10:].mean()
    print("PASS: variogram redundancy weights")


if __name__ == "__main__":
    main()
