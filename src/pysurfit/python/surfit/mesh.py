"""Mesh export for regular grids and SurfaceStack layers.

The grid is triangulated per cell; cells with an undefined or masked corner are
skipped.  glTF, OBJ and STL are written without a heavy dependency.  PyVista is
optional and imported only by ``to_pyvista``.
"""

import base64
import json
import struct

import numpy as np

_UNDEF = float(np.finfo(np.float32).max)


def _defined(values):
    return ~np.isclose(values, _UNDEF, rtol=1e-6) & np.isfinite(values)


def grid_mesh(values, extent, mask=None, name=None):
    """Return vertices/faces for defined cells of a regular grid."""
    values = np.asarray(values, dtype=float)
    if values.ndim != 2:
        raise ValueError("values must be a 2D grid")
    count_y, count_x = values.shape
    x0 = float(extent["min_x"])
    y0 = float(extent["min_y"])
    sx = float(extent["step_x"])
    sy = float(extent["step_y"])
    valid = _defined(values)
    if mask is not None:
        mask = np.asarray(mask, dtype=bool)
        if mask.shape != values.shape:
            raise ValueError("mask shape must match values")
        valid &= mask
    index = -np.ones(values.shape, dtype=np.int64)
    index[valid] = np.arange(int(valid.sum()))
    vertices = np.empty((count_y, count_x, 3), dtype=float)
    vertices[:, :, 0] = x0 + np.arange(count_x)[None, :] * sx
    vertices[:, :, 1] = y0 + np.arange(count_y)[:, None] * sy
    vertices[:, :, 2] = values
    vertices = vertices.reshape(-1, 3)[valid.reshape(-1)]
    faces = []
    for j in range(count_y - 1):
        for i in range(count_x - 1):
            a = index[j, i]
            b = index[j, i + 1]
            c = index[j + 1, i + 1]
            d = index[j + 1, i]
            if min(a, b, c, d) < 0:
                continue
            faces.append((a, b, c))
            faces.append((a, c, d))
    return {
        "name": name or "surface",
        "vertices": np.asarray(vertices, dtype=float),
        "faces": np.asarray(faces, dtype=np.int64).reshape(-1, 3),
        "extent": dict(extent),
    }


def stack_meshes(stack, names=None, masks=None):
    """Triangulate every selected layer of a SurfaceStack."""
    names = list(stack.layer_names() if names is None else names)
    result = {}
    for name in names:
        mask = None if masks is None else masks.get(name)
        result[name] = grid_mesh(stack.values(name), stack.extent(),
                                 mask=mask, name=name)
    return result


def _mesh_mapping(layers):
    if isinstance(layers, dict) and "vertices" not in layers:
        return layers
    return {layers.get("name", "surface"): layers}


def _gltf_document(layers, up_axis):
    document = {
        "asset": {"version": "2.0", "generator": "surfit"},
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": [], "meshes": [], "accessors": [], "bufferViews": [],
        "buffers": [],
    }
    blobs = []
    offset = 0
    for index, (name, mesh) in enumerate(layers.items()):
        vertices = np.asarray(mesh["vertices"], dtype=np.float64)
        if up_axis == "y":
            vertices = vertices[:, [0, 2, 1]]
            vertices[:, 2] *= -1.0
        positions = vertices.astype("<f4").tobytes()
        indices = np.asarray(mesh["faces"], dtype="<u4").tobytes()
        position_view = len(document["bufferViews"])
        document["bufferViews"].append({
            "buffer": 0, "byteOffset": offset, "byteLength": len(positions)})
        offset += len(positions)
        blobs.append(positions)
        index_view = len(document["bufferViews"])
        document["bufferViews"].append({
            "buffer": 0, "byteOffset": offset, "byteLength": len(indices)})
        offset += len(indices)
        blobs.append(indices)
        document["accessors"].append({
            "bufferView": position_view, "componentType": 5126,
            "count": int(vertices.shape[0]), "type": "VEC3",
            "min": vertices.min(axis=0).tolist(),
            "max": vertices.max(axis=0).tolist()})
        document["accessors"].append({
            "bufferView": index_view, "componentType": 5125,
            "count": int(mesh["faces"].size), "type": "SCALAR"})
        accessor = 2 * index
        document["meshes"].append({"name": str(name), "primitives": [{
            "attributes": {"POSITION": accessor},
            "indices": accessor + 1, "mode": 4}]})
        document["nodes"].append({"name": str(name), "mesh": index})
        document["scenes"][0]["nodes"].append(index)
    payload = b"".join(blobs)
    document["buffers"].append({
        "byteLength": len(payload),
        "uri": "data:application/octet-stream;base64," +
               base64.b64encode(payload).decode("ascii")})
    return document


