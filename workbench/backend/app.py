"""FastAPI surface workbench: upload points/faults, solve, inspect, export."""

from __future__ import annotations

import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BIN = os.environ.get("SURFIT_BIN", "")
if BIN:
    sys.path.insert(0, BIN)
import surfit  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
WORK = Path(os.environ.get(
    "SURFIT_STUDIO_WORK",
    str(Path.home() / ".local" / "share" / "surfit-studio"),
))
try:
    WORK.mkdir(parents=True, exist_ok=True)
    probe = WORK / ".write-test"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()
except OSError:
    # Sandboxes may mount HOME read-only; keep the app usable and say where
    # projects went rather than failing at import time.
    print("warning: %s is not writable; using a temporary work directory" % WORK)
    WORK = Path(tempfile.gettempdir()) / "surfit-studio"
    WORK.mkdir(parents=True, exist_ok=True)
PROJECTS = WORK / "projects"
PROJECTS.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD = 25 * 1024 * 1024
MAX_POINTS = 200_000
MAX_CELLS = 1_000_000
AUTO_GRID_SIDE = 200
JOB_TTL = 60 * 60 * 6

app = FastAPI(title="surfit surface workbench", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")
_pool = ThreadPoolExecutor(max_workers=1)
_lock = threading.Lock()
_jobs: Dict[str, "Job"] = {}


@dataclass
class Job:
    id: str
    status: str = "queued"
    error: Optional[str] = None
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    mesh: Optional[dict] = None
    metrics: Optional[dict] = None
    dat_path: Optional[str] = None
    gltf_path: Optional[str] = None
    workdir: str = ""
    name: str = "surface"


def _parse_table(raw: bytes) -> np.ndarray:
    text = raw.decode("utf-8", errors="replace")
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.replace(",", " ").replace(";", " ").split()
        try:
            values = [float(item) for item in parts]
        except ValueError:
            if not rows:
                continue  # header
            raise HTTPException(400, "data must be numeric columns: x y z [weight]")
        rows.append(values)
    if not rows:
        raise HTTPException(400, "empty data file")
    width = min(len(row) for row in rows)
    if width < 3:
        raise HTTPException(400, "points need at least x y z")
    return np.asarray([row[:width] for row in rows], dtype=float)


def _geojson_features(raw: bytes):
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(400, "invalid GeoJSON: %s" % error)
    if document.get("type") == "FeatureCollection":
        return list(document.get("features", []))
    if document.get("type") == "Feature":
        return [document]
    raise HTTPException(400, "GeoJSON must be a Feature or FeatureCollection")


def _shp_features(raw: bytes, suffix: str = ".zip"):
    """Read an ESRI shapefile without GDAL via pyshp."""
    try:
        import shapefile
    except ImportError as error:
        raise HTTPException(400, "SHP support needs pyshp (pip install pyshp)") from error
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "upload" + suffix)
        with open(path, "wb") as handle:
            handle.write(raw)
        if suffix == ".zip":
            archive = os.path.join(directory, "data")
            try:
                with zipfile.ZipFile(path) as bundle:
                    for name in bundle.namelist():
                        if name.startswith("/") or ".." in name.split("/"):
                            raise HTTPException(400, "unsafe path in archive")
                    bundle.extractall(archive)
            except zipfile.BadZipFile as error:
                raise HTTPException(400, "upload a zip of .shp/.shx/.dbf/.prj") from error
            candidates = list(Path(archive).rglob("*.shp"))
            if not candidates:
                raise HTTPException(400, "archive has no .shp")
            path = str(candidates[0])
        try:
            reader = shapefile.Reader(path)
        except Exception as error:
            raise HTTPException(400, "could not read SHP: %s" % error) from error
        try:
            names = [field[0] for field in reader.fields[1:]]
            records = list(reader.records())
        except Exception:
            # A bare .shp is valid geometry; there is simply no DBF.
            names = []
            records = None
        shapes = list(reader.iterShapes())
        features = []
        for index, shape in enumerate(shapes):
            properties = {}
            if records is not None and index < len(records):
                properties = dict(zip(names, records[index]))
            features.append({
                "type": "Feature",
                "geometry": shape.__geo_interface__,
                "properties": properties,
            })
        if not features:
            raise HTTPException(400, "SHP has no features")
        return features


def _features(raw: bytes, filename: Optional[str]):
    suffix = Path(filename or "").suffix.lower()
    if suffix in (".geojson", ".json"):
        return _geojson_features(raw)
    if suffix in (".shp", ".gpkg", ".zip"):
        if suffix == ".gpkg":
            raise HTTPException(400, "GeoPackage needs geopandas; use SHP or GeoJSON")
        return _shp_features(raw, suffix)
    return None


def _line_list(geometry):
    if not geometry:
        return []
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if kind == "LineString":
        return [coords]
    if kind == "MultiLineString":
        return list(coords)
    if kind == "Polygon":
        return [coords[0]] if coords else []
    if kind == "MultiPolygon":
        return [part[0] for part in coords if part]
    return []


def _fields_from(x_field="", y_field="", z_field="", weight_field=""):
    return {key: value.strip() for key, value in (
        ("x", x_field), ("y", y_field), ("z", z_field), ("weight", weight_field))
            if value and value.strip()}


