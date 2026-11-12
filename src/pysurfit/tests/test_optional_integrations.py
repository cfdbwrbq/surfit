"""Optional integrations with real dependencies.

Run this test with geopandas, shapely, xarray, zarr and scikit-learn on the
path; it skips cleanly when they are absent.  The normal suite runs it without
those dependencies.

  PYTHONPATH=.optional-site:build-ci/bin python3 \
      src/pysurfit/tests/test_optional_integrations.py
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


def _optional():
    try:
        import geopandas  # noqa: F401
        import shapely  # noqa: F401
        import xarray  # noqa: F401
        import zarr  # noqa: F401
        import sklearn  # noqa: F401
    except ImportError:
        return False
    return True


def layer(value):
    task = surfit.Session(map_name="optional", tol=1e-7)
    assert all(task.add_points([0, 1, 0, 1], [0, 0, 1, 1],
                               [value] * 4, name="p"))
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    if not _optional():
        print("SKIP: optional dependencies are not installed")
        return

    import geopandas as gpd
    import xarray as xr
    from shapely.geometry import LineString, Point, Polygon
    from sklearn.linear_model import LinearRegression

    points = gpd.GeoDataFrame(
        {"z": [1.0, 2.0], "w": [1.0, 0.5]},
        geometry=[Point(0.0, 0.0), Point(1.0, 1.0)], crs="EPSG:32637")
    task = surfit.Session(map_name="geo", tol=1e-7)
    task.set_metadata(crs="EPSG:32637")
    result = surfit.add_geodataframe(task, points, kind="points",
                                     z_column="z", weight_column="w")
    assert result["count"] == 2
    task.close()

    lines = gpd.GeoDataFrame(
        geometry=[LineString([(0, 0), (1, 1)])], crs="EPSG:32637")
    task = surfit.Session(map_name="geo", tol=1e-7)
    task.set_metadata(crs="EPSG:32637")
    curves = surfit.add_geodataframe(task, lines, kind="curves")
    assert curves["count"] == 1
    task.close()

    polygons = gpd.GeoDataFrame(
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])],
        crs="EPSG:32637")
    task = surfit.Session(map_name="geo", tol=1e-7)
    task.set_metadata(crs="EPSG:32637")
    areas = surfit.add_geodataframe(task, polygons, kind="areas")
    assert areas["count"] == 1
    task.close()

    mismatch = surfit.Session(map_name="geo", tol=1e-7)
    mismatch.set_metadata(crs="EPSG:4326")
    try:
        surfit.add_geodataframe(mismatch, points, kind="points",
                                z_column="z")
    except ValueError as error:
        assert "CRS" in str(error)
    else:
        raise AssertionError("CRS mismatch did not raise")
    mismatch.close()

    with surfit.SurfaceStack("optional-stack") as stack:
        stack.add_layer("top", lambda: layer(10.0))
        stack.add_layer("bottom", lambda: layer(4.0))
        stack.solve()
        stack.set_layer_uncertainty("top", residuals=[1.0, 2.0], level=0.8)
        dataset = stack.to_xarray()
        assert set(dataset.data_vars) >= {"top", "bottom", "top_lower"}
        assert dataset.sizes["x"] == stack.values("top").shape[1]
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "stack.zarr")
            stack.to_zarr(path)
            reopened = xr.open_zarr(path)
            assert np.allclose(reopened["top"].values, stack.values("top"))
            reopened.close()

    features = np.column_stack(([0.0, 1.0, 2.0, 3.0],
                                [0.0, 1.0, 0.0, 1.0]))
    values = 1.0 + 2.0 * features[:, 0] + 3.0 * features[:, 1]
    fitted = surfit.regression_trend(features, values,
                                     model=LinearRegression())
    assert fitted["rmse"] < 1e-9

    print("PASS: geopandas, xarray, zarr and sklearn integrations")


if __name__ == "__main__":
    main()