def export_gltf(path, layers, up_axis="y"):
    """Write a minimal glTF 2.0 file (embedded buffer) for one or more meshes."""
    meshes = _mesh_mapping(layers)
    document = _gltf_document(meshes, up_axis)
    with open(path, "w", encoding="utf-8") as stream:
        json.dump(document, stream)
    return path


def export_obj(path, layers):
    """Write OBJ vertices/faces with one object group per layer."""
    meshes = _mesh_mapping(layers)
    offset = 1
    with open(path, "w", encoding="utf-8") as stream:
        for name, mesh in meshes.items():
            stream.write("o %s\n" % (name,))
            for vertex in mesh["vertices"]:
                stream.write("v %.10g %.10g %.10g\n" % tuple(vertex))
            for face in mesh["faces"]:
                stream.write("f %d %d %d\n" % tuple(int(i + offset)
                                                       for i in face))
            offset += len(mesh["vertices"])
    return path


def _face_normal(a, b, c):
    normal = np.cross(b - a, c - a)
    length = np.linalg.norm(normal)
    return normal / length if length > 0 else np.zeros(3)


def export_stl(path, layers, binary=True):
    """Write one layer as STL; a multi-layer mapping is rejected explicitly."""
    if isinstance(layers, dict) and "vertices" not in layers:
        if len(layers) != 1:
            raise ValueError("STL supports one layer; pass a single mesh")
        layers = next(iter(layers.values()))
    vertices = np.asarray(layers["vertices"], dtype=float)
    faces = np.asarray(layers["faces"], dtype=np.int64)
    if binary:
        with open(path, "wb") as stream:
            stream.write(b"surfit".ljust(80, b" "))
            stream.write(struct.pack("<I", len(faces)))
            for face in faces:
                a, b, c = vertices[face]
                normal = _face_normal(a, b, c)
                stream.write(struct.pack("<12fH", *normal, *a, *b, *c, 0))
    else:
        with open(path, "w", encoding="ascii") as stream:
            stream.write("solid surfit\n")
            for face in faces:
                a, b, c = vertices[face]
                normal = _face_normal(a, b, c)
                stream.write(" facet normal %.6g %.6g %.6g\n" % tuple(normal))
                stream.write("  outer loop\n")
                for vertex in (a, b, c):
                    stream.write("   vertex %.6g %.6g %.6g\n" % tuple(vertex))
                stream.write("  endloop\n endfacet\n")
            stream.write("endsolid surfit\n")
    return path


def to_pyvista(layers):
    """Return a PyVista PolyData or MultiBlock; PyVista is optional."""
    try:
        import pyvista as pv
    except ImportError as error:
        raise ImportError("to_pyvista needs pyvista") from error
    meshes = _mesh_mapping(layers)
    blocks = {}
    for name, mesh in meshes.items():
        faces = np.column_stack((
            np.full(len(mesh["faces"]), 3), mesh["faces"])).ravel()
        blocks[name] = pv.PolyData(mesh["vertices"], faces)
    if len(blocks) == 1:
        return next(iter(blocks.values()))
    return pv.MultiBlock(blocks)