def _value_filter(min_value=None, max_value=None, exclude_zero=False):
    return {"min": min_value, "max": max_value, "exclude_zero": bool(exclude_zero)}


def _validate_value_filter(min_value, max_value):
    if min_value is not None and max_value is not None and min_value > max_value:
        raise HTTPException(400, "min_value must not exceed max_value")


def _value_allowed(value, value_filter):
    if not value_filter:
        return True
    if value_filter.get("exclude_zero") and value == 0:
        return False
    minimum = value_filter.get("min")
    maximum = value_filter.get("max")
    if minimum is not None and value < minimum:
        return False
    if maximum is not None and value > maximum:
        return False
    return True


def _field_value(properties, name, label):
    if name not in properties:
        raise HTTPException(400, "%s field %r is not present" % (label, name))
    try:
        return float(properties[name])
    except (TypeError, ValueError) as error:
        raise HTTPException(400, "%s field %r is not numeric" % (label, name)) from error


def _point_values(feature, fields=None):
    fields = fields or {}
    geometry = feature.get("geometry") or {}
    properties = feature.get("properties") or {}
    x_field = fields.get("x")
    y_field = fields.get("y")
    z_field = fields.get("z")
    weight_field = fields.get("weight")
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if kind == "Point":
        points = [coords]
    elif kind == "MultiPoint":
        points = list(coords)
    else:
        raise HTTPException(400, "points file must contain Point features")
    result = []
    for coordinate in points:
        if x_field or y_field:
            if not x_field or not y_field:
                raise HTTPException(400, "choose both x and y fields")
            x = _field_value(properties, x_field, "x")
            y = _field_value(properties, y_field, "y")
        else:
            if len(coordinate) < 2:
                raise HTTPException(400, "GeoJSON point has no x/y")
            x, y = float(coordinate[0]), float(coordinate[1])
        if z_field:
            z = _field_value(properties, z_field, "z")
        elif len(coordinate) > 2:
            z = float(coordinate[2])
        else:
            z = properties.get("z")
            if z is None:
                for candidate in ("Z", "elev", "elevation", "value"):
                    if candidate in properties:
                        z = properties[candidate]
                        break
            if z is None:
                raise HTTPException(
                    400, "points need a z coordinate or a z field; choose the field")
            z = float(z)
        weight = properties.get(weight_field) if weight_field else properties.get("weight")
        result.append((x, y, z, float(weight) if weight is not None else 1.0))
    return result


def _points(raw: Optional[bytes], filename: Optional[str] = None, fields=None,
            value_filter=None):
    if raw is None:
        return None, None, None, None
    features = _features(raw, filename)
    if features is not None:
        rows = []
        for feature in features:
            rows.extend(_point_values(feature, fields))
        if not rows:
            raise HTTPException(400, "points file has no features")
        data = np.asarray(rows, dtype=float)
        if data.shape[0] > MAX_POINTS:
            raise HTTPException(400, "too many points (limit %d)" % MAX_POINTS)
        keep = np.array([_value_allowed(float(value), value_filter)
                         for value in data[:, 2]], dtype=bool)
        data = data[keep]
        return data[:, 0], data[:, 1], data[:, 2], data[:, 3]
    data = _parse_table(raw)
    if data.shape[0] > MAX_POINTS:
        raise HTTPException(400, "too many points (limit %d)" % MAX_POINTS)
    keep = np.array([_value_allowed(float(value), value_filter)
                     for value in data[:, 2]], dtype=bool)
    data = data[keep]
    weights = data[:, 3] if data.shape[1] >= 4 else None
    return data[:, 0], data[:, 1], data[:, 2], weights


def _faults(raw: Optional[bytes], filename: Optional[str] = None):
    if raw is None:
        return []
    features = _features(raw, filename)
    if features is not None:
        result = []
        for index, feature in enumerate(features):
            for part, line in enumerate(_line_list(feature.get("geometry"))):
                if len(line) >= 2:
                    result.append(("fault_%d_%d" % (index, part),
                                   np.asarray(line, dtype=float)[:, :2]))
        if not result:
            raise HTTPException(400, "faults file has no LineString features")
        return result
    data = _parse_table(raw)
    groups = {}
    if data.shape[1] >= 3:
        ids = data[:, 2].astype(int)
    else:
        ids = np.zeros(data.shape[0], dtype=int)
    for index, group_id in enumerate(ids):
        groups.setdefault(int(group_id), []).append(data[index, :2])
    return [(str(name), np.asarray(points, dtype=float))
            for name, points in sorted(groups.items()) if len(points) >= 2]


