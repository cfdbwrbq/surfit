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


def read_geotiff(path, band=1, nodata=None):
    """Read one north-up GeoTIFF band into a surfit grid.

    Returns ``{"values", "extent", "crs", "nodata"}``.  Cells are cell
    centres, matching :func:`save_geotiff`; a north-up raster is flipped so
    row 0 is ``min_y``.  Rotated or west-up rasters are rejected rather than
    silently misaligned.  GDAL is optional.
    """
    try:
        from osgeo import gdal
    except ImportError as error:
        raise ImportError(
            "read_geotiff needs GDAL; install the system gdal python bindings"
        ) from error
    dataset = gdal.Open(str(path))
    if dataset is None:
        raise ValueError("read_geotiff: cannot open %s" % (path,))
    if band < 1 or band > dataset.RasterCount:
        raise ValueError("read_geotiff: band %d is out of range" % (band,))
    transform = dataset.GetGeoTransform(can_return_null=True)
    if transform is None or transform[2] != 0 or transform[4] != 0:
        raise ValueError(
            "read_geotiff: only north-up rasters without rotation are supported")
    if transform[1] <= 0:
        raise ValueError("read_geotiff: west-up x spacing is not supported")
    raster = dataset.GetRasterBand(band)
    values = raster.ReadAsArray().astype(float)
    file_nodata = raster.GetNoDataValue()
    missing = nodata if nodata is not None else file_nodata
    if missing is not None:
        values[values == missing] = UNDEF_VALUE
    count_y, count_x = values.shape
    step_x = float(transform[1])
    step_y = abs(float(transform[5]))
    x_min = float(transform[0]) + step_x / 2.0
    y_center = float(transform[3]) + float(transform[5]) / 2.0
    if transform[5] < 0:
        values = np.flipud(values)
        y_min = y_center - (count_y - 1) * step_y
    else:
        y_min = y_center
    extent = {
        "min_x": x_min,
        "max_x": x_min + (count_x - 1) * step_x,
        "min_y": y_min,
        "max_y": y_min + (count_y - 1) * step_y,
        "step_x": step_x,
        "step_y": step_y,
        "count_x": count_x,
        "count_y": count_y,
    }
    crs = dataset.GetProjection()
    dataset = None
    return {"values": values, "extent": extent, "crs": crs or None,
            "nodata": missing}


def save_geotiff_stack(directory, layers, extent, crs=None, nodata=None):
    """Write named layers as individual GeoTIFFs plus a JSON manifest.

    ``layers`` is a mapping name -> array.  The manifest keeps the layer order,
    file names, extent, CRS and nodata; this is the exchange format, not a
    second private container.
    """
    import json
    import os

    os.makedirs(directory, exist_ok=True)
    document = {"layers": [], "extent": dict(extent), "crs": crs,
                "nodata": nodata}
    for index, (name, values) in enumerate(layers.items()):
        filename = "layer_%03d.tif" % index
        path = os.path.join(directory, filename)
        save_geotiff(path, values, extent, crs=crs, nodata=nodata)
        document["layers"].append({"name": str(name), "file": filename})
    with open(os.path.join(directory, "manifest.json"), "w",
              encoding="utf-8") as stream:
        json.dump(document, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return document
