"""Builds the figures in the documentation from real solves.

    PYTHONPATH=... SURFIT_BIN=... python3 docs/make_images.py

The SVGs are committed, so building the documentation does not need node; run
this when the viewer or an example changes.  node, d3 and jsdom are needed:

    mkdir -p ../js-test && cd ../js-test && npm install d3 jsdom
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT = os.path.join(HERE, "_static")
DATA = os.path.join(REPO, "examples", "surfit", "tests", "data")
NODE_MODULES = os.path.join(os.path.dirname(REPO), "js-test", "node_modules")


def figures():
    """The solves behind the two figures, as (name, build, config) triples."""
    return (
        ("map-area", build_area, {"levels": 14, "size": 700,
                                  "title": "area example"}),
        ("map-faults", build_faults, {"levels": 12, "size": 700,
                                      "title": "fault example"}),
    )


def build_area():
    """Five areas with fixed values, completed by completer()."""
    task = surfit.Session(map_name="map_area", tol=5.01187e-006)
    for name in ("area1", "area2", "area3", "area4", "area5"):
        task.read_areas(os.path.join(DATA, "%s.txt" % name), name)
    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")
    task.solve()
    return task


def build_faults():
    """Points across four fault lines: the surface must break along them."""
    task = surfit.Session(map_name="map_faults", tol=1e-005)
    task.set_solver("cg")
    task.pnts_read(os.path.join(DATA, "11points.txt"), "11points")
    for name in ("flt_line1", "flt_line2", "flt_line3", "flt_line4"):
        task.curv_read(os.path.join(DATA, "%s.txt" % name), name)
    task.grid(1, 99, 0.5, -50, 50, 0.5)
    task.points("11points")
    for name in ("flt_line1", "flt_line2", "flt_line3", "flt_line4"):
        task.fault(name)
    task.completer(0.5, 2)
    task.solve()
    return task


def payload(task):
    """The same structure the page embeds, taken from the generated page."""
    import base64
    import re

    page = task.viewer()
    found = re.search(r"window\.SURFIT_DATA = (\{.*?\});</script>", page, re.S)
    return json.loads(found.group(1))


def main():
    viewer_js = os.path.join(os.path.dirname(surfit.__file__), "viewer.js")
    renderer = os.path.join(HERE, "render_svg.js")

    if not os.path.isdir(os.path.join(NODE_MODULES, "d3")):
        raise SystemExit("d3 is not installed; see the module docstring")

    for name, build, config in figures():
        task = build()
        data = payload(task)
        target = os.path.join(OUT, "%s.svg" % name)

        with tempfile.TemporaryDirectory() as directory:
            data_path = os.path.join(directory, "data.json")
            with open(data_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
            result = subprocess.run(
                ["node", renderer, viewer_js, data_path, target],
                capture_output=True, check=True,
                env=dict(os.environ, NODE_PATH=NODE_MODULES,
                         LEVELS=str(config["levels"]),
                         SIZE=str(config["size"]),
                         TITLE=config["title"]))
        print("%s: %s" % (name, result.stdout.decode()))
        surfit.clear_data()


if __name__ == "__main__":
    main()
