"""Optional GeoParquet adapter; skips without pyarrow/shapely."""

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    try:
        from shapely.geometry import LineString, Point, Polygon
    except ImportError:
        print("SKIP: shapely is not installed")
        return
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        print("SKIP: pyarrow is not installed")
        return

    with tempfile.TemporaryDirectory() as directory:
        points = os.path.join(directory, "points.parquet")
        surfit.save_geoparquet(
            points, [Point(0, 0, 1), Point(1, 1, 2)], crs="EPSG:32637",
            columns={"w": [1.0, 0.5]})
        task = surfit.Session(map_name="geoparquet")
        task.set_metadata(crs="EPSG:32637")
        result = surfit.add_geoparquet(
            task, points, kind="points", weight_column="w")
        assert result["count"] == 2
        task.close()

        lines = os.path.join(directory, "lines.parquet")
        surfit.save_geoparquet(
            lines, [LineString([(0, 0), (1, 1)])], crs="EPSG:32637")
        task = surfit.Session(map_name="geoparquet")
        assert surfit.add_geoparquet(task, lines, kind="curves")["count"] == 1
        task.close()

        areas = os.path.join(directory, "areas.parquet")
        surfit.save_geoparquet(
            areas, [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
            crs="EPSG:32637")
        task = surfit.Session(map_name="geoparquet")
        assert surfit.add_geoparquet(task, areas, kind="areas")["count"] == 1
        task.close()

    print("PASS: GeoParquet points/curves/areas round trip")


if __name__ == "__main__":
    main()
