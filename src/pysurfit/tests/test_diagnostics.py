"""Residual and chi-square diagnostics against a cell-constant grid.

The pure check uses a 2x2 grid where the cell lookup and every statistic can be
computed by hand.  The session check feeds the same two points to the engine and
verifies that ``Session.residuals`` sees the solved cell value.

  python3 test_diagnostics.py
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
from surfit.diagnostics import outlier_mask, point_residuals  # noqa: E402

EXTENT = {"min_x": 0.0, "min_y": 0.0, "step_x": 1.0, "step_y": 1.0,
          "count_x": 2, "count_y": 2}


def pure_check():
    values = np.array([[1.0, 2.0], [3.0, 4.0]])
    stats = point_residuals(
        values, EXTENT,
        [0.2, 1.2, 1.2, -1.0],
        [0.2, 0.2, 1.2, 0.2],
        [1.5, 2.5, 4.5, 99.0],
        weights=[1.0, 1.0, 2.0, 1.0])
    assert stats["n"] == 3, stats
    assert np.allclose(stats["residuals"], [0.5, 0.5, 0.5])
    assert np.isclose(stats["rmse"], 0.5)
    assert np.isclose(stats["bias"], 0.5)
    assert np.isclose(stats["chi2"], 1.0)
    assert np.isclose(stats["weighted_mse"], 0.25)
    assert stats["dof"] == 2
    print("PASS: pure residual statistics")

    undefined = values.copy()
    undefined[0, 0] = surfit.UNDEF_VALUE
    stats = point_residuals(undefined, EXTENT, [0.2], [0.2], [1.0])
    assert stats["n"] == 0
    print("PASS: undefined cells are skipped")

    flags, stats = outlier_mask(
        values, EXTENT, [0.2] * 5, [0.2] * 5,
        [1.0, 1.1, 0.9, 1.0, 10.0])
    assert stats["n"] == 5
    assert flags.tolist() == [False, False, False, False, True], flags
    print("PASS: a large residual is flagged by MAD")


def session_check():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        with open(path, "w", encoding="ascii") as stream:
            stream.write("0.01 0.01 0\n0.02 0.02 10\n")
        task = surfit.Session(map_name="diag", tol=1e-9)
        assert all(task.read_points(path, "p"))
        task.grid(0, 1, 1, 0, 1, 1)
        task.points("p")
        task.solve()
        stats = task.residuals([0.01, 0.02], [0.01, 0.02], [0.0, 10.0])
    assert stats["n"] == 2, stats
    assert np.isclose(stats["rmse"], 5.0)
    assert np.isclose(stats["bias"], 0.0)
    print("PASS: Session.residuals sees the solved cell")


def main():
    pure_check()
    session_check()
    print("PASS: residual diagnostics")


if __name__ == "__main__":
    main()
