"""Regular-grid mesh export: glTF, OBJ, STL and undefined cells."""

import json
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


def layer(value):
    task = surfit.Session(map_name="mesh", tol=1e-7)
    task.add_points([0, 1, 0, 1], [0, 0, 1, 1], [value] * 4, name="p")
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    values = np.arange(9.0).reshape(3, 3)
    values[0, 0] = surfit.UNDEF_VALUE
    mesh = surfit.grid_mesh(
        values, {"min_x": 0, "min_y": 0, "step_x": 1, "step_y": 1})
    assert mesh["vertices"].shape == (8, 3)
    assert mesh["faces"].shape == (6, 3)

    with tempfile.TemporaryDirectory() as directory:
        gltf = os.path.join(directory, "mesh.gltf")
        obj = os.path.join(directory, "mesh.obj")
        stl = os.path.join(directory, "mesh.stl")
        ascii_stl = os.path.join(directory, "mesh-ascii.stl")
        surfit.export_gltf(gltf, mesh)
        surfit.export_obj(obj, mesh)
        surfit.export_stl(stl, mesh)
        surfit.export_stl(ascii_stl, mesh, binary=False)
        with open(gltf, encoding="utf-8") as stream:
            document = json.load(stream)
        assert document["asset"]["version"] == "2.0"
        assert os.path.getsize(obj) > 0
        assert os.path.getsize(stl) == 84 + 6 * 50
        assert "endsolid" in open(ascii_stl, encoding="ascii").read()

        stack = surfit.SurfaceStack("mesh-stack")
        stack.add_layer("top", lambda: layer(10.0))
        stack.add_layer("bottom", lambda: layer(4.0))
        stack.solve()
        stack.export_gltf(os.path.join(directory, "stack.gltf"))
        stack.export_obj(os.path.join(directory, "stack.obj"))
        stack.export_stl(os.path.join(directory, "stack.stl"))
        stack.close()

    print("PASS: mesh export, undefined cells, stack glTF/OBJ/STL")


if __name__ == "__main__":
    main()
