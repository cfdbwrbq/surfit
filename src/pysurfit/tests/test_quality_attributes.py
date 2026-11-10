"""Per-node support and declustering.

The support arrays answer "where is this cell constrained?" without inventing
an error model.  Declustering is a preprocessing step; the original points stay
available for residuals.

  python3 test_quality_attributes.py
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
from surfit.diagnostics import cell_attributes  # noqa: E402


EXTENT = {"min_x": 0.0, "min_y": 0.0, "step_x": 1.0, "step_y": 1.0,
          "count_x": 2, "count_y": 2}


def support_check():
    values = np.ones((2, 2))
    attributes = cell_attributes(
        values, EXTENT, [0.2, 0.2, 1.2], [0.2, 0.2, 0.2],
        weights=[1.0, 2.0, 0.0])
    assert attributes["count"].tolist() == [[2, 1], [0, 0]]
    assert np.isclose(attributes["sum_weights"][0, 0], 3.0)
    assert np.isclose(attributes["sum_weights"][0, 1], 0.0)
    assert np.isclose(attributes["min_distance"][0, 0],
                      np.hypot(0.2, 0.2))
    assert np.isnan(attributes["min_distance"][1, 1])
    assert np.isclose(attributes["mean_distance"][0, 0],
                      np.mean([np.hypot(0.2, 0.2), np.hypot(0.2, 0.2)]))
    print("PASS: per-cell support, weights and distances")


def report_and_session_check():
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        with open(path, "w", encoding="ascii") as stream:
            stream.write("0.01 0.01 0\n0.02 0.02 10\n")
        task = surfit.Session(map_name="support", tol=1e-9)
        assert all(task.read_points(path, "p"))
        task.grid(0, 1, 1, 0, 1, 1)
        task.points("p")
        task.solve()
        attributes = task.quality_attributes([0.01], [0.01])
        report = task.report([0.01, 0.02], [0.01, 0.02], [0.0, 10.0])
    assert attributes["count"].shape == task.values().shape
    assert attributes["count"].sum() == 1
    assert report["grid"]["covered"] == 1
    assert report["grid"]["uncovered"] == 63
    print("PASS: Session support arrays and report coverage")


def decluster_check():
    x = np.array([0.1, 0.4, 1.1, 1.4])
    y = np.array([0.1, 0.2, 0.1, 0.2])
    z = np.array([1.0, 2.0, 3.0, 4.0])
    result = surfit.decluster_points(x, y, z, block=1.0, method="mean")
    assert result["count"].tolist() == [2, 2]
    assert np.allclose(result["z"], [1.5, 3.5])
    assert np.allclose(result["weights"], [2.0, 2.0])
    nearest = surfit.decluster_points(x, y, z, block=1.0, method="nearest")
    assert np.allclose(nearest["z"], [1.0, 3.0])
    low = surfit.decluster_points(x, y, z, block=1.0, method="min")
    high = surfit.decluster_points(x, y, z, block=1.0, method="max")
    assert np.allclose(low["z"], [1.0, 3.0])
    assert np.allclose(high["z"], [2.0, 4.0])
    idw = surfit.decluster_points(x, y, z, block=1.0, method="idw")
    assert idw["z"].shape == (2,)
    assert np.allclose(idw["weights"], [2.0, 2.0])
    print("PASS: decluster mean/nearest/min/max/IDW")


def main():
    support_check()
    report_and_session_check()
    decluster_check()
    print("PASS: per-node support and declustering")


if __name__ == "__main__":
    main()
