"""Optional GeoParquet adapter without GDAL.

pyarrow carries the Parquet data and GeoParquet metadata; shapely decodes WKB.
The adapter is deliberately explicit: CRS mismatch raises, and unsupported
geometry mixtures are rejected instead of being silently dropped.
"""

import json

import numpy as np


def _dependencies():
    try:
        import pyarrow.parquet as parquet
        from shapely import wkb
    except ImportError as error:
        raise ImportError(
            "GeoParquet needs pyarrow and shapely") from error
    return parquet, wkb


def _geometry_metadata(table):
    metadata = table.schema.metadata or {}
    raw = metadata.get(b"geo")
    if raw is None:
        raw = metadata.get("geo")
    if raw is None:
        return {"primary_column": "geometry", "columns": {}}
    return json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)


def _geometry_crs(geo):
    primary = geo.get("primary_column", "geometry")
    record = geo.get("columns", {}).get(primary, {})
    crs = record.get("crs")
    if isinstance(crs, dict):
        return crs.get("name") or json.dumps(crs, sort_keys=True)
    return crs


def _check_crs(task, crs):
    target = getattr(task, "metadata", {}).get("crs")
    if crs is not None and target is not None and str(crs) != str(target):
        raise ValueError("GeoParquet CRS %s does not match task CRS %s"
                         % (crs, target))


def _load_geometries(path):
    parquet, wkb = _dependencies()
    table = parquet.read_table(path)
    geo = _geometry_metadata(table)
    primary = geo.get("primary_column", "geometry")
    if primary not in table.column_names:
        raise ValueError("GeoParquet geometry column %r is missing" % (primary,))
    geometries = []
    for value in table.column(primary).to_pylist():
        if value is None:
            raise ValueError("GeoParquet contains a null geometry")
        if isinstance(value, bytes):
            geometries.append(wkb.loads(value))
        elif isinstance(value, (str,)):
            geometries.append(wkb.loads(value.encode("latin-1")))
        else:
            geometries.append(value)
    return table, geometries, _geometry_crs(geo), primary


def _kind(geometry):
    name = geometry.geom_type
    if name == "Point":
        return "points"
    if name in ("LineString", "MultiLineString"):
        return "curves"
    if name in ("Polygon", "MultiPolygon"):
        return "areas"
    raise ValueError("unsupported GeoParquet geometry %r" % (name,))


def _line_coordinates(geometry):
    if geometry.geom_type == "LineString":
        return np.asarray([[p[0], p[1]] for p in geometry.coords])
    if geometry.geom_type == "MultiLineString":
        return np.vstack([_line_coordinates(part) for part in geometry.geoms])
    raise ValueError("expected LineString/MultiLineString")


def _polygon_coordinates(geometry):
    if geometry.geom_type == "Polygon":
        return np.asarray([[p[0], p[1]] for p in geometry.exterior.coords])
    if geometry.geom_type == "MultiPolygon":
        return [_polygon_coordinates(part) for part in geometry.geoms]
    raise ValueError("expected Polygon/MultiPolygon")


def add_geoparquet(task, path, kind="auto", name="geo", z_column=None,
                   weight_column=None):
    """Add Point/LineString/Polygon GeoParquet rows to a Session."""
    table, geometries, crs, _ = _load_geometries(path)
    _check_crs(task, crs)
    kinds = {_kind(geometry) for geometry in geometries}
    if kind == "auto":
        if len(kinds) != 1:
            raise ValueError("mixed GeoParquet geometry types; pass kind=")
        kind = kinds.pop()
    elif kind not in kinds:
        raise ValueError("GeoParquet rows are not %r" % (kind,))
    if kind == "points":
        x = np.array([geometry.x for geometry in geometries], dtype=float)
        y = np.array([geometry.y for geometry in geometries], dtype=float)
        if z_column is not None:
            z = np.asarray(table.column(z_column).to_pylist(), dtype=float)
        elif all(geometry.has_z for geometry in geometries):
            z = np.array([geometry.z for geometry in geometries], dtype=float)
        else:
            raise ValueError("Point GeoParquet has no Z; pass z_column")
        weights = None
        if weight_column is not None:
            weights = np.asarray(table.column(weight_column).to_pylist(),
                                 dtype=float)
        task.add_points(x, y, z, weights=weights, name=name)
        return {"kind": kind, "name": name, "count": len(x), "crs": crs}
    if weight_column is not None:
        raise ValueError("weight_column is only supported for points")
    if kind == "curves":
        names = []
        for index, geometry in enumerate(geometries):
            coordinates = _line_coordinates(geometry)
            item = "%s_%03d" % (name, index)
            task.add_curves(coordinates[:, 0], coordinates[:, 1], name=item)
            names.append(item)
        return {"kind": kind, "names": names, "count": len(names), "crs": crs}
    if kind == "areas":
        names = []
        for index, geometry in enumerate(geometries):
            parts = _polygon_coordinates(geometry)
            if isinstance(parts, list):
                for part_index, coordinates in enumerate(parts):
                    item = "%s_%03d_%03d" % (name, index, part_index)
                    task.add_areas(coordinates[:, 0], coordinates[:, 1],
                                   name=item)
                    names.append(item)
            else:
                item = "%s_%03d" % (name, index)
                task.add_areas(parts[:, 0], parts[:, 1], name=item)
                names.append(item)
        return {"kind": kind, "names": names, "count": len(names), "crs": crs}
    raise ValueError("kind must be points, curves or areas")


def save_geoparquet(path, geometries, crs=None, columns=None):
    """Write WKB geometries and optional columns as GeoParquet."""
    try:
        import pyarrow as pa
        import pyarrow.parquet as parquet
        from shapely import wkb
    except ImportError as error:
        raise ImportError(
            "GeoParquet needs pyarrow and shapely") from error
    geometries = list(geometries)
    if not geometries:
        raise ValueError("at least one geometry is required")
    arrays = [pa.array([wkb.dumps(geometry) for geometry in geometries])]
    names = ["geometry"]
    if columns:
        for key, values in columns.items():
            arrays.append(pa.array(values))
            names.append(str(key))
    table = pa.Table.from_arrays(arrays, names=names)
    geo = {
        "version": "1.1.0",
        "primary_column": "geometry",
        "columns": {"geometry": {
            "encoding": "WKB",
            "geometry_types": [geometry.geom_type for geometry in geometries],
            "crs": crs,
        }},
    }
    metadata = dict(table.schema.metadata or {})
    metadata[b"geo"] = json.dumps(geo).encode("utf-8")
    table = table.replace_schema_metadata(metadata)
    parquet.write_table(table, path)
    return path
