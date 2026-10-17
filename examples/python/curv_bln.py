"""The curve BLN round trip -- examples/surfit_io/bln/curv_bln.tcl.

    python3 examples/python/curv_bln.py

Four isolines are saved as BLN and only three are loaded back, by pattern.  The
pattern is the point of the example: ``curv_load_bln`` takes a name pattern and
a file pattern, just like the other loaders.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit_io", "bln")
CURVES = ("iso1", "iso2", "iso3", "iso4")


def build():
    """Runs the round trip and returns the session with the loaded curves."""
    task = surfit.Session("map")

    for name in CURVES:
        assert all(task.read_curves(os.path.join(DATA, "%s.xy" % name), name)), name

    assert all(task.curv_save_bln("curvs.bln", "iso*"))
    task.clear_data()

    assert all(task.curv_load_bln("curvs.bln", "iso[1-3]"))
    return task


def main():
    task = build()
    print("wrote curvs.bln and loaded %d curve(s): %s"
          % (task.curv_size(), ", ".join(task.curv_getName("iso*"))))


if __name__ == "__main__":
    main()
