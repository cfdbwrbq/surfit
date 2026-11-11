"""2D polygonal declustering weights, both backends.

A 3x3 grid on a 2x2 square has known Voronoi cell areas: corners 0.25,
edges 0.5, centre 1.0.  The pure clipping backend always runs; the SciPy
backend runs when SciPy is installed and must agree.  Duplicate splitting,
collinearity and the bounds rule are checked too.

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


def check_backend(backend):
    grid = np.array([0.0, 1.0, 2.0])
    x, y = np.meshgrid(grid, grid)
    weights = surfit.voronoi_weights(
        x.ravel(), y.ravel(), bounds=(0.0, 2.0, 0.0, 2.0),
        backend=backend)
    assert weights.size == 9
    assert np.isclose(weights.mean(), 1.0)
    assert np.isclose(weights[4], weights[0] / 4.0)
    assert np.isclose(weights[1], weights[0] / 2.0)

    duplicate_x = np.array([0.0, 0.0, 2.0, 2.0, 1.0, 1.0])
    duplicate_y = np.array([0.0, 0.0, 2.0, 2.0, 0.0, 2.0])
    duplicate = surfit.voronoi_weights(
        duplicate_x, duplicate_y, bounds=(0.0, 2.0, 0.0, 2.0),
        backend=backend)
    assert np.isclose(duplicate[0], duplicate[1])
    assert np.isclose(duplicate.mean(), 1.0)
    return weights


def invalid_inputs():
    cases = (([0, 1], [0, 1]),
             ([0, 1, 2], [0, 1, 2]),
             ([0, 1, 2], [0, 1, 3]))
    for bad_x, bad_y in cases:
        try:
            surfit.voronoi_weights(
                bad_x, bad_y, bounds=(0.0, 2.0, 0.0, 2.0),
                backend="clip")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid input did not raise")


def main():
    clip = check_backend("clip")
    try:
        import scipy  # noqa: F401
    except ImportError:
        print("scipy is not installed; only the clip backend is tested")
        auto = check_backend("auto")
        assert np.allclose(auto, clip)
        try:
            surfit.voronoi_weights(
                [0, 1, 2], [0, 1, 3], bounds=(0.0, 2.0, 0.0, 2.0),
                backend="scipy")
        except ImportError:
            pass
        else:
            raise AssertionError("backend='scipy' did not report missing scipy")
    else:
        scipy_weights = check_backend("scipy")
        auto = check_backend("auto")
        assert np.allclose(scipy_weights, clip, rtol=1e-10, atol=1e-12)
        assert np.allclose(auto, clip, rtol=1e-10, atol=1e-12)
        saved = sys.modules.get("scipy")
        sys.modules["scipy"] = None
        try:
            fallback = surfit.voronoi_weights(
                [0.0, 1.0, 2.0], [0.0, 1.0, 0.0],
                bounds=(0.0, 2.0, 0.0, 2.0), backend="auto")
        finally:
            if saved is None:
                del sys.modules["scipy"]
            else:
                sys.modules["scipy"] = saved
        assert fallback.size == 3
        print("PASS: scipy and clip backends agree")
    invalid_inputs()
    print("PASS: 2D Voronoi declustering weights")


if __name__ == "__main__":
    main()
