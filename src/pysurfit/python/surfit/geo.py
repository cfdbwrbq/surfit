"""Optional GeoPandas/Shapely adapter.

GeoPandas is not required.  When it is installed, ``add_geodataframe`` copies
Point, LineString and Polygon coordinates into the native array constructors.
CRS is checked, never silently reprojected.
"""

import numpy as np


def _check_crs(task, gdf):
    source = getattr(gdf, "crs", None)
    target = getattr(task, "metadata", {}).get("crs")
    if source is not None and target is not None and str(source) != str(target):
        raise ValueError(
            "GeoDataFrame CRS %s does not match task CRS %s"
            % (source, target))


def _point_columns(gdf, z_column):
    x = []
    y = []
    z = []
    for geometry in gdf.geometry:
        if geometry is None or geometry.geom_type != "Point":
            raise ValueError("points_from_geodataframe needs Point geometries")
        x.append(float(geometry.x))
        y.append(float(geometry.y))
        if z_column is not None:
            z.append(float(geometry.z) if z_column == "__z__"
                     else float(gdf[z_column].iloc[len(z)]))
        elif geometry.has_z:
            z.append(float(geometry.z))
        else:
            raise ValueError("Point geometry has no Z; pass z_column")
    weights = None
    return np.asarray(x), np.asarray(y), np.asarray(z), weights


def _line_coordinates(geometry):
    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)
        return np.asarray([[point[0], point[1]] for point in coords])
    if geometry.geom_type == "MultiLineString":
        parts = [_line_coordinates(part) for part in geometry.geoms]
        return np.vstack(parts)
    raise ValueError("curves need LineString or MultiLineString geometries")


def _polygon_coordinates(geometry):
    if geometry.geom_type == "Polygon":
        return np.asarray([[point[0], point[1]]
                           for point in geometry.exterior.coords])
    if geometry.geom_type == "MultiPolygon":
        parts = [_polygon_coordinates(part) for part in geometry.geoms]
        return parts
    raise ValueError("areas need Polygon or MultiPolygon geometries")


def add_geodataframe(task, gdf, kind="points", name="geo", z_column=None,
                     weight_column=None):
    """Add a GeoDataFrame to a Session without an intermediate file.

    ``kind`` is ``points``, ``curves`` or ``areas``.  For points, Z comes from
    ``z_column`` or from the Point geometry; ``weight_column`` is optional.
    Lines and polygons create one named object per geometry.  Holes and
    attributes other than the optional weight are not copied.
    """
    try:
        import geopandas  # noqa: F401
    except ImportError as error:
        raise ImportError(
            "add_geodataframe needs geopandas") from error
    if gdf.empty:
        raise ValueError("GeoDataFrame is empty")
    _check_crs(task, gdf)
    if kind == "points":
        x, y, z, _ = _point_columns(gdf, z_column)
        weights = None
        if weight_column is not None:
            weights = np.asarray(gdf[weight_column], dtype=float)
        task.add_points(x, y, z, weights=weights, name=name)
        return {"kind": kind, "name": name, "count": int(len(x))}
    if weight_column is not None:
        raise ValueError("weight_column is only supported for points")
    if kind == "curves":
        names = []
        for index, geometry in enumerate(gdf.geometry):
            coordinates = _line_coordinates(geometry)
            item_name = "%s_%03d" % (name, index)
            task.add_curves(coordinates[:, 0], coordinates[:, 1],
                            name=item_name)
            names.append(item_name)
        return {"kind": kind, "names": names, "count": len(names)}
    if kind == "areas":
        names = []
        for index, geometry in enumerate(gdf.geometry):
            parts = _polygon_coordinates(geometry)
            if isinstance(parts, list):
                for part_index, coordinates in enumerate(parts):
                    item_name = "%s_%03d_%03d" % (name, index, part_index)
                    task.add_areas(coordinates[:, 0], coordinates[:, 1],
                                   name=item_name)
                    names.append(item_name)
            else:
                item_name = "%s_%03d" % (name, index)
                task.add_areas(parts[:, 0], parts[:, 1], name=item_name)
                names.append(item_name)
        return {"kind": kind, "names": names, "count": len(names)}
    raise ValueError("kind must be 'points', 'curves' or 'areas'")
