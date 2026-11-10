"""Tiled solves for curves, contours and areas via the generic driver.

The callback selects the full geometry for each tile and lets the engine clip
it to the tile grid; only the inner part is copied.  The check compares the
interior of the mosaic with a full solve, so a tile edge cannot hide a bad
clip.

  python3 test_tiled_geometry.py
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
from surfit.tiled import solve_tiled, tile_boxes  # noqa: E402

STEP = 2.0
EXTENT = (-10.0, 10.0, -10.0, 10.0)


def write_curve(path):
    with open(path, "w", encoding="ascii") as stream:
        for x in np.linspace(-10.0, 10.0, 21):
            stream.write("%.17g\t0\n" % x)


def write_contour(path):
    with open(path, "w", encoding="ascii") as stream:
        for x in np.linspace(-10.0, 10.0, 21):
            stream.write("%.17g\t2\t5\n" % x)


def write_area(path):
    with open(path, "w", encoding="ascii") as stream:
        for x, y in ((-4, -4), (4, -4), (4, 4), (-4, 4), (-4, -4)):
            stream.write("%d\t%d\n" % (x, y))


def full_task(directory, kind):
    task = surfit.Session(map_name="full", tol=1e-7)
    if kind == "curve":
        assert all(task.read_curves(os.path.join(directory, "curve.txt"), "g"))
        task.curve(5, "g")
    elif kind == "contour":
        assert all(task.read_contours(
            os.path.join(directory, "contour.txt"), "g"))
        task.contour("g")
    else:
        assert all(task.read_areas(os.path.join(directory, "area.txt"), "g"))
        task.area(-2, "g")
    task.grid(EXTENT[0], EXTENT[1], STEP, EXTENT[2], EXTENT[3], STEP)
    task.completer(1, 1.6)
    task.solve()
    return task.values()


def main():
    with tempfile.TemporaryDirectory() as directory:
        write_curve(os.path.join(directory, "curve.txt"))
        write_contour(os.path.join(directory, "contour.txt"))
        write_area(os.path.join(directory, "area.txt"))
        for kind in ("curve", "contour", "area"):
            def build_tile(tile, kind=kind):
                task = surfit.Session(map_name="tile", tol=1e-7)
                if kind == "curve":
                    assert all(task.read_curves(
                        os.path.join(directory, "curve.txt"), "g"))
                    task.curve(5, "g")
                elif kind == "contour":
                    assert all(task.read_contours(
                        os.path.join(directory, "contour.txt"), "g"))
                    task.contour("g")
                else:
                    assert all(task.read_areas(
                        os.path.join(directory, "area.txt"), "g"))
                    task.area(-2, "g")
                xmin, xmax, ymin, ymax = tile["extent"]
                task.grid(xmin, xmax, tile["step"],
                          ymin, ymax, tile["step"])
                task.completer(1, 1.6)
                task.solve()
                return task

            result = solve_tiled(
                build_tile, EXTENT, STEP, inner=4, halo=5,
                memmap_path=os.path.join(directory, kind + ".f64"))
            full = full_task(directory, kind)
            tiled = np.asarray(result["values"])
            assert tiled.shape == full.shape
            inner = (slice(2, -2), slice(2, -2))
            difference = np.nanmax(np.abs(tiled[inner] - full[inner]))
            span = np.nanmax(full) - np.nanmin(full)
            print("%s: tiles=%d interior_diff=%.6f span=%.3f"
                  % (kind, result["tiles"], difference, span))
            assert difference <= max(span * 0.05, 0.05), difference
        boxes = list(tile_boxes(EXTENT, STEP, inner=4, halo=2))
        assert boxes[0]["inner"] == (0, 0, 4, 4)
        assert boxes[-1]["index"] == (8, 8)
    print("PASS: tiled curve, contour and area solves")


if __name__ == "__main__":
    main()
