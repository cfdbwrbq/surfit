"""Ordered surfaces agree on a grid and report crossings/thickness.

  python3 test_stack.py
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


def layer(value, relation=None):
    task = surfit.Session(map_name="layer", tol=1e-7)
    if relation is not None:
        relation.apply(task)
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
    assert all(item["coverage"] == 1.0 for item in report["layers"])
    validation = stack.validate(min_thickness=0.9, min_coverage=1.0)
    assert validation["ok"]
    assert validation["violations"] == []
    stack.validate(min_thickness=0.9, strict=True)
    weak = stack.validate(min_thickness=10.0)
    assert not weak["ok"]
    assert weak["violations"][0]["code"] == "thickness"
    stack.close()

    with surfit.SurfaceStack("thresholds") as thresholds:
        thresholds.add_layer("top", lambda: layer(10.0))
        thresholds.add_layer("bottom", lambda: layer(4.0))
        thresholds.solve()
        for bad in (-1, 1.5):
            try:
                thresholds.validate(max_crossings=bad)
            except ValueError:
                pass
            else:
                raise AssertionError("bad max_crossings did not raise")
        for bad in (-0.1, 1.1):
            try:
                thresholds.validate(min_coverage=bad)
            except ValueError:
                pass
            else:
                raise AssertionError("bad min_coverage did not raise")

    crossed = surfit.SurfaceStack("crossed")
    crossed.add_layer("top", lambda: layer(5.0))
    crossed.add_layer("bottom", lambda: layer(10.0))
    crossed.solve()
    assert crossed.report()["crossings"] > 0
    invalid = crossed.validate()
    assert not invalid["ok"]
    assert invalid["violations"][0]["code"] == "crossings"
    try:
        crossed.validate(strict=True)
    except surfit.StackValidationError as error:
        assert error.validation["violations"][0]["code"] == "crossings"
    else:
        raise AssertionError("strict validation did not raise")
    crossed.close()

    parallel = surfit.SurfaceStack("parallel")
    parallel.add_layer("top", lambda: layer(10.0))
    parallel.add_layer("bottom", lambda: layer(4.0))
    parallel.solve(parallel=True, workers=2)
    assert parallel.report()["crossings"] == 0
    thickness = parallel.thickness("top")
    assert np.allclose(thickness[np.isfinite(thickness)], 6.0)
    assert parallel.pinchout_mask("top").sum() == 0
    parallel.close()

    chain = surfit.SurfaceStack("chain")
    chain.add_layer("top", lambda relations: layer(7.0, relations),
                    above="middle", min_thickness=1.0)
    chain.add_layer("middle", lambda relations: layer(4.0, relations),
                    above="bottom", min_thickness=1.0)
    chain.add_layer("bottom", lambda: layer(1.0))
    chain.solve()
    assert chain.report()["crossings"] == 0
    assert np.min(chain.thickness("top")) >= 0.9
    assert np.min(chain.thickness("middle")) >= 0.9
    chain.close()

    skip = surfit.SurfaceStack("skip")
    skip.add_layer("top", lambda relations: layer(7.0, relations),
                   above="bottom", min_thickness=1.0)
    skip.add_layer("middle", lambda: layer(4.0))
    skip.add_layer("bottom", lambda: layer(1.0))
    skip.solve()
    assert skip.report()["crossings"] == 0
    skip.close()

    cyclic = surfit.SurfaceStack("cyclic")
    cyclic.add_layer("a", lambda relations: layer(1.0, relations))
    cyclic.add_layer("b", lambda relations: layer(2.0, relations))
    cyclic.add_relation("a", "b")
    cyclic.add_relation("b", "a")
    try:
        cyclic.solve()
    except ValueError as error:
        assert "cycle" in str(error)
    else:
        raise AssertionError("cycle did not raise")

    constrained = surfit.SurfaceStack("constrained")
    constrained.add_layer("top", lambda relation: layer(5.0, relation),
                          above="bottom", min_thickness=1.0)
    constrained.add_layer("bottom", lambda: layer(10.0))
    constrained.solve()
    top = constrained.values("top")
    bottom = constrained.values("bottom")
    assert constrained.report()["crossings"] == 0
    both = surfit.defined_mask(top) & surfit.defined_mask(bottom)
    assert np.min(top[both] - bottom[both]) >= 0.9
    constrained.close()

    with tempfile.TemporaryDirectory() as directory:
        initial = surfit.SurfaceStack("persisted")
        initial.add_layer("top", lambda: layer(10.0))
        initial.add_layer("bottom", lambda: layer(4.0))
        initial.solve()
        before = initial.report()
        initial.save(directory)
        loaded = surfit.SurfaceStack.load(directory)
        assert loaded.layer_names() == ["top", "bottom"]
        assert np.allclose(loaded.values("top"), initial.values("top"))
        assert loaded.report()["crossings"] == before["crossings"]
        assert loaded.report()["layers"][0]["thickness"]["pinchouts"] == 0
        loaded.close()
        initial.close()

    with tempfile.TemporaryDirectory() as directory:
        mapped = surfit.SurfaceStack("mapped")
        mapped.add_layer("top", lambda: layer(10.0))
        mapped.add_layer("bottom", lambda: layer(4.0))
        mapped.solve(memmap=True,
                     memmap_dir=os.path.join(directory, "values"))
        assert isinstance(mapped.values("top"), np.memmap)
        assert mapped.report()["crossings"] == 0
        mapped.save(os.path.join(directory, "saved"))
        loaded = surfit.SurfaceStack.load(
            os.path.join(directory, "saved"), mmap=True)
        assert isinstance(loaded.values("bottom"), np.memmap)
        assert np.allclose(loaded.values("top"), mapped.values("top"))
        loaded.close()
        mapped.close()

    pinched = surfit.SurfaceStack("pinched")
    pinched.add_layer("top", lambda: layer(10.0))
    pinched.add_layer("bottom", lambda: layer(10.0))
    pinched.solve()
    assert pinched.pinchout_mask("top").sum() > 0
    assert pinched.apply_pinchout("top", mode="merge") > 0
    assert np.allclose(pinched.values("top"), pinched.values("bottom"))
    assert pinched.report()["crossings"] == 0
    assert pinched.report()["seconds"] >= 0.0
    pinched.close()

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
