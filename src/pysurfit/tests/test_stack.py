"""Ordered surfaces agree on a grid and report crossings/thickness.

  python3 test_stack.py
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
    task = surfit.Session(map_name="layer", tol=1e-7)
    assert all(task.add_points([0, 1, 0, 1], [0, 0, 1, 1],
                               [value] * 4, name="p"))
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    stack = surfit.SurfaceStack("site")
    stack.add_layer("top", lambda: layer(10.0))
    stack.add_layer("middle", lambda: layer(5.0))
    stack.add_layer("bottom", lambda: layer(4.0))
    stack.solve()
    report = stack.report()
    assert stack.layer_names() == ["top", "middle", "bottom"]
    assert report["crossings"] == 0
    assert len(report["layers"]) == 3
    assert stack.values("top").shape == stack.values("bottom").shape
    assert all(item["defined"] == item["total"] for item in report["layers"])
    assert all(item["thickness"]["min"] >= 0
               for item in report["layers"][:-1])
    stack.close()

    crossed = surfit.SurfaceStack("crossed")
    crossed.add_layer("top", lambda: layer(5.0))
    crossed.add_layer("bottom", lambda: layer(10.0))
    crossed.solve()
    assert crossed.report()["crossings"] > 0
    crossed.close()

    duplicate = surfit.SurfaceStack("duplicate")
    duplicate.add_layer("a", lambda: layer(1.0))
    try:
        duplicate.add_layer("a", lambda: layer(2.0))
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate layer did not raise")
    print("PASS: ordered surface stack and report")


if __name__ == "__main__":
    main()
