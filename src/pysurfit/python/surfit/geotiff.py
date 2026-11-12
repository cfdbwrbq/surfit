"""Optional GeoTIFF input and output.

GDAL is preferred because it carries CRS, nodata and GeoTIFF tags.  When GDAL
is absent, ``tifffile`` can read/write the pixel data and the simple
north-up georeferencing tags; a CRS cannot be written without GDAL, and that
case raises instead of silently dropping the CRS.
"""

import os

import numpy as np

from surfit import UNDEF_VALUE
from surfit.provenance import engine_version


def _extent_geotransform(extent):
    return (
        float(extent["min_x"]) - float(extent["step_x"]) / 2.0,
        float(extent["step_x"]), 0.0,
        float(extent["max_y"]) + float(extent["step_y"]) / 2.0,
        0.0, -float(extent["step_y"]),
    )


def _extent_from_transform(transform, count_y, count_x):
    step_x = float(transform[1])
    step_y = abs(float(transform[5]))
    x_min = float(transform[0]) + step_x / 2.0
    y_center = float(transform[3]) + float(transform[5]) / 2.0
    if transform[5] < 0:
        y_min = y_center - (count_y - 1) * step_y
    else:
        y_min = y_center
    return {
        "min_x": x_min,
        "max_x": x_min + (count_x - 1) * step_x,
        "min_y": y_min,
        "max_y": y_min + (count_y - 1) * step_y,
        "step_x": step_x,
        "step_y": step_y,
        "count_x": count_x,
        "count_y": count_y,
    }


def _save_tifffile(path, values, extent, nodata):
    try:
        import tifffile
    except ImportError as error:
        raise ImportError(
            "save_geotiff needs GDAL or tifffile"
        ) from error
    geotransform = _extent_geotransform(extent)
    tags = [
        (33550, "d", 3, (geotransform[1], abs(geotransform[5]), 0.0), False),
        (33922, "d", 6, (0.0, 0.0, 0.0, geotransform[0],
                         geotransform[3], 0.0), False),
    ]
    tifffile.imwrite(path, np.flipud(values), extratags=tags)
    return path


def _read_tifffile(path, band):
    try:
        import tifffile
    except ImportError as error:
        raise ImportError(
            "read_geotiff needs GDAL or tifffile"
        ) from error
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[band - 1]
        values = page.asarray().astype(float)
        page_tags = page.tags
        scale = page_tags.get("ModelPixelScaleTag")
        tiepoint = page_tags.get("ModelTiepointTag")
        if scale is None or tiepoint is None:
            raise ValueError(
                "read_geotiff: tifffile found no GeoTIFF scale/tiepoint tags")
        scale = scale.value
        tiepoint = tiepoint.value
        transform = (float(tiepoint[3]), float(scale[0]), 0.0,
                     float(tiepoint[4]), 0.0, -float(scale[1]))
        extent = _extent_from_transform(transform, *values.shape)
        nodata_tag = page_tags.get("GDAL_NODATA")
        missing = float(nodata_tag.value) if nodata_tag is not None else None
    return {"values": np.flipud(values), "extent": extent, "crs": None,
            "nodata": missing}


