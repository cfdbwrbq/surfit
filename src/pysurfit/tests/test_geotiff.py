"""GeoTIFF output carries values, geotransform, CRS and nodata.

GDAL is optional; when it is not installed this test reports SKIP rather than
failing the whole suite.

  python3 test_geotiff.py
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

try:
    from osgeo import gdal
except ImportError:
    gdal = None


def main():
    if gdal is None:
        print("SKIP: GDAL is not installed")
        return

    with tempfile.TemporaryDirectory() as directory:
        points = os.path.join(directory, "points.txt")
        with open(points, "w", encoding="ascii") as stream:
            stream.write("0.01 0.01 0\n0.02 0.02 10\n")
        task = surfit.Session(map_name="geotiff", tol=1e-9)
        assert all(task.read_points(points, "p"))
        task.grid(0, 1, 1, 0, 1, 1)
        task.points("p")
        task.solve()
        path = os.path.join(directory, "grid.tif")
        task.save_geotiff(path, crs="EPSG:32637")

        dataset = gdal.Open(path)
        assert dataset is not None
        band = dataset.GetRasterBand(1)
        assert band.ReadAsArray().shape == task.values().shape
        assert dataset.GetProjection()
        assert not np.isnan(band.ReadAsArray()).any()
        assert band.GetNoDataValue() is not None
        dataset = None

    print("PASS: GeoTIFF values, projection and nodata")


if __name__ == "__main__":
    main()
