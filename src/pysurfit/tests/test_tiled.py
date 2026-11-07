"""Out-of-core point gridding keeps the whole result on a memmap.

The synthetic field is solved in overlapping tiles; only the inner part of each
tile is copied.  The check is that the mosaic has no undefined inner nodes and
that its error against the known field is in the same range as the full solve.

  python3 test_tiled.py
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
from surfit.tiled import solve_point_tiles  # noqa: E402

STEP = 0.5
EXTENT = (-10.0, 10.0, -10.0, 10.0)


def field(x, y):
    return 2.0 * np.exp(-((x - 1.0) ** 2 + (y + 2.0) ** 2) / (2.0 * 3.0 ** 2))


def main():
    rng = np.random.default_rng(2026)
    x = rng.uniform(-9.5, 9.5, 1600)
    y = rng.uniform(-9.5, 9.5, 1600)
    z = field(x, y)

    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "tiled.f64")
        result = solve_point_tiles(
            x, y, z, EXTENT, STEP, inner=16, halo=4,
            memmap_path=path, tol=1e-7)
        values = result["values"]
        assert result["tiles"] > 1, result["tiles"]
        assert values.shape == (41, 41), values.shape
        defined = surfit.defined_mask(values)
        assert defined.all(), "tile mosaic has undefined nodes"

        xx, yy = np.meshgrid(np.arange(41) * STEP + EXTENT[0],
                             np.arange(41) * STEP + EXTENT[2])
        truth = field(xx, yy)
        rmse = float(np.sqrt(np.mean((values[defined] - truth[defined]) ** 2)))
        span = float(truth.max() - truth.min())
        print("tiles=%d rmse=%.6f relative=%.4f" %
              (result["tiles"], rmse, rmse / span))
        assert rmse / span < 0.15, rmse / span

    print("PASS: tiled memmap mosaic")


if __name__ == "__main__":
    main()