def _contours(raw: Optional[bytes], filename: Optional[str] = None, fields=None,
              value_filter=None):
    if raw is None:
        return []
    features = _features(raw, filename)
    if features is not None:
        result = []
        fields = fields or {}
        for index, feature in enumerate(features):
            properties = feature.get("properties") or {}
            z_field = fields.get("z")
            default_z = (properties.get(z_field) if z_field
                         else properties.get("z", properties.get("value")))
            for part, line in enumerate(_line_list(feature.get("geometry"))):
                if len(line) < 2:
                    continue
                rows = []
                for coordinate in line:
                    if len(coordinate) > 2:
                        rows.append([coordinate[0], coordinate[1], coordinate[2]])
                    elif default_z is not None:
                        rows.append([coordinate[0], coordinate[1], default_z])
                    else:
                        raise HTTPException(
                            400, "contour line needs z coordinates or a z/value property")
                line = np.asarray(rows, dtype=float)
                if line.size and not _value_allowed(float(line[0, 2]), value_filter):
                    continue
                result.append(("contour_%d_%d" % (index, part), line))
        if not result:
            raise HTTPException(400, "contours file has no LineString features")
        return result
    data = _parse_table(raw)
    groups = {}
    if data.shape[1] >= 4:
        ids = data[:, 3].astype(int)
    else:
        ids = np.zeros(data.shape[0], dtype=int)
    for index, group_id in enumerate(ids):
        groups.setdefault(int(group_id), []).append(data[index, :3])
    result = []
    for name, points in sorted(groups.items()):
        if len(points) < 2:
            continue
        line = np.asarray(points, dtype=float)
        if not _value_allowed(float(line[0, 2]), value_filter):
            continue
        result.append((str(name), line))
    return result


def _areas(raw: Optional[bytes], filename: Optional[str] = None):
    if raw is None:
        return []
    features = _features(raw, filename)
    if features is None:
        raise HTTPException(400, "areas must be GeoJSON or SHP polygons")
    result = []
    for index, feature in enumerate(features):
        properties = feature.get("properties") or {}
        for part, line in enumerate(_line_list(feature.get("geometry"))):
            if len(line) < 3:
                continue
            polygon = np.asarray(line, dtype=float)[:, :2]
            if not np.allclose(polygon[0], polygon[-1]):
                polygon = np.vstack([polygon, polygon[0]])
            result.append(("area_%d_%d" % (index, part), polygon, properties))
    if not result:
        raise HTTPException(400, "areas file has no polygon features")
    return result


def _parse_area_rules(raw: Optional[str]):
    if not raw:
        return []
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(400, "area_rules must be JSON") from error
    if not isinstance(rules, list):
        raise HTTPException(400, "area_rules must be a list")
    return rules


def _parse_global_rules(raw: Optional[str]):
    if not raw:
        return []
    try:
        rules = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(400, "global_rules must be JSON") from error
    if not isinstance(rules, list):
        raise HTTPException(400, "global_rules must be a list")
    return rules


DEFAULT_RULE_ORDER = ["points", "contours", "faults", "areas", "global",
                      "bounds", "completer"]


def _parse_rule_order(raw: Optional[str]):
    if not raw:
        return list(DEFAULT_RULE_ORDER)
    try:
        order = json.loads(raw)
    except json.JSONDecodeError as error:
        raise HTTPException(400, "rule_order must be JSON") from error
    if not isinstance(order, list) or not all(isinstance(item, str) for item in order):
        raise HTTPException(400, "rule_order must be a list of strings")
    result = [item for item in order if item in DEFAULT_RULE_ORDER]
    for item in DEFAULT_RULE_ORDER:
        if item not in result:
            result.append(item)
    return result


def _mesh(values, extent, points, faults, contours=(), areas=(), max_side=260):
    values = np.asarray(values, dtype=float)
    step = max(1, int(np.ceil(max(values.shape) / max_side)))
    sampled = values[::step, ::step]
    sampled_extent = {
        "min_x": extent["min_x"],
        "min_y": extent["min_y"],
        "step_x": extent["step_x"] * step,
        "step_y": extent["step_y"] * step,
    }
    mesh = surfit.grid_mesh(sampled, sampled_extent)
    valid = np.isfinite(values) & (values < float(np.finfo(np.float32).max))
    zmin = float(np.nanmin(values[valid])) if valid.any() else 0.0
    zmax = float(np.nanmax(values[valid])) if valid.any() else 1.0
    return {
        "vertices": np.asarray(mesh["vertices"], dtype=float).tolist(),
        "faces": np.asarray(mesh["faces"], dtype=int).tolist(),
        "points": points.tolist(),
        "faults": [{"name": str(name), "points": pts.tolist()}
                   for name, pts in faults],
        "contours": [{"name": str(name), "points": pts.tolist()}
                     for name, pts in contours],
        "areas": [{"name": str(name), "points": pts.tolist()}
                  for name, pts in areas],
        "zmin": zmin,
        "zmax": zmax,
        "extent": dict(extent),
        "stride": step,
        "shape": [int(values.shape[0]), int(values.shape[1])],
        "defined": int(valid.sum()),
        "undefined": int(values.size - valid.sum()),
        "total": int(values.size),
    }


