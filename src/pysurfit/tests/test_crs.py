"""Optional CRS helpers; skips when pyproj is absent.

  python3 test_crs.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    try:
        import pyproj  # noqa: F401
    except ImportError:
        print("SKIP: pyproj is not installed")
        return

    x, y = surfit.to_crs([10.0], [20.0], "EPSG:4326", "EPSG:32637")
    assert x and y
    assert surfit.is_geographic_crs("EPSG:4326")
    assert not surfit.is_geographic_crs("EPSG:32637")
    assert surfit.require_projected("EPSG:32637") == "EPSG:32637"
    try:
        surfit.require_projected("EPSG:4326")
    except ValueError:
        pass
    else:
        raise AssertionError("geographic CRS should require a projection")
    extent = {
        "min_x": 0.0, "max_x": 1.0, "min_y": 0.0, "max_y": 1.0,
        "step_x": 0.1, "step_y": 0.1, "count_x": 11, "count_y": 11,
    }
    bounds = surfit.transform_extent(
        extent, "EPSG:4326", "EPSG:32637", samples=8)
    assert bounds["min_x"] < bounds["max_x"]
    assert bounds["min_y"] < bounds["max_y"]
    print("PASS: optional CRS helpers")


if __name__ == "__main__":
    main()
