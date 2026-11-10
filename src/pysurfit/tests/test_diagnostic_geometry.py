"""Typed point diagnostics and their GeoJSON/CSV form.

A point is classified as used, outlier, undefined cell, outside the grid or
zero weight.  The code makes a QC layer actionable without inventing a map of
uncertainty.

  python3 test_diagnostic_geometry.py
"""

import json
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
from surfit.diagnostics import diagnostic_points, diagnostics_to_geojson  # noqa: E402


EXTENT = {"min_x": 0.0, "min_y": 0.0, "step_x": 1.0, "step_y": 1.0,
          "count_x": 2, "count_y": 2}


def pure_check():
    values = np.array([[1.0, 2.0], [3.0, surfit.UNDEF_VALUE]])
    x = [0.2, 0.2, 0.2, 0.2, 0.2, 1.2, -1.0, 0.2]
    y = [0.2, 0.2, 0.2, 0.2, 0.2, 1.2, 0.2, 0.2]
    z = [0.0, 1.0, 2.0, 10.0, 1.0, 3.0, 1.0, 1.0]
    weights = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0]
    document = diagnostic_points(values, EXTENT, x, y, z, weights)
    assert document["code"].tolist() == [0, 0, 0, 1, 0, 2, 3, 4]
    assert document["code_name"][3] == "outlier"
    assert document["code_name"][5] == "undefined_cell"
    assert document["code_name"][6] == "outside_grid"
    assert np.isnan(document["residual"][6])
    assert np.isnan(document["residual"][7])
    assert document["scale"][0] > 0.0
    feature = diagnostics_to_geojson(document)
    assert feature["type"] == "FeatureCollection"
    assert len(feature["features"]) == 8
    assert feature["features"][6]["properties"]["residual"] is None
    print("PASS: typed point codes and GeoJSON")


def session_check():
    with tempfile.TemporaryDirectory() as directory:
        points = os.path.join(directory, "points.txt")
        with open(points, "w", encoding="ascii") as stream:
            stream.write("0.01 0.01 0\n0.02 0.02 10\n")
        task = surfit.Session(map_name="diaggeo", tol=1e-9)
        assert all(task.read_points(points, "p"))
        task.grid(0, 1, 1, 0, 1, 1)
        task.points("p")
        task.solve()
        geojson = os.path.join(directory, "diagnostics.geojson")
        table = os.path.join(directory, "diagnostics.csv")
        task.save_diagnostics(geojson, [0.01], [0.01], [0.0])
        task.save_diagnostics(table, [0.01], [0.01], [0.0])
        with open(geojson, encoding="utf-8") as stream:
            saved = json.load(stream)
        with open(table, encoding="utf-8") as stream:
            rows = stream.read().splitlines()
    assert saved["features"][0]["properties"]["code"] == 0
    assert rows[0].startswith("x,y,z,residual")
    print("PASS: Session writes GeoJSON and CSV diagnostics")


def main():
    pure_check()
    session_check()
    print("PASS: typed diagnostic geometry")


if __name__ == "__main__":
    main()
