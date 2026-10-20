"""Builds the figures in the documentation from the examples themselves.

    PYTHONPATH=... SURFIT_BIN=... python3 docs/make_images.py

Each figure is the output of the example next to it: this imports the example
module and calls its ``build()``, so a figure cannot drift from the code the
reader is invited to run.  The SVGs are committed, so building the
documentation needs neither node nor a browser.

Regenerate after changing the viewer or an example.  node, d3 and jsdom are
needed::

    mkdir -p ../js-test && cd ../js-test && npm install d3 jsdom
"""

import importlib.util
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
EXAMPLES = os.path.join(REPO, "examples", "python")
AREA_DATA = os.path.join(REPO, "examples", "surfit", "tests", "data")
NODE_MODULES = os.path.join(os.path.dirname(REPO), "js-test", "node_modules")

#: (figure name, example module, renderer options)
FIGURES = (
    # areas
    ("map-area", "area", {"levels": 14, "size": 700,
                          "title": "area example"}),
    ("map-area-3d", "area", {"levels": 10, "size": 700,
                              "title": "area example, 3-D",
                              "renderer": "3d",
                              "contours": False,
                              "areas": ["area1", "area2", "area3",
                                        "area4", "area5"]}),
    ("map-area-completer", "area_completer", {"levels": 12, "size": 700,
                                              "title": "area_completer example"}),
    ("map-area-ineq", "area_ineq", {"levels": 12, "size": 700,
                                    "title": "area_ineq example"}),
    ("map-area-mean", "area_mean", {"levels": 12, "size": 700,
                                    "title": "area_mean example"}),
    ("map-area-wmean", "area_wmean", {"levels": 12, "size": 700,
                                      "title": "area_wmean example"}),
    ("map-area-surf", "area_surf", {"levels": 12, "size": 700,
                                    "title": "area_surf example"}),
    ("map-area-surf-ineq", "area_surf_ineq", {"levels": 12, "size": 700,
                                              "title": "area_surf_ineq example"}),
    # contours
    ("map-contour", "contour", {"levels": 12, "size": 700,
                                "title": "contour example"}),
    ("map-contour-ineq", "contour_ineq", {"levels": 12, "size": 700,
                                          "title": "contour_ineq example"}),
    # curves
    ("map-curve", "curve", {"levels": 12, "size": 700,
                            "title": "curve example"}),
    ("map-curve-ineq", "curve_ineq", {"levels": 12, "size": 700,
                                      "title": "curve_ineq example"}),
    ("map-curve-surf", "curve_surf", {"levels": 12, "size": 700,
                                      "title": "curve_surf example"}),
    ("map-curve-surf-ineq", "curve_surf_ineq", {"levels": 12, "size": 700,
                                                "title": "curve_surf_ineq example"}),
    # faults
    ("map-faults", "faults", {"levels": 12, "size": 700,
                              "title": "fault example"}),
    ("map-fault-aniso", "fault_aniso", {"levels": 12, "size": 700,
                                        "title": "fault_aniso example"}),
    ("map-fault-approx", "fault_approx", {"levels": 12, "size": 700,
                                          "title": "fault_approx example"}),
    # inequalities
    ("map-ineq", "ineq", {"levels": 12, "size": 700,
                          "title": "ineq example"}),
    ("map-points-ineq", "points_ineq", {"levels": 12, "size": 700,
                                        "title": "points_ineq example"}),
    # masks
    ("map-mask", "mask", {"levels": 12, "size": 700,
                          "title": "mask example"}),
    ("map-mask-add", "mask_add", {"levels": 12, "size": 700,
                                  "title": "mask_add example"}),
    ("map-mask-completer", "mask_completer", {"levels": 12, "size": 700,
                                              "title": "mask_completer example"}),
    ("map-mask-ineq", "mask_ineq", {"levels": 12, "size": 700,
                                    "title": "mask_ineq example"}),
    ("map-mask-mean", "mask_mean", {"levels": 12, "size": 700,
                                    "title": "mask_mean example"}),
    ("map-mask-surf", "mask_surf", {"levels": 12, "size": 700,
                                    "title": "mask_surf example"}),
    ("map-mask-surf-add", "mask_surf_add", {"levels": 12, "size": 700,
                                            "title": "mask_surf_add example"}),
    ("map-mask-surf-ineq", "mask_surf_ineq", {"levels": 12, "size": 700,
                                              "title": "mask_surf_ineq example"}),
    ("map-mask-wmean", "mask_wmean", {"levels": 12, "size": 700,
                                      "title": "mask_wmean example"}),
    # averages
    ("map-mean", "mean", {"levels": 12, "size": 700,
                          "title": "mean example"}),
    ("map-wmean", "wmean", {"levels": 12, "size": 700,
                            "title": "wmean example"}),
    # surfaces
    ("map-surface", "surface", {"levels": 12, "size": 700,
                                "title": "surface example"}),
    ("map-surface-add", "surface_add", {"levels": 12, "size": 700,
                                        "title": "surface_add example"}),
    ("map-surface-ineq", "surface_ineq", {"levels": 12, "size": 700,
                                          "title": "surface_ineq example"}),
    # trends
    ("map-trend-from-numpy", "trend_from_numpy", {"levels": 12, "size": 700,
                                                  "title": "trend example"}),
    ("map-trend", "trend", {"levels": 12, "size": 700,
                            "title": "trend example"}),
    # flows, press1: pressure from a 250-atm boundary and one well
    ("map-press-points", "press_points", {"levels": 12, "size": 700,
                                          "title": "pressure field example"}),
    ("map-flow-points", "flow_points", {"levels": 12, "size": 700,
                                        "title": "flow_points example"}),
    ("map-flow-points2", "flow_points2", {"levels": 12, "size": 700,
                                          "title": "flow_points2 example"}),
    ("map-flow-area", "flow_area", {"levels": 12, "size": 700,
                                    "title": "flow_area example"}),
    ("map-flow-curve", "flow_curve", {"levels": 12, "size": 700,
                                      "title": "flow_curve example"}),
    ("map-flow-cntr", "flow_cntr", {"levels": 12, "size": 700,
                                    "title": "flow_cntr example"}),
    # flows, press2: a real field with a fracture in two directions
    ("map-hor-frac", "map_hor_frac", {"levels": 12, "size": 700,
                                      "title": "horizontal fracture"}),
    ("map-ver-frac", "map_ver_frac", {"levels": 12, "size": 700,
                                      "title": "vertical fracture"}),
    # first steps: the smallest complete task
    ("map-first-steps", "first_steps", {"levels": 14, "size": 700,
                                        "title": "first steps"}),
    # terrain: an SRTM tile of Sao Tome, as a hard rule and as a weighted one
    ("map-dem", "dem", {"levels": 14, "size": 700,
                        "title": "dem example"}),
    ("map-dem-add", "dem_add", {"levels": 14, "size": 700,
                                "title": "dem_add example"}),
)


