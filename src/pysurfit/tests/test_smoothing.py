"""Outer smoothing selection with spatial CV.

  python3 test_smoothing.py
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
    rng = np.random.default_rng(2026)
    x = rng.uniform(0.0, 10.0, 40)
    y = rng.uniform(0.0, 10.0, 40)
    z = np.zeros(40)
    extent = {
        "min_x": 0.0, "max_x": 10.0, "min_y": 0.0, "max_y": 10.0,
        "step_x": 1.0, "step_y": 1.0, "count_x": 11, "count_y": 11,
    }

    def build(parameter, train, train_weights):
        assert train.size > 0
        return np.full((11, 11), float(parameter)), extent

    result = surfit.select_parameter(
        build, x, y, z, parameters=[0.0, 1.0, 2.0],
        folds=4, mode="block", block=2.5)
    assert result["parameter"] == 0.0
    assert result["scores"][0]["rmse"] == 0.0
    assert len(result["scores"]) == 3
    print("PASS: automatic parameter selection via spatial CV")


if __name__ == "__main__":
    main()
