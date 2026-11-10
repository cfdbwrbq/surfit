"""Support-based resolution diagnostics.

  python3 test_resolution.py
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
    extent = {
        "min_x": 0.0, "max_x": 10.0, "min_y": 0.0, "max_y": 10.0,
        "step_x": 0.1, "step_y": 0.1, "count_x": 101, "count_y": 101,
    }
    values = np.ones((101, 101))
    report = surfit.resolution_report(
        extent, x=np.linspace(1, 9, 25), y=np.linspace(1, 9, 25),
        values=values)
    assert report["nyquist"] == 0.2
    assert report["samples"] == 25
    assert report["defined_fraction"] == 1.0
    assert report["samples_per_cell"] < 1.0
    assert "warning" in report
    coarse = surfit.resolution_report(extent)
    assert "data_spacing" not in coarse
    print("PASS: support/resolution diagnostics")


if __name__ == "__main__":
    main()
