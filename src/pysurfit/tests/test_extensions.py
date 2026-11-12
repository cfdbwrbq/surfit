"""Volumetrics, sections, regression residuals and optional integrations.

  python3 test_extensions.py
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


def layer(value):
    task = surfit.Session(map_name="ext", tol=1e-7)
    assert all(task.add_points([0, 1, 0, 1], [0, 0, 1, 1],
                               [value] * 4, name="p"))
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    extent = {"min_x": 0.0, "max_x": 1.0, "min_y": 0.0, "max_y": 1.0,
              "step_x": 1.0, "step_y": 1.0, "count_x": 2, "count_y": 2}
    item = surfit.volume_between(np.full((2, 2), 10.0),
                                 np.full((2, 2), 4.0), extent)
    assert item["volume"] == 24.0
    assert item["cells"] == 4
    percentiles = surfit.volume_percentiles([1.0, 2.0, 3.0])
    assert percentiles["p50"] == 2.0
    ensemble = surfit.volume_ensemble(
        [np.full((2, 2), 10.0), np.full((2, 2), 12.0)],
        [np.full((2, 2), 4.0), np.full((2, 2), 4.0)], extent)
    assert ensemble["n"] == 2
    assert ensemble["p50"] > 0

    with surfit.SurfaceStack("section") as stack:
        stack.add_layer("top", lambda: layer(10.0))
        stack.add_layer("bottom", lambda: layer(4.0))
        stack.solve()
        assert stack.extent()["count_x"] >= 3
        volume = surfit.stack_volume(stack, "top", "bottom")
        assert volume["volume"] > 0
        stack.set_layer_uncertainty("top", residuals=[1.0, 2.0], level=0.8)
        section = stack.section([0.0, 1.0], [0.0, 0.0], samples=5)
        assert section["samples"] == 5
        assert set(section["layers"]) == {"top", "bottom"}
        assert "top" in section["intervals"]
        assert section["layers"]["top"].shape == (5,)

    task = surfit.Session(map_name="rules", tol=1e-7)
    task.add_points([0, 1, 0, 1], [0, 0, 1, 1], [1, 2, 3, 4], name="p")
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    rules = task.rule_report()
    assert rules["count"] == 2
    assert rules["rules"][0]["name"].startswith("f_points")
    task.close()

    conflict = surfit.Session(map_name="conflict", tol=1e-6)
    conflict.add_points([0, 1, 0, 1], [0, 0, 1, 1], [0.0] * 4,
                        name="p")
    conflict.grid(0, 1, 0.5, 0, 1, 0.5)
    conflict.points("p")
    conflict.geq(10)
    conflict.completer(1, 1.6)
    conflict.solve()
    violation_rules = conflict.rule_report()["rules"]
    inequality = [item for item in violation_rules
                  if item["name"] == "f_ineq"]
    assert inequality and inequality[0]["violations"] > 0
    assert inequality[0]["residual"] is not None
    assert inequality[0]["residual"] > 0
    conflict.close()

    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([0.0, 1.0, 0.0, 1.0])
    features = np.column_stack((x, y))
    values = 1.0 + 2.0 * x + 3.0 * y
    regression = surfit.regression_trend(features, values)
    assert regression["n"] == 4
    assert regression["rmse"] < 1e-9
    assert np.allclose(regression["residuals"], 0.0)

    try:
        import geopandas  # noqa: F401
    except ImportError:
        print("SKIP: geopandas")
    try:
        import xarray  # noqa: F401
    except ImportError:
        print("SKIP: xarray")
    print("PASS: volumetrics, sections, rule report and regression")


if __name__ == "__main__":
    main()