def _solve(job: Job, point_files, fault_files, contour_files, area_files,
           surface_files, area_rules, global_rules, rule_order, fields, value_filter,
           cell_size: float, auto_cell: bool, tol: float, solver: str,
           d1: float, d2: float,
           lower: Optional[float], upper: Optional[float], extent_values):
    try:
        job.status = "running"
        job.updated = time.time()
        point_rows = []
        for raw, name in point_files:
            px, py, pz, pw = _points(raw, name, fields, value_filter)
            if px is None:
                continue
            weights = np.ones(px.size) if pw is None else np.asarray(pw, dtype=float)
            point_rows.append((px, py, pz, weights))
        if point_rows:
            x = np.concatenate([row[0] for row in point_rows])
            y = np.concatenate([row[1] for row in point_rows])
            z = np.concatenate([row[2] for row in point_rows])
            weights = np.concatenate([row[3] for row in point_rows])
            if x.size > MAX_POINTS:
                raise ValueError("too many points across files")
        else:
            x = y = z = weights = None
        faults = []
        for index, (raw, name) in enumerate(fault_files):
            for feature, line in _faults(raw, name):
                feature_name = feature if feature.startswith("fault") else "fault_%s" % feature
                faults.append(("%d_%s" % (index, feature_name), line))
        contours = []
        for index, (raw, name) in enumerate(contour_files):
            for feature, line in _contours(raw, name, fields, value_filter):
                feature_name = feature if feature.startswith("contour") else "contour_%s" % feature
                contours.append(("%d_%s" % (index, feature_name), line))
        areas = []
        for index, (raw, name) in enumerate(area_files):
            for feature, polygon, properties in _areas(raw, name):
                areas.append(("%d_%s" % (index, feature), polygon, properties))
        if x is None and not contours:
            raise ValueError("give points, contours, or both")
        if x is None and len(contours) < 2:
            # A single contour-only task crashes the current CMOFS completer;
            # reject it here until the core handles this degenerate input.
            raise ValueError("contour-only solve needs at least two contour lines")
        if extent_values and all(item is not None for item in extent_values):
            min_x, max_x, min_y, max_y = [float(item) for item in extent_values]
        else:
            all_x = [] if x is None else [x]
            all_y = [] if y is None else [y]
            for _name, line in contours:
                all_x.append(line[:, 0])
                all_y.append(line[:, 1])
            for _name, polygon, _properties in areas:
                all_x.append(polygon[:, 0])
                all_y.append(polygon[:, 1])
            xs = np.concatenate(all_x)
            ys = np.concatenate(all_y)
            pad_base = 0.0 if auto_cell else cell_size
            pad_x = max(float(np.ptp(xs)) * 0.05, pad_base)
            pad_y = max(float(np.ptp(ys)) * 0.05, pad_base)
            min_x, max_x = float(xs.min()) - pad_x, float(xs.max()) + pad_x
            min_y, max_y = float(ys.min()) - pad_y, float(ys.max()) + pad_y
        if max_x <= min_x or max_y <= min_y:
            raise ValueError("extent is empty")
        if auto_cell:
            cell_size = max(max_x - min_x, max_y - min_y) / AUTO_GRID_SIDE
        if cell_size <= 0:
            raise ValueError("cell size must be positive")
        nx = int(np.floor((max_x - min_x) / cell_size)) + 1
        ny = int(np.floor((max_y - min_y) / cell_size)) + 1
        if nx < 2 or ny < 2 or nx * ny > MAX_CELLS:
            raise ValueError("grid too large: %d x %d" % (nx, ny))
        step_x = (max_x - min_x) / (nx - 1)
        step_y = (max_y - min_y) / (ny - 1)
        task = surfit.Session(map_name="studio", tol=tol, strict=True)
        task.set_solver(solver)
        surface_dir = tempfile.TemporaryDirectory()
        surface_names = []
        for index, (raw, original) in enumerate(surface_files):
            surface_path = os.path.join(surface_dir.name, "surface_%d.func" % index)
            with open(surface_path, "wb") as handle:
                handle.write(raw)
            before = set(task.surf_names())
            loaded = task.surf_load(surface_path)
            if not any(loaded):
                raise ValueError("could not load surface %s" % (original or index))
            new_names = [name for name in task.surf_names() if name not in before]
            if not new_names:
                raise ValueError("surface %s has no readable grid" % (original or index))
            surface_names.append(new_names[0])
        if x is not None:
            task.add_points(x, y, z, weights=weights, name="points")
        for name, line in contours:
            curve_name = str(name) if "contour" in str(name) else "contour_%s" % name
            task.add_contours(line[:, 0], line[:, 1], line[:, 2], name=curve_name)
        for name, line in faults:
            curve_name = str(name) if "fault" in str(name) else "fault_%s" % name
            task.add_curves(line[:, 0], line[:, 1], name=curve_name)
        for name, polygon, _properties in areas:
            task.add_areas(polygon[:, 0], polygon[:, 1], name=str(name))
        task.grid(min_x, max_x, step_x, min_y, max_y, step_y)
        def add_points_rule():
            if x is not None:
                task.points("points")

        def add_contours_rule():
            for name, _line in contours:
                curve_name = str(name) if "contour" in str(name) else "contour_%s" % name
                task.contour(curve_name)

        def add_faults_rule():
            for name, _line in faults:
                curve_name = str(name) if "fault" in str(name) else "fault_%s" % name
                task.fault(curve_name)

        def add_area_rules():
            area_by_name = {str(name): name for name, _polygon, _props in areas}
            for index, rule in enumerate(area_rules):
                rule = rule or {}
                name = rule.get("name", "")
                if name not in area_by_name and index < len(areas):
                    name = areas[index][0]
                if name not in area_by_name:
                    continue
                area_name = str(name)
                mode = rule.get("mode", "none")
                if mode == "constant":
                    task.area(float(rule["value"]), area_name)
                elif mode == "bounds":
                    if rule.get("lower") is not None:
                        task.area_geq(float(rule["lower"]), area_name)
                    if rule.get("upper") is not None:
                        task.area_leq(float(rule["upper"]), area_name)
                elif mode in ("undef", "mask"):
                    task.area("undef", area_name)
                elif mode == "mean":
                    task.area_mean(float(rule["value"]), area_name)
                elif mode == "add":
                    task.area_add(float(rule["value"]), float(rule.get("weight", 0.1)),
                                  area_name)

        def add_global_rules():
            for rule in global_rules:
                mode = rule.get("mode", "none")
                if mode == "mean":
                    task.mean(float(rule["value"]), 0)
                elif mode == "wmean":
                    surface = str(rule.get("surface", ""))
                    if surface.startswith("surface_"):
                        surface = surface_names[int(surface.split("_")[1])]
                    task.wmean(float(rule["value"]), surface, 0)
                elif mode == "trend":
                    surface = str(rule.get("surface", ""))
                    if surface.startswith("surface_"):
                        surface = surface_names[int(surface.split("_")[1])]
                    task.trend(float(rule.get("weight", 1)),
                               int(rule.get("order", 10)), surface)

        def add_bounds():
            if lower is not None:
                task.geq(lower)
            if upper is not None:
                task.leq(upper)

        handlers = {
            "points": add_points_rule, "contours": add_contours_rule,
            "faults": add_faults_rule, "areas": add_area_rules,
            "global": add_global_rules, "bounds": add_bounds,
            "completer": lambda: task.completer(d1, d2),
        }
        for group in rule_order:
            handlers[group]()
        task.solve()
        values = np.asarray(task.values(), dtype=float)
        extent = {"min_x": min_x, "min_y": min_y,
                  "step_x": step_x, "step_y": step_y}
        mesh_points = (np.column_stack((x, y, z)) if x is not None
                       else np.empty((0, 3), dtype=float))
        job.mesh = _mesh(values, extent, mesh_points,
                         [(name, pts) for name, pts in faults], contours,
                         [(name, polygon) for name, polygon, _props in areas])
        job.metrics = {
            "points": int(0 if x is None else x.size),
            "contours": len(contours),
            "faults": len(faults),
            "areas": len(areas),
            "surfaces": len(surface_files),
            "grid": [int(nx), int(ny)],
            "cell_size": float(cell_size),
            "auto_cell": bool(auto_cell),
            "tol": float(tol),
            "solver": solver,
            "defined": job.mesh["defined"],
            "undefined": job.mesh["total"] - job.mesh["defined"],
            "zmin": job.mesh["zmin"],
            "zmax": job.mesh["zmax"],
            "rule_report": task.rule_report(),
        }
        job.dat_path = str(WORK / (job.id + ".dat"))
        task.save(job.dat_path)
        job.gltf_path = str(WORK / (job.id + ".gltf"))
        surfit.export_gltf(job.gltf_path, surfit.grid_mesh(values, extent))
        task.close()
        job.status = "done"
    except Exception as error:  # report the failure to the browser
        job.status = "error"
        job.error = "%s: %s" % (type(error).__name__, error)
    finally:
        job.updated = time.time()


