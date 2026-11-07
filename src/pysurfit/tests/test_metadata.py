"""Provenance metadata is kept on the task and written as a sidecar.

The engine formats do not carry CRS or units, so the Python layer records them
next to the result instead of pretending that a .dat or .grd file has them.

  python3 test_metadata.py
"""

import json
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
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "result.meta.json")
        task = surfit.Session(
            map_name="meta",
            metadata={"crs": "EPSG:32637", "x_units": "m", "y_units": "m"})
        task.set_metadata(z_units="m", source="synthetic")
        assert task.metadata["crs"] == "EPSG:32637"
        assert task.metadata["source"] == "synthetic"
        task.save_metadata(path)
        with open(path, encoding="utf-8") as stream:
            document = json.load(stream)
        assert document["map_name"] == "meta"
        assert document["crs"] == "EPSG:32637"
        assert document["z_units"] == "m"
        print("PASS: metadata survives the task and the JSON sidecar")


if __name__ == "__main__":
    main()
