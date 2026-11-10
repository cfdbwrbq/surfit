"""Optional GeoTIFF output with a real CRS.

GDAL is not a required dependency of surfit.  Import this module only when the
extra is installed (``python -m pip install gdal`` or the system package); the
rest of the package keeps working without it.
"""

import numpy as np

from surfit import UNDEF_VALUE
from surfit.provenance import engine_version


def save_geotiff(path, values, extent, crs=None, nodata=None, metadata=None):
    """Write a (count_y, count_x) grid as a north-up GeoTIFF.

    ``extent`` is the ``surf_extent`` dict; nodes are cell centres, so the
    raster corners are half a step outside the first and last node.  ``crs`` is
    anything ``osr.SpatialReference.SetFromUserInput`` accepts, for example
    ``"EPSG:32637"`` or a WKT string.
    """
    try:
        from osgeo import gdal, osr
    except ImportError as error:
        raise ImportError(
            "save_geotiff needs GDAL; install the system gdal python bindings"
        ) from error

    values = np.asarray(values, dtype=float)
    count_y, count_x = values.shape
    if count_y != int(extent["count_y"]) or count_x != int(extent["count_x"]):
        raise ValueError("values shape does not match extent")

    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(
        path, count_x, count_y, 1, gdal.GDT_Float64,
        options=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"])
    geotransform = (
        float(extent["min_x"]) - float(extent["step_x"]) / 2.0,
        float(extent["step_x"]), 0.0,
        float(extent["max_y"]) + float(extent["step_y"]) / 2.0,
        0.0, -float(extent["step_y"]),
    )
    dataset.SetGeoTransform(geotransform)
    if crs:
        spatial = osr.SpatialReference()
        spatial.SetFromUserInput(str(crs))
        dataset.SetProjection(spatial.ExportToWkt())
    dataset.SetMetadata({
        "SURFIT_VERSION": engine_version(),
        "SURFIT_NODATA": str(float(UNDEF_VALUE if nodata is None else nodata)),
    })
    if metadata:
        for key, value in metadata.items():
            if value is not None:
                dataset.SetMetadataItem(
                    "SURFIT_" + str(key).upper(), str(value))
    band = dataset.GetRasterBand(1)
    band.WriteArray(np.flipud(values))
    band.SetNoDataValue(
        float(UNDEF_VALUE if nodata is None else nodata))
    dataset.FlushCache()
    dataset = None
    return path