def _cleanup():
    now = time.time()
    with _lock:
        for key, job in list(_jobs.items()):
            if now - job.updated > JOB_TTL:
                for path in (job.dat_path, job.gltf_path):
                    if path and os.path.exists(path):
                        os.unlink(path)
                _jobs.pop(key, None)


def _project_path(project_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{12}", project_id):
        raise HTTPException(404, "project not found")
    path = PROJECTS / project_id
    if not path.is_dir():
        raise HTTPException(404, "project not found")
    return path


def _project_meta(project_id: str) -> dict:
    path = _project_path(project_id)
    with open(path / "project.json", encoding="utf-8") as stream:
        return json.load(stream)


def _project_response(meta: dict) -> dict:
    project_id = meta["id"]
    counters = {}
    sources = []
    for item in meta.get("sources", []):
        role = item["role"]
        index = counters.get(role, 0)
        counters[role] = index + 1
        sources.append({"role": role, "name": item["name"],
                        "url": "/api/projects/%s/sources/%s/%d"
                               % (project_id, role, index)})
    return {
        "id": project_id,
        "name": meta.get("name", "Untitled"),
        "created": meta.get("created"),
        "updated": meta.get("updated"),
        "settings": meta.get("settings", {}),
        "sources": sources,
        "has_result": bool(meta.get("result")),
        "counts": meta.get("counts", {}),
        "downloads": {
            "dat": "/api/projects/%s/download.dat" % project_id
            if meta.get("result", {}).get("dat") else None,
            "gltf": "/api/projects/%s/download.gltf" % project_id
            if meta.get("result", {}).get("gltf") else None,
            "mesh": "/api/projects/%s/mesh" % project_id
            if meta.get("result", {}).get("mesh") else None,
        },
    }


def _safe_name(name: str) -> str:
    base = Path(name or "data").name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base)
    return (base or "data")[:120]


@app.get("/api/projects")
def list_projects():
    projects = []
    for path in PROJECTS.iterdir():
        if not path.is_dir() or not (path / "project.json").exists():
            continue
        try:
            meta = _project_meta(path.name)
        except (OSError, ValueError, KeyError):
            continue
        projects.append(_project_response(meta))
    projects.sort(key=lambda item: item.get("updated", 0), reverse=True)
    return {"projects": projects}


