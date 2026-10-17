"""The terrain example -- examples/globe/dem.tcl, written in Python.

    python3 examples/python/dem.py

Loads an SRTM tile of Sao Tome from the zipped HGT file, grids the island and
makes the surface equal to the DEM there, interpolating between the tile's
3-arcsecond samples.  The sea is zero in the tile, so the island rises out of a
flat surface at sea level.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "globe")
TILE = "N00E006.hgt"


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_dem", tol=1e-5)

    assert all(task.dem_load_hgt_zip(os.path.join(DATA, TILE + ".zip"), TILE))

    task.grid(6.4, 6.8, 0.0005, 0, 0.48, 0.0005)

    task.dem(TILE)
    task.completer()

    task.solve()
    task.grid_unload()
    return task


def main():
    task = build()
    task.save("dem.dat")

    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved dem.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.1f max=%.1f mean=%.1f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("the 3-arcsecond average flattens the summit: Pico de Sao Tome is "
          "2024 m")


if __name__ == "__main__":
    main()
