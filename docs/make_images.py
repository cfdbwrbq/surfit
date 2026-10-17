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
NODE_MODULES = os.path.join(os.path.dirname(REPO), "js-test", "node_modules")

#: (figure name, example module, renderer options)
FIGURES = (
    ("map-area", "area", {"levels": 14, "size": 700,
                          "title": "area example"}),
    ("map-faults", "faults", {"levels": 12, "size": 700,
                              "title": "fault example"}),
    ("map-trend", "trend_from_numpy", {"levels": 12, "size": 700,
                                       "title": "trend example"}),
)


def load_example(name):
    """Imports examples/python/<name>.py under a private module name."""
    path = os.path.join(EXAMPLES, "%s.py" % name)
    spec = importlib.util.spec_from_file_location("example_%s" % name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
            with open(data_path, "w", encoding="utf-8") as handle:
                json.dump(payload(task), handle)
            result = subprocess.run(
                ["node", renderer, viewer_js, data_path,
                 os.path.join(OUT, "%s.svg" % name)],
                capture_output=True, check=True,
                env=dict(os.environ, NODE_PATH=NODE_MODULES,
                         LEVELS=str(config["levels"]),
                         SIZE=str(config["size"]),
                         TITLE=config["title"]))
        print("%s: %s" % (name, result.stdout.decode()))
        surfit.clear_data()


if __name__ == "__main__":
    main()