@app.post("/api/projects")
async def save_project(
    points: List[UploadFile] = File(default=[]),
    faults: List[UploadFile] = File(default=[]),
    contours: List[UploadFile] = File(default=[]),
    areas: List[UploadFile] = File(default=[]),
    surfaces: List[UploadFile] = File(default=[]),
    area_rules: str = Form(""),
    global_rules: str = Form(""),
    rule_order: str = Form(""),
    name: str = Form("Untitled"),
    job_id: Optional[str] = Form(None),
    x_field: str = Form(""),
    y_field: str = Form(""),
    z_field: str = Form(""),
    weight_field: str = Form(""),
    min_value: Optional[float] = Form(None),
    max_value: Optional[float] = Form(None),
    exclude_zero: bool = Form(False),
    cell_size: float = Form(1.0),
    cell_size_auto: bool = Form(False),
    tol: float = Form(1e-6),
    solver: str = Form("cg"),
    d1: float = Form(1.0),
    d2: float = Form(1.6),
    lower: Optional[float] = Form(None),
    upper: Optional[float] = Form(None),
    min_x: Optional[float] = Form(None),
    max_x: Optional[float] = Form(None),
    min_y: Optional[float] = Form(None),
    max_y: Optional[float] = Form(None),
):
    point_files = await _read_group(points, "points")
    fault_files = await _read_group(faults, "faults")
    contour_files = await _read_group(contours, "contours")
    area_files = await _read_group(areas, "areas")
    surface_files = await _read_group(surfaces, "surfaces")
    if not point_files and not contour_files:
        raise HTTPException(400, "save at least one points or contours file")
    project_id = uuid.uuid4().hex[:12]
    path = PROJECTS / project_id
    sources_dir = path / "sources"
    sources_dir.mkdir(parents=True)
    sources = []
    for role, group in (("points", point_files), ("faults", fault_files),
                        ("contours", contour_files), ("areas", area_files),
                        ("surfaces", surface_files)):
        role_dir = sources_dir / role
        role_dir.mkdir()
        for index, (raw, original) in enumerate(group):
            filename = "%03d_%s" % (index, _safe_name(original or role))
            with open(role_dir / filename, "wb") as handle:
                handle.write(raw)
            sources.append({"role": role, "name": original or filename,
                            "stored": "%s/%s" % (role, filename)})
    settings = {"cell_size": cell_size, "cell_size_auto": cell_size_auto,
                "tol": tol, "solver": solver,
                "d1": d1, "d2": d2, "lower": lower, "upper": upper,
                "min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y,
                "x_field": x_field, "y_field": y_field, "z_field": z_field,
                "weight_field": weight_field,
                "min_value": min_value, "max_value": max_value,
                "exclude_zero": exclude_zero,
                "area_rules": _parse_area_rules(area_rules),
                "global_rules": _parse_global_rules(global_rules),
                "rule_order": _parse_rule_order(rule_order)}
    counts = {"points": len(point_files), "faults": len(fault_files),
              "contours": len(contour_files), "areas": len(area_files),
              "surfaces": len(surface_files)}
    result = {}
    job = _jobs.get(job_id) if job_id else None
    if job is not None and job.status == "done":
        result = {}
        if job.mesh is not None:
            with open(path / "mesh.json", "w", encoding="utf-8") as stream:
                json.dump(job.mesh, stream)
            result["mesh"] = "mesh.json"
        if job.metrics is not None:
            with open(path / "metrics.json", "w", encoding="utf-8") as stream:
                json.dump(job.metrics, stream)
            result["metrics"] = "metrics.json"
        for key, source in (("dat", job.dat_path), ("gltf", job.gltf_path)):
            if source and os.path.exists(source):
                target = path / ("result." + key)
                shutil.copyfile(source, target)
                result[key] = target.name
    now = time.time()
    meta = {"id": project_id, "name": (name or "Untitled")[:120],
            "created": now, "updated": now, "settings": settings,
            "sources": sources, "counts": counts, "result": result}
    with open(path / "project.json", "w", encoding="utf-8") as stream:
        json.dump(meta, stream, indent=2)
    return _project_response(meta)


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    return _project_response(_project_meta(project_id))


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    path = _project_path(project_id)
    shutil.rmtree(path)
    return {"deleted": project_id}


@app.get("/api/projects/{project_id}/archive")
def export_project(project_id: str):
    path = _project_path(project_id)
    archive = WORK / ("project-%s.zip" % project_id)
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for item in path.rglob("*"):
            if item.is_file():
                bundle.write(item, item.relative_to(path))
    return FileResponse(archive, filename="surfit-project-%s.zip" % project_id)


@app.post("/api/projects/import")
async def import_project(archive: UploadFile = File(...)):
    raw = await archive.read()
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(400, "project archive too large")
    temporary = WORK / ("import-%s.zip" % uuid.uuid4().hex[:12])
    with open(temporary, "wb") as handle:
        handle.write(raw)
    project_id = uuid.uuid4().hex[:12]
    target = PROJECTS / project_id
    try:
        with zipfile.ZipFile(temporary) as bundle:
            for name in bundle.namelist():
                if name.startswith("/") or ".." in name.split("/"):
                    raise HTTPException(400, "unsafe path in project archive")
            if "project.json" not in bundle.namelist():
                raise HTTPException(400, "project archive has no project.json")
            bundle.extractall(target)
        meta_path = target / "project.json"
        with open(meta_path, encoding="utf-8") as stream:
            meta = json.load(stream)
        meta["id"] = project_id
        meta["name"] = str(meta.get("name", "Imported"))[:120]
        meta["updated"] = time.time()
        with open(meta_path, "w", encoding="utf-8") as stream:
            json.dump(meta, stream, indent=2)
        return _project_response(meta)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
    finally:
        if temporary.exists():
            temporary.unlink()


