"""2D polygonal declustering weights.

A 3x3 grid on a 2x2 square has known Voronoi cell areas: corners 0.25,
edges 0.5, centre 1.0.  The weights are inverse areas, mean 1.  The test also
checks duplicate splitting, collinearity and the bounds rule.

  python3 test_voronoi_weights.py
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
    try:
        import scipy  # noqa: F401
    except ImportError:
        print("SKIP: scipy is not installed")
        return

    grid = np.array([0.0, 1.0, 2.0])
    x, y = np.meshgrid(grid, grid)
    weights = surfit.voronoi_weights(
        x.ravel(), y.ravel(), bounds=(0.0, 2.0, 0.0, 2.0))
    assert weights.size == 9
    assert np.isclose(weights.mean(), 1.0)
    centre = weights[4]
    corner = weights[0]
    edge = weights[1]
    assert np.isclose(centre, corner / 4.0)
    assert np.isclose(edge, corner / 2.0)

    duplicate_x = np.array([0.0, 0.0, 2.0, 2.0, 1.0, 1.0])
    duplicate_y = np.array([0.0, 0.0, 2.0, 2.0, 0.0, 2.0])
    duplicate = surfit.voronoi_weights(
        duplicate_x, duplicate_y, bounds=(0.0, 2.0, 0.0, 2.0))
    assert np.isclose(duplicate[0], duplicate[1])
    assert np.isclose(duplicate.mean(), 1.0)

    for bad_x, bad_y in (([0, 1], [0, 1]),
                         ([0, 1, 2], [0, 1, 2]),
                         ([0, 1, 2], [0, 1, 3])):
        try:
            surfit.voronoi_weights(bad_x, bad_y, bounds=(0.0, 2.0, 0.0, 2.0))
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input did not raise")
    print("PASS: 2D Voronoi declustering weights")


if __name__ == "__main__":
    main()
