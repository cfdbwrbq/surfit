"""Tests for the HTML viewer: the data path, and the JS when node is present.

Rendering proper needs a browser, but three things can be checked here:

* the payload embedded in the page decodes back to the very same grid;
* viewer.computeLayers() produces sane geometry (node, d3);
* viewer.render() draws a complete map into a real DOM (node, jsdom) - one
  filled band per level, a clip region, and axes with tick labels.

The last one is what catches a map that would come out empty or unlabelled.

The two node checks are skipped unless d3 and jsdom are installed next to the
checkout::

    mkdir -p ../js-test && cd ../js-test && npm install d3 jsdom
"""

import base64
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
NODE_MODULES = os.path.join(os.path.dirname(REPO), "js-test", "node_modules")
sys.path.insert(0, os.environ.get("SURFIT_BIN",
                                  os.path.join(os.path.dirname(REPO), "build-cpp", "bin")))

import surfit  # noqa: E402

UNDEF = float(np.finfo(np.float32).max)


def js_environment():
    """The node module directory, or None when the check cannot run."""
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    needed = ("d3", "jsdom")
    if not all(os.path.isdir(os.path.join(NODE_MODULES, name)) for name in needed):
        return None
    return NODE_MODULES


def run_node(script, modules, *args, stdin=None):
    result = subprocess.run(
        ["node", os.path.join(HERE, script)] + list(args),
        input=stdin, capture_output=True,
        env=dict(os.environ, NODE_PATH=modules))
    if result.returncode != 0:
        raise AssertionError("%s failed: %s"
                             % (script, result.stderr.decode()[:800]))
    return json.loads(result.stdout.decode())


def viewer_js():
    """The file that actually ships, not a copy of it."""
    return os.path.join(os.path.dirname(os.path.abspath(surfit.__file__)),
                        "viewer.js")


def sample():
    """A small grid with one undefined node, and the geometry to place it."""
    values = np.arange(12, dtype=float).reshape(3, 4)
    values[1, 1] = UNDEF
    extent = {
        "count_x": 4, "count_y": 3,
        "min_x": -1.5, "max_x": 1.5, "min_y": 10.0, "max_y": 12.0,
        "step_x": 1.0, "step_y": 1.0,
    }
    return values, extent


def payload_of(page):
    match = re.search(r"window\.SURFIT_DATA = (\{.*?\});</script>", page, re.S)
    assert match is not None, "no data in the page"
    return json.loads(match.group(1))


def as_payload(values, extent):
    return {
        "values": base64.b64encode(
            np.ascontiguousarray(values, dtype="<f8").tobytes()).decode(),
        "count_x": extent["count_x"], "count_y": extent["count_y"],
        "min_x": extent["min_x"], "max_x": extent["max_x"],
        "min_y": extent["min_y"], "max_y": extent["max_y"],
        "step_x": extent["step_x"], "step_y": extent["step_y"],
        "undef": UNDEF,
    }


def test_payload_round_trip(values, extent):
    page = surfit.render_html(values, extent, title="round trip")
    data = payload_of(page)

    restored = np.frombuffer(base64.b64decode(data["values"]), dtype="<f8")
    restored = restored.reshape(data["count_y"], data["count_x"])

    assert restored.shape == values.shape, (restored.shape, values.shape)
    assert np.array_equal(restored, values), "the grid did not survive"
    assert data["min_x"] == -1.5 and data["max_x"] == 1.5
    assert data["step_x"] == 1.0 and data["step_y"] == 1.0
    assert "surfit-view" in page and "SurfitViewer.render" in page
    assert "d3" in page, "the page does not load d3"


def test_shape_mismatch_is_reported(values, extent):
    broken = dict(extent, count_x=extent["count_x"] + 1)
    try:
        surfit.render_html(values, broken)
    except ValueError as error:
        assert "x" in str(error), str(error)
        return
    raise AssertionError("a mismatched extent was accepted")


def test_layers(values, extent):
    modules = js_environment()
    if modules is None:
        return "SKIP"

    report = run_node("viewer_check.js", modules, viewer_js(),
                      stdin=json.dumps(as_payload(values, extent)).encode())

    assert report["layers"] == report["levels"], report
    assert report["defined"] == values.size - 1, report
    assert report["region"] is True, report
    assert report["within_bounds"] is True, report
    assert report["ascending"] is True, report
    assert report["empty_rings"] == 0, report
    return "PASS"


def test_render(values, extent):
    modules = js_environment()
    if modules is None:
        return "SKIP"

    with tempfile.TemporaryDirectory() as directory:
        data_path = os.path.join(directory, "data.json")
        svg_path = os.path.join(directory, "map.svg")
        with open(data_path, "w", encoding="utf-8") as handle:
            json.dump(as_payload(values, extent), handle)
        report = run_node("render_check.js", modules, viewer_js(),
                          data_path, svg_path)
        with open(svg_path, encoding="utf-8") as handle:
            svg = handle.read()

    assert report["has_svg"] is True, report
    assert report["bands"] == report["levels"], report
    assert report["bands_with_fill"] == report["levels"], report
    assert report["bands_with_path"] == report["levels"], report
    assert report["region_clip"] == 1, report
    assert report["axis_ticks"] > 0, "the axes have no labels"
    # A reversed paint order hides the whole map under the lowest band while
    # every other check still passes, so it is checked on its own.
    assert report["draw_order_ascending"] is True, report
    assert report["distinct_fills"] == report["levels"], report
    assert report["has_base_fill"] == 1, report
    assert svg.startswith("<svg"), svg[:40]
    return "PASS"


def main():
    values, extent = sample()
    test_payload_round_trip(values, extent)
    test_shape_mismatch_is_reported(values, extent)
    print("payload round trip: PASS")
    print("shape mismatch:     PASS")
    print("contour layers:     %s" % test_layers(values, extent))
    print("dom render:         %s" % test_render(values, extent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
