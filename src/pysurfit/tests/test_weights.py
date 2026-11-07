"""Per-point weights change the cell average, not just a rule weight.

Two points fall into the same grid cell.  Without weights the cell is their
arithmetic mean; with weights [1, 3] it is the weighted mean; with [0, 1] the
zero-weight point is ignored.  This is the smallest check that proves the
weights reached the engine and survived the grid binding.

  python3 test_weights.py
"""

import os
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def solve(path, weights):
    task = surfit.Session(map_name="weights", tol=1e-9)
    if weights is None:
        assert all(task.read_points(path, "p"))
    else:
        assert all(task.read_points(path, "p", weights=weights))
    task.grid(0, 1, 1, 0, 1, 1)
    task.points("p")
    task.solve()
    return task.values()


def value(values):
    defined = surfit.defined_mask(values)
    assert defined.sum() == 1, "expected one defined cell, got %d" % defined.sum()
    return float(values[defined][0])


def main():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        with open(path, "w", encoding="ascii") as stream:
            stream.write("0.01 0.01 0\n0.02 0.02 10\n")

        assert np.isclose(value(solve(path, None)), 5.0)
        assert np.isclose(value(solve(path, [1, 3])), 7.5)
        assert np.isclose(value(solve(path, [0, 1])), 10.0)
        print("PASS: unweighted, weighted and zero-weight cells")

        task = surfit.Session(map_name="bad", tol=1e-9)
        assert all(task.read_points(path, "p"))
        assert not task.pnts_set_weights("p", [1])
        try:
            task.read_points(path, "p", weights=[1])
        except ValueError:
            pass
        else:
            raise AssertionError("a short weight vector was accepted")
        print("PASS: a weight vector of the wrong length is rejected")


if __name__ == "__main__":
    main()
