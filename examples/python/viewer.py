"""Solves the area example and writes an interactive HTML map.

    python3 examples/python/viewer.py [output.html]

The page embeds the grid, so it can be moved around freely; it loads d3 from a
CDN when opened, which is the only thing it needs from outside. Pass
``d3_url=...`` to point at a local copy on a machine without network access.

The solve itself is the area example next door: only the output differs.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))
sys.path.insert(0, HERE)

import area  # noqa: E402


def main(output="area.html"):
    task = area.build()

    task.save_viewer(output, title="area example", levels=14)
    print("wrote %s (%d bytes)" % (output, os.path.getsize(output)))


if __name__ == "__main__":
    main(*sys.argv[1:])