@app.get("/api/projects/{project_id}/sources/{role}/{index}")
def project_source(project_id: str, role: str, index: int):
    if role not in {"points", "faults", "contours", "areas", "surfaces"}:
        raise HTTPException(404, "source not found")
    meta = _project_meta(project_id)
    matches = [item for item in meta.get("sources", []) if item["role"] == role]
    if index < 0 or index >= len(matches):
        raise HTTPException(404, "source not found")
    path = _project_path(project_id) / "sources" / matches[index]["stored"]
    if not path.is_file():
        raise HTTPException(404, "source not found")
    return FileResponse(path, filename=matches[index]["name"])


@app.get("/api/projects/{project_id}/mesh")
def project_mesh(project_id: str):
    meta = _project_meta(project_id)
    name = meta.get("result", {}).get("mesh")
    if not name:
        raise HTTPException(404, "project has no result")
    return FileResponse(_project_path(project_id) / name, media_type="application/json")


@app.get("/api/projects/{project_id}/metrics")
def project_metrics(project_id: str):
    meta = _project_meta(project_id)
    name = meta.get("result", {}).get("metrics")
    if not name:
        raise HTTPException(404, "project has no result")
    return FileResponse(_project_path(project_id) / name, media_type="application/json")


@app.get("/api/projects/{project_id}/download.dat")
def project_dat(project_id: str):
    meta = _project_meta(project_id)
    name = meta.get("result", {}).get("dat")
    if not name:
        raise HTTPException(404, "project has no result")
    return FileResponse(_project_path(project_id) / name, filename="surfit-result.dat")


@app.get("/api/projects/{project_id}/download.gltf")
def project_gltf(project_id: str):
    meta = _project_meta(project_id)
    name = meta.get("result", {}).get("gltf")
    if not name:
        raise HTTPException(404, "project has no result")
    return FileResponse(_project_path(project_id) / name, filename="surfit-surface.gltf")


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


async def _read_group(group, label):
    result = []
    for upload in group:
        raw = await upload.read()
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(400, "%s file too large" % label)
        result.append((raw, upload.filename))
    return result


def _preview_sources(point_files, fault_files, contour_files, area_files,
                     surface_files, fields=None, value_filter=None):
    points = []
    point_count = 0
    fields = fields or {}
    for raw, name in point_files:
        px, py, pz, _weights = _points(raw, name, fields, value_filter)
        if px is not None:
            point_count += int(px.size)
            if point_count > MAX_POINTS:
                raise HTTPException(400, "too many points")
            points.extend(zip(px.tolist(), py.tolist(), pz.tolist()))
    faults = []
    for index, (raw, name) in enumerate(fault_files):
        for feature, line in _faults(raw, name):
            faults.append({"name": "%d_%s" % (index, feature),
                           "points": line.tolist()})
    contours = []
    for index, (raw, name) in enumerate(contour_files):
        for feature, line in _contours(raw, name, fields, value_filter):
            contours.append({"name": "%d_%s" % (index, feature),
                             "points": line.tolist()})
    areas = []
    for index, (raw, name) in enumerate(area_files):
        for feature, polygon, properties in _areas(raw, name):
            areas.append({"name": "%d_%s" % (index, feature),
                          "points": polygon.tolist(),
                          "properties": properties})
    surfaces = [{"key": "surface_%d" % index, "name": name or "surface"}
                for index, (_raw, name) in enumerate(surface_files)]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    for item in faults + contours + areas:
        xs.extend(point[0] for point in item["points"])
        ys.extend(point[1] for point in item["points"])
    bounds = None
    if xs:
        bounds = {"min_x": min(xs), "max_x": max(xs),
                  "min_y": min(ys), "max_y": max(ys)}
    return {
        "points": points,
        "faults": faults,
        "contours": contours,
        "areas": areas,
        "surfaces": surfaces,
        "counts": {"points": len(points), "faults": len(faults),
                   "contours": len(contours), "areas": len(areas),
                   "surfaces": len(surfaces)},
        "bounds": bounds,
    }