def save_geotiff(path, values, extent, crs=None, nodata=None, metadata=None,
                 cog=False):
    """Write a (count_y, count_x) grid as a north-up GeoTIFF.

    GDAL is used when available; ``tifffile`` is the fallback for pixels and
    scale/tiepoint tags.  ``crs`` and ``cog=True`` require GDAL and raise a
    clear ImportError otherwise.  ``cog=True`` writes a Cloud Optimized
    GeoTIFF through GDAL's COG driver.
    """
    values = np.asarray(values, dtype=float)
    count_y, count_x = values.shape
    if count_y != int(extent["count_y"]) or count_x != int(extent["count_x"]):
        raise ValueError("values shape does not match extent")
    try:
        from osgeo import gdal, osr
    except ImportError:
        if crs or cog:
            raise ImportError(
                "save_geotiff needs GDAL for CRS or COG output") from None
        return _save_tifffile(path, values, extent, nodata)

    target = path
    temporary = None
    if cog:
        temporary = path + ".tmp.tif"
        target = temporary
    driver = gdal.GetDriverByName("GTiff")
    dataset = driver.Create(
        target, count_x, count_y, 1, gdal.GDT_Float64,
        options=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"])
    dataset.SetGeoTransform(_extent_geotransform(extent))
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
    band.SetNoDataValue(float(UNDEF_VALUE if nodata is None else nodata))
    dataset.FlushCache()
    dataset = None
    if cog:
        gdal.Translate(path, temporary, format="COG",
                       creationOptions=["COMPRESS=DEFLATE"])
        os.unlink(temporary)
    return path


def _rotated_target(transform, width, height, step_x, step_y):
    corners = []
    for px, py in ((0, 0), (width, 0), (0, height), (width, height)):
        corners.append((transform[0] + px * transform[1] + py * transform[2],
                        transform[3] + px * transform[4] + py * transform[5]))
    xs = [point[0] for point in corners]
    ys = [point[1] for point in corners]
    min_x = min(xs) + step_x / 2.0
    min_y = min(ys) + step_y / 2.0
    count_x = max(2, int(np.floor((max(xs) - min(xs)) / step_x)) + 1)
    count_y = max(2, int(np.floor((max(ys) - min(ys)) / step_y)) + 1)
    return {
        "min_x": min_x,
        "max_x": min_x + (count_x - 1) * step_x,
        "min_y": min_y,
        "max_y": min_y + (count_y - 1) * step_y,
        "step_x": step_x,
        "step_y": step_y,
        "count_x": count_x,
        "count_y": count_y,
    }


def _validate_target(extent):
    required = ("min_x", "max_x", "min_y", "max_y",
                "step_x", "step_y", "count_x", "count_y")
    missing = [key for key in required if key not in extent]
    if missing:
        raise ValueError("target_extent is missing %s" % (missing,))
    if float(extent["step_x"]) <= 0 or float(extent["step_y"]) <= 0:
        raise ValueError("target_extent steps must be positive")
    return dict(extent)


def _warp_rotated(dataset, band, target, resample, nodata):
    from osgeo import gdal

    count_x = int(target["count_x"])
    count_y = int(target["count_y"])
    step_x = float(target["step_x"])
    step_y = float(target["step_y"])
    half_x = step_x / 2.0
    half_y = step_y / 2.0
    bounds = (
        float(target["min_x"]) - half_x,
        float(target["min_y"]) - half_y,
        float(target["min_x"]) + (count_x - 1) * step_x + half_x,
        float(target["min_y"]) + (count_y - 1) * step_y + half_y,
    )
    options = gdal.WarpOptions(
        format="MEM", width=count_x, height=count_y, outputBounds=bounds,
        xRes=step_x, yRes=step_y, resampleAlg=resample,
        srcNodata=None if nodata is None else float(nodata),
        dstNodata=None if nodata is None else float(nodata))
    warped = gdal.Warp("", dataset, options=options)
    if warped is None:
        raise ValueError("read_geotiff: GDAL warp failed")
    values = warped.GetRasterBand(band).ReadAsArray().astype(float)
    missing = warped.GetRasterBand(band).GetNoDataValue()
    if missing is not None:
        values[values == missing] = UNDEF_VALUE
    values = np.flipud(values)
    warped = None
    return values, target, missing


def read_geotiff(path, band=1, nodata=None, target_extent=None,
                 resample="bilinear"):
    """Read one north-up GeoTIFF band into a surfit grid.

    GDAL is preferred; ``tifffile`` is a fallback for north-up pixel data and
    scale/tiepoint tags (CRS is then ``None``).  A rotated raster is explicitly
    warped to a regular north-up grid: ``target_extent`` selects that grid,
    otherwise its bounding box and pixel size are used.  The result records
    ``rotated`` and ``resampled`` so the caller can see that a warp happened.
    """
    try:
        from osgeo import gdal
    except ImportError:
        if target_extent is not None or not (resample == "bilinear"):
            raise ImportError(
                "read_geotiff needs GDAL for a rotated/targeted read") from None
        return _read_tifffile(path, band)
    dataset = gdal.Open(str(path))
    if dataset is None:
        raise ValueError("read_geotiff: cannot open %s" % (path,))
    if band < 1 or band > dataset.RasterCount:
        raise ValueError("read_geotiff: band %d is out of range" % (band,))
    transform = dataset.GetGeoTransform(can_return_null=True)
    if transform is None:
        raise ValueError("read_geotiff: raster has no geotransform")
    rotated = (transform[2] != 0 or transform[4] != 0 or transform[1] <= 0)
    if rotated or target_extent is not None:
        if target_extent is None:
            step_x = float(np.hypot(transform[1], transform[4]))
            step_y = float(np.hypot(transform[2], transform[5]))
            step = min(step_x, step_y)
            target = _rotated_target(transform, dataset.RasterXSize,
                                     dataset.RasterYSize, step, step)
        else:
            target = _validate_target(target_extent)
        if resample not in ("nearest", "bilinear", "cubic"):
            raise ValueError("resample must be nearest, bilinear or cubic")
        values, target, missing = _warp_rotated(
            dataset, band, target, resample, nodata)
        crs = dataset.GetProjection()
        dataset = None
        return {"values": values, "extent": target, "crs": crs or None,
                "nodata": missing, "rotated": bool(rotated),
                "resampled": True, "resampling": resample}
    if transform[2] != 0 or transform[4] != 0:
        raise ValueError(
            "read_geotiff: only north-up rasters without rotation are supported")
    raster = dataset.GetRasterBand(band)
    values = raster.ReadAsArray().astype(float)
    file_nodata = raster.GetNoDataValue()
    missing = nodata if nodata is not None else file_nodata
    if missing is not None:
        values[values == missing] = UNDEF_VALUE
    if transform[5] < 0:
        values = np.flipud(values)
    extent = _extent_from_transform(transform, *values.shape)
    crs = dataset.GetProjection()
    dataset = None
    return {"values": values, "extent": extent, "crs": crs or None,
            "nodata": missing, "rotated": False, "resampled": False,
            "resampling": None}


def save_geotiff_stack(directory, layers, extent, crs=None, nodata=None):
    """Write named layers as individual GeoTIFFs plus a JSON manifest."""
    import json

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


def save_geotiff_bands(path, layers, extent, crs=None, nodata=None,
                       metadata=None, cog=False):
    """Write several layers as bands of one GeoTIFF.

    Band descriptions preserve layer names.  The function needs GDAL; it is
    the multi-band counterpart of :func:`save_geotiff_stack`.
    """
    try:
        from osgeo import gdal, osr
    except ImportError as error:
        raise ImportError(
            "save_geotiff_bands needs GDAL") from error
    count_y = int(extent["count_y"])
    count_x = int(extent["count_x"])
    target = path
    temporary = None
    if cog:
        temporary = path + ".tmp.tif"
        target = temporary
    dataset = gdal.GetDriverByName("GTiff").Create(
        target, count_x, count_y, len(layers), gdal.GDT_Float64,
        options=["TILED=YES", "COMPRESS=DEFLATE", "BIGTIFF=IF_SAFER"])
    dataset.SetGeoTransform(_extent_geotransform(extent))
    if crs:
        spatial = osr.SpatialReference()
        spatial.SetFromUserInput(str(crs))
        dataset.SetProjection(spatial.ExportToWkt())
    for index, (name, values) in enumerate(layers.items(), 1):
        band = dataset.GetRasterBand(index)
        band.SetDescription(str(name))
        band.WriteArray(np.flipud(np.asarray(values, dtype=float)))
        band.SetNoDataValue(float(UNDEF_VALUE if nodata is None else nodata))
    dataset.FlushCache()
    dataset = None
    if cog:
        gdal.Translate(path, temporary, format="COG",
                       creationOptions=["COMPRESS=DEFLATE"])
        os.unlink(temporary)
    return path