def load_example(name):
    """Imports examples/python/<name>.py under a private module name."""
    path = os.path.join(EXAMPLES, "%s.py" % name)
    spec = importlib.util.spec_from_file_location("example_%s" % name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AREA_Z = {"area1": 10.0, "area2": 20.0, "area3": 30.0,
          "area4": 40.0, "area5": None}


def area_polygons(names):
    """Read the simple x y polygons used by the area example."""
    polygons = []
    for name in names:
        points = []
        with open(os.path.join(AREA_DATA, "%s.txt" % name), encoding="utf-8") as handle:
            for line in handle:
                fields = line.split()
                if len(fields) >= 2:
                    points.append([float(fields[0]), float(fields[1])])
        polygons.append({"name": name, "points": points,
                         "z": AREA_Z.get(name)})
    return polygons


def payload(task):
    """The structure the page embeds, taken back out of the generated page."""
    import re

    page = task.viewer()
    found = re.search(r"window\.SURFIT_DATA = (\{.*?\});</script>", page, re.S)
    return json.loads(found.group(1))


def main():
    viewer_js = os.path.join(os.path.dirname(surfit.__file__), "viewer.js")
    renderer = os.path.join(HERE, "render_svg.js")

    if not os.path.isdir(os.path.join(NODE_MODULES, "d3")):
        raise SystemExit("d3 is not installed; see the module docstring")

    for name, example, config in FIGURES:
        built = load_example(example).build()
        task = built[0] if isinstance(built, tuple) else built

        with tempfile.TemporaryDirectory() as directory:
            data_path = os.path.join(directory, "data.json")
            data = payload(task)
            if config.get("areas"):
                data["areas"] = area_polygons(config["areas"])
            with open(data_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
            result = subprocess.run(
                ["node", renderer, viewer_js, data_path,
                 os.path.join(OUT, "%s.svg" % name)],
                capture_output=True, check=True,
                env=dict(os.environ, NODE_PATH=NODE_MODULES,
                         LEVELS=str(config["levels"]),
                         SIZE=str(config["size"]),
                         TITLE=config["title"],
                         RENDERER=config.get("renderer", ""),
                         CONTOURS="0" if config.get("contours") is False else "1"))
        print("%s: %s" % (name, result.stdout.decode()))
        surfit.clear_data()


if __name__ == "__main__":
    main()
