"""Grid collar and crop helpers.

  python3 test_padding.py
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
        "step_x": 0.5, "step_y": 0.5, "count_x": 21, "count_y": 21,
    }
    padded = surfit.pad_extent(extent, margin=1.0)
    assert padded["min_x"] == -1.0
    assert padded["max_x"] == 11.0
    assert padded["count_x"] == 25
    padded_values = np.zeros((padded["count_y"], padded["count_x"]))
    cropped, cropped_extent = surfit.crop_surface(
        padded_values, padded, extent)
    assert cropped.shape == (21, 21)
    assert cropped_extent["min_x"] == 0.0
    assert cropped_extent["max_x"] == 10.0
    assert cropped_extent["count_x"] == 21
    percent = surfit.pad_extent(extent, percent=10.0)
    assert percent["min_x"] == -1.0
    assert percent["max_x"] == 11.0
    print("PASS: grid collar and crop")


if __name__ == "__main__":
    main()
