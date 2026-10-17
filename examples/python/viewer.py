"""Solves the area example and writes an interactive HTML map.

    python3 examples/python/viewer.py [output.html]

The page embeds the grid, so it can be moved around freely; it loads d3 from a
CDN when opened, which is the only thing it needs from outside.  Pass
``d3_url=...`` to point at a local copy on a machine without network access.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area5")


def main(output="area.html"):
    task = surfit.Session(map_name="map_area", tol=5.01187e-006)

    for name in AREAS:
        task.read_areas(os.path.join(DATA, "%s.txt" % name), name)

    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(10, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")

    task.solve()

    task.save_viewer(output, title="surfit area example", levels=14)
    print("wrote %s (%d bytes)" % (output, os.path.getsize(output)))


if __name__ == "__main__":
    main(*sys.argv[1:])
