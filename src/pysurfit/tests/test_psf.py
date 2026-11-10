"""Point-spread width measured from an impulse response.

A Gaussian impulse with a known sigma is placed on a grid; the measured half
width and fitted sigma must recover it within one grid step.

  python3 test_psf.py
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
    step = 0.1
    count = 101
    extent = {
        "min_x": -5.0, "max_x": 5.0, "min_y": -5.0, "max_y": 5.0,
        "step_x": step, "step_y": step, "count_x": count, "count_y": count,
    }
    x = np.linspace(extent["min_x"], extent["max_x"], count)
    y = np.linspace(extent["min_y"], extent["max_y"], count)
    grid_x, grid_y = np.meshgrid(x, y)
    sigma = 1.2
    values = np.exp(-((grid_x - 0.3) ** 2 + (grid_y - 0.2) ** 2)
                    / (2.0 * sigma ** 2))
    report = surfit.psf_report(values, extent, center=(0.3, 0.2))
    expected = sigma * np.sqrt(2.0 * np.log(2.0))
    assert abs(report["half_width"] - expected) < step * 2.0, report
    assert abs(report["sigma"] - sigma) < step * 3.0, report
    assert report["resolved_features"] > report["grid_step"]

    def build(center_x, center_y):
        field = np.exp(-((grid_x - center_x) ** 2 + (grid_y - center_y) ** 2)
                       / (2.0 * sigma ** 2))
        return field

    estimated = surfit.estimate_psf(build, 0.3, 0.2, extent)
    assert estimated["report"]["sigma"] == report["sigma"]
    print("PASS: PSF half-width and Gaussian sigma")


if __name__ == "__main__":
    main()
