"""Ensemble arithmetic and declarative recipe/CLI."""

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


def test_ensemble():
    extent = {"step_x": 1.0, "step_y": 2.0}
    first = surfit.SurfaceEnsemble(
        [{"top": np.ones((2, 2))}, {"top": np.ones((2, 2)) * 3.0}],
        extent=extent)
    second = surfit.SurfaceEnsemble(
        [{"top": np.zeros((2, 2))}, {"top": np.ones((2, 2))}],
        extent=extent)
    difference = first - second
    assert np.allclose(difference["top"][1], 2.0)
    assert np.allclose(difference.percentiles()["p50"]["top"], 1.5)
    assert np.allclose(difference.volume_between(0.0, extent)["top"],
                       [8.0, 16.0])


def test_recipe():
    with tempfile.TemporaryDirectory() as directory:
        points = os.path.join(directory, "points.txt")
        with open(points, "w", encoding="ascii") as stream:
            stream.write("0 0 1\n1 0 2\n0 1 3\n1 1 4\n")
        output = os.path.join(directory, "out.dat")
        recipe = {
            "name": "recipe",
            "grid": [0, 1, 0.5, 0, 1, 0.5],
            "data": [{"kind": "points", "path": "points.txt", "name": "p"}],
            "rules": [{"command": "points", "args": ["p"]},
                      {"command": "completer", "args": [1, 1.6]}],
            "output": {"save": output},
        }
        path = os.path.join(directory, "task.json")
        with open(path, "w", encoding="utf-8") as stream:
            json.dump(recipe, stream)
        task = surfit.run_recipe(path)
        task.close()
        assert os.path.exists(output)
        summary = surfit.recipe_summary(path)
        assert summary["data"] == ["points"]
        assert summary["rules"] == ["points", "completer"]
        from surfit.cli import main as cli_main

        assert cli_main(["run", path, "--summary"]) == 0
        result_path = os.path.join(directory, "result.json")
        assert cli_main(["run", path, "--result-json", result_path]) == 0
        with open(result_path, encoding="utf-8") as stream:
            result = json.load(stream)
        assert result["ok"] is True
        assert len(result["shape"]) == 2
        assert result["defined"] > 0
        assert result["defined"] + result["undefined"] == (
            result["shape"][0] * result["shape"][1])
        assert result["min"] <= result["mean"] <= result["max"]


def main():
    test_ensemble()
    test_recipe()
    print("PASS: coherent ensembles, recipes and recipe summary")


if __name__ == "__main__":
    main()