def _schema_for_group(group):
    names = set()
    for raw, filename in group:
        features = _features(raw, filename)
        if features is None:
            # Text tables: expose a conventional header when one is present.
            for line in raw.decode("utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.replace(",", " ").replace(";", " ").split()
                try:
                    [float(item) for item in parts]
                except ValueError:
                    names.update(part for part in parts if part)
                break
            continue
        for feature in features:
            names.update((feature.get("properties") or {}).keys())
    return sorted(names)


@app.post("/api/schema")
async def schema(
    points: List[UploadFile] = File(default=[]),
    faults: List[UploadFile] = File(default=[]),
    contours: List[UploadFile] = File(default=[]),
    areas: List[UploadFile] = File(default=[]),
    surfaces: List[UploadFile] = File(default=[]),
):
    point_files = await _read_group(points, "points")
    fault_files = await _read_group(faults, "faults")
    contour_files = await _read_group(contours, "contours")
    area_files = await _read_group(areas, "areas")
    surface_files = await _read_group(surfaces, "surfaces")
    return {
        "points": _schema_for_group(point_files),
        "faults": _schema_for_group(fault_files),
        "contours": _schema_for_group(contour_files),
        "areas": _schema_for_group(area_files),
        "surfaces": [],
    }


@app.post("/api/preview")
async def preview(
    points: List[UploadFile] = File(default=[]),
    faults: List[UploadFile] = File(default=[]),
    contours: List[UploadFile] = File(default=[]),
    areas: List[UploadFile] = File(default=[]),
    surfaces: List[UploadFile] = File(default=[]),
    x_field: str = Form(""),
    y_field: str = Form(""),
    z_field: str = Form(""),
    weight_field: str = Form(""),
    min_value: Optional[float] = Form(None),
    max_value: Optional[float] = Form(None),
    exclude_zero: bool = Form(False),
):
    _validate_value_filter(min_value, max_value)
    point_files = await _read_group(points, "points")
    fault_files = await _read_group(faults, "faults")
    contour_files = await _read_group(contours, "contours")
    area_files = await _read_group(areas, "areas")
    surface_files = await _read_group(surfaces, "surfaces")
    if not point_files and not contour_files and not fault_files and not area_files:
        return _preview_sources([], [], [], [], surface_files)
    return _preview_sources(
        point_files, fault_files, contour_files, area_files, surface_files,
        _fields_from(x_field, y_field, z_field, weight_field),
        _value_filter(min_value, max_value, exclude_zero))


@app.get("/api/health")
def health():
    return {"ok": True, "jobs": len(_jobs)}


@app.post("/api/jobs")
async def create_job(
    points: List[UploadFile] = File(default=[]),
    faults: List[UploadFile] = File(default=[]),
    contours: List[UploadFile] = File(default=[]),
    areas: List[UploadFile] = File(default=[]),
    surfaces: List[UploadFile] = File(default=[]),
    area_rules: str = Form(""),
    global_rules: str = Form(""),
    rule_order: str = Form(""),
    x_field: str = Form(""),
    y_field: str = Form(""),
    z_field: str = Form(""),
    weight_field: str = Form(""),
    min_value: Optional[float] = Form(None),
    max_value: Optional[float] = Form(None),
    exclude_zero: bool = Form(False),
    cell_size: float = Form(1.0),
    cell_size_auto: bool = Form(False),
    tol: float = Form(1e-6),
    solver: str = Form("cg"),
    d1: float = Form(1.0),
    d2: float = Form(1.6),
    lower: Optional[float] = Form(None),
    upper: Optional[float] = Form(None),
    min_x: Optional[float] = Form(None),
    max_x: Optional[float] = Form(None),
    min_y: Optional[float] = Form(None),
    max_y: Optional[float] = Form(None),
):
    if not cell_size_auto and cell_size <= 0:
        raise HTTPException(400, "cell_size must be positive")
    if solver not in {"cg", "jcg", "ssor", "jacobi", "rf"}:
        raise HTTPException(400, "unknown solver")
    _validate_value_filter(min_value, max_value)
    point_files = await _read_group(points, "points")
    fault_files = await _read_group(faults, "faults")
    contour_files = await _read_group(contours, "contours")
    area_files = await _read_group(areas, "areas")
    surface_files = await _read_group(surfaces, "surfaces")
    if not point_files and not contour_files:
        raise HTTPException(400, "upload points or contours")
    _cleanup()
    job = Job(id=uuid.uuid4().hex[:12])
    with _lock:
        _jobs[job.id] = job
    _pool.submit(_solve, job, point_files, fault_files, contour_files,
                 area_files, surface_files, _parse_area_rules(area_rules),
                 _parse_global_rules(global_rules), _parse_rule_order(rule_order),
                 _fields_from(x_field, y_field, z_field, weight_field),
                 _value_filter(min_value, max_value, exclude_zero),
                 cell_size, cell_size_auto, tol, solver, d1, d2, lower, upper,
                 (min_x, max_x, min_y, max_y))
    return {"id": job.id, "status": job.status}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return {
        "id": job.id, "status": job.status, "error": job.error,
        "metrics": job.metrics,
        "downloads": {
            "dat": "/api/jobs/%s/download.dat" % job.id if job.dat_path else None,
            "gltf": "/api/jobs/%s/download.gltf" % job.id if job.gltf_path else None,
        },
    }


@app.get("/api/jobs/{job_id}/mesh")
def get_mesh(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if job.status != "done" or job.mesh is None:
        raise HTTPException(409, "job is not solved")
    return JSONResponse(job.mesh)


@app.get("/api/jobs/{job_id}/download.dat")
def download_dat(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job.dat_path or not os.path.exists(job.dat_path):
        raise HTTPException(404, "result not found")
    return FileResponse(job.dat_path, filename="surfit-result.dat")


@app.get("/api/jobs/{job_id}/download.gltf")
def download_gltf(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job.gltf_path or not os.path.exists(job.gltf_path):
        raise HTTPException(404, "result not found")
    return FileResponse(job.gltf_path, filename="surfit-surface.gltf")
