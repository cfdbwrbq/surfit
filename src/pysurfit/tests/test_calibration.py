"""Split-conformal calibration from held-out residuals.

  python3 test_calibration.py
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
    residuals = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    quantile = surfit.conformal_quantile(residuals, level=0.8)
    assert quantile == 4.0, quantile
    interval = surfit.calibrated_interval(10.0, residuals, level=0.8)
    assert interval["lower"] == 6.0
    assert interval["upper"] == 14.0
    field = surfit.calibrated_interval(
        np.array([[1.0, 2.0]]), residuals, level=0.6)
    assert field["lower"].shape == (1, 2)
    assert np.isclose(field["quantile"], 3.0)
    for bad in (0.0, 1.0):
        try:
            surfit.conformal_quantile(residuals, level=bad)
        except ValueError:
            pass
        else:
            raise AssertionError("bad level did not raise")
    print("PASS: split-conformal quantile and interval")


if __name__ == "__main__":
    main()
