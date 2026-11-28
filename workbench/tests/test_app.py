"""Small end-to-end check for the studio API."""
import os
import sys
import tempfile
import time
import zipfile

import shapefile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import backend.app as app

POINTS = "0 0 1\n1 0 2\n0 1 3\n1 1 4\n0.5 0.5 2.5\n"
FAULTS = "0.5 0 10\n0.5 1 10\n"
TWO_COLUMN_FAULTS = "0.5 0\n0.5 1\n"
CONTOURS = "0.2 0.5 10 1\n0.8 0.5 10 1\n0.5 0.2 12 2\n0.5 0.8 12 2\n"


def main():
    client = TestClient(app.app)
    assert client.get("/api/health").json()["ok"]
    preview = client.post(
        "/api/preview",
        files={"points": ("points.geojson",
                          open("examples/points.geojson", "rb").read(),
                          "application/geo+json"),
               "faults": ("faults.geojson",
                          open("examples/faults.geojson", "rb").read(),
                          "application/geo+json"),
               "contours": ("contours.geojson",
                            open("examples/contours.geojson", "rb").read(),
                            "application/geo+json")},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["counts"] == {"points": 8, "faults": 1, "contours": 2, "areas": 0, "surfaces": 0}
    two_column = client.post(
        "/api/preview",
        files={"points": ("points.csv", POINTS, "text/plain"),
               "faults": ("faults.txt", TWO_COLUMN_FAULTS, "text/plain")},
    )
    assert two_column.status_code == 200, two_column.text
    assert two_column.json()["counts"]["faults"] == 1
    response = client.post(
        "/api/jobs",
        files={"points": ("points.csv", POINTS, "text/plain"),
               "faults": ("faults.csv", FAULTS, "text/plain"),
               "contours": ("contours.csv", CONTOURS, "text/plain")},
        data={"cell_size": "0.1", "tol": "1e-6", "solver": "cg",
              "d1": "1", "d2": "1.6"},
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["id"]
    for _ in range(60):
        state = client.get("/api/jobs/%s" % job_id).json()
        if state["status"] in ("done", "error"):
            break
        time.sleep(0.2)
    assert state["status"] == "done", state
    assert state["metrics"]["faults"] == 1
    assert state["solver"] == "cg"
    assert state["iteration"] > 0
    assert state["phase"] > 0
    assert state["phase_count"] > 0
    assert state["metrics"]["contours"] == 2
    mesh = client.get("/api/jobs/%s/mesh" % job_id).json()
    assert len(mesh["vertices"]) > 0
    assert len(mesh["faces"]) > 0
    assert mesh["undefined"] == 0
    assert "extent" in mesh
    dat = client.get("/api/jobs/%s/download.dat" % job_id)
    assert dat.status_code == 200

    with tempfile.TemporaryDirectory() as directory:
        base = os.path.join(directory, "fields")
        writer = shapefile.Writer(base)
        writer.field("east", "N", 10, 2)
        writer.field("north", "N", 10, 2)
        writer.field("elev", "N", 10, 2)
        for east, north, elev in ((10, 20, 100), (11, 21, 101), (12, 22, 102)):
            writer.point(0, 0)
            writer.record(east, north, elev)
        writer.close()
        archive_path = os.path.join(directory, "fields.zip")
        with zipfile.ZipFile(archive_path, "w") as bundle:
            for suffix in (".shp", ".shx", ".dbf"):
                bundle.write(base + suffix, "fields" + suffix)
        shp_raw = open(archive_path, "rb").read()
    filtered = client.post(
        "/api/preview",
        files={"points": ("filter.csv", "0 0 0\n1 0 1\n2 0 2\n", "text/plain")},
        data={"exclude_zero": "true"},
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["points"] == [[1.0, 0.0, 1.0], [2.0, 0.0, 2.0]]
    filtered = client.post(
        "/api/preview",
        files={"points": ("filter.csv", "0 0 0\n1 0 1\n2 0 2\n", "text/plain")},
        data={"min_value": "1", "max_value": "1"},
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["points"] == [[1.0, 0.0, 1.0]]

    shp_schema = client.post(
        "/api/schema",
        files={"points": ("fields.zip", shp_raw, "application/zip")},
    )
    assert shp_schema.status_code == 200, shp_schema.text
    assert shp_schema.json()["points"] == ["east", "elev", "north"]

    shp_preview = client.post(
        "/api/preview",
        files={"points": ("fields.zip", shp_raw, "application/zip")},
        data={"x_field": "east", "y_field": "north", "z_field": "elev"},
    )
    assert shp_preview.status_code == 200, shp_preview.text
    assert shp_preview.json()["points"] == [[10.0, 20.0, 100.0],
                                            [11.0, 21.0, 101.0],
                                            [12.0, 22.0, 102.0]]

    auto = client.post(
        "/api/jobs",
        files={"points": ("auto.csv",
                          "0 0 1\n1 0 2\n0 1 3\n1 1 4\n0.5 0.5 2.5\n",
                          "text/plain")},
        data={"cell_size_auto": "true", "solver": "cg"},
    )
    assert auto.status_code == 200, auto.text
    auto_id = auto.json()["id"]
    for _ in range(120):
        auto_state = client.get("/api/jobs/%s" % auto_id).json()
        if auto_state["status"] in ("done", "error"):
            break
        time.sleep(0.25)
    assert auto_state["status"] == "done", auto_state
    assert auto_state["metrics"]["auto_cell"] is True
    assert auto_state["metrics"]["grid"] == [201, 201]

    area = client.post(
        "/api/jobs",
        files={
            "points": ("auto.csv",
                       "0 0 1\n1 0 2\n0 1 3\n1 1 4\n0.5 0.5 2.5\n",
                       "text/plain"),
            "areas": ("area.geojson",
                      open("examples/area.geojson", "rb").read(),
                      "application/geo+json"),
        },
        data={"cell_size": "0.1", "solver": "cg",
              "area_rules": '[{"mode": "constant", "value": 10}]'},
    )
    assert area.status_code == 200, area.text
    area_id = area.json()["id"]
    for _ in range(80):
        area_state = client.get("/api/jobs/%s" % area_id).json()
        if area_state["status"] in ("done", "error"):
            break
        time.sleep(0.2)
    assert area_state["status"] == "done", area_state
    assert area_state["metrics"]["areas"] == 1

    surface = client.post(
        "/api/jobs",
        files={
            "points": ("surface.csv",
                       "0 0 1\n1 0 2\n0 1 3\n1 1 4\n0.5 0.5 2.5\n",
                       "text/plain"),
            "surfaces": ("func.func",
                         open("examples/func.func", "rb").read(),
                         "application/octet-stream"),
        },
        data={"cell_size": "1", "solver": "cg",
              "global_rules": '[{"mode": "mean", "value": 2.5}]'},
    )
    assert surface.status_code == 200, surface.text
    surface_id = surface.json()["id"]
    for _ in range(120):
        surface_state = client.get("/api/jobs/%s" % surface_id).json()
        if surface_state["status"] in ("done", "error"):
            break
        time.sleep(0.2)
    assert surface_state["status"] == "done", surface_state
    assert surface_state["metrics"]["surfaces"] == 1
    assert any(rule["name"] == "f_mean"
               for rule in surface_state["metrics"]["rule_report"]["rules"])

    project = client.post(
        "/api/projects",
        files={"points": ("points.geojson",
                          open("examples/points.geojson", "rb").read(),
                          "application/geo+json"),
               "faults": ("faults.geojson",
                          open("examples/faults.geojson", "rb").read(),
                          "application/geo+json"),
               "contours": ("contours.geojson",
                            open("examples/contours.geojson", "rb").read(),
                            "application/geo+json")},
        data={"name": "Test project", "job_id": job_id, "cell_size": "1",
              "solver": "cg"},
    )
    assert project.status_code == 200, project.text
    project_data = project.json()
    assert project_data["has_result"]
    assert project_data["sources"][0]["url"].endswith("/sources/points/0")
    assert client.get(project_data["sources"][0]["url"]).status_code == 200
    assert client.get("/api/projects/%s/mesh" % project_data["id"]).status_code == 200
    assert client.get("/api/projects/%s/metrics" % project_data["id"]).status_code == 200
    assert client.get("/api/projects").json()["projects"]
    archive = client.get("/api/projects/%s/archive" % project_data["id"])
    assert archive.status_code == 200
    imported = client.post("/api/projects/import",
                           files={"archive": ("project.zip", archive.content, "application/zip")})
    assert imported.status_code == 200, imported.text
    imported_data = imported.json()
    assert imported_data["has_result"]
    assert imported_data["sources"][0]["url"].endswith("/sources/points/0")
    assert client.delete("/api/projects/%s" % imported_data["id"]).status_code == 200
    assert client.delete("/api/projects/%s" % project_data["id"]).status_code == 200

    geo = client.post(
        "/api/jobs",
        files={
            "points": ("points.geojson",
                       open("examples/points.geojson", "rb").read(),
                       "application/geo+json"),
            "faults": ("faults.geojson",
                       open("examples/faults.geojson", "rb").read(),
                       "application/geo+json"),
            "contours": ("contours.geojson",
                         open("examples/contours.geojson", "rb").read(),
                         "application/geo+json"),
        },
        data={"cell_size": "1", "solver": "cg"},
    )
    assert geo.status_code == 200, geo.text
    geo_id = geo.json()["id"]
    for _ in range(60):
        geo_state = client.get("/api/jobs/%s" % geo_id).json()
        if geo_state["status"] in ("done", "error"):
            break
        time.sleep(0.2)
    assert geo_state["status"] == "done", geo_state
    assert geo_state["metrics"]["contours"] == 2

    contour_only = client.post(
        "/api/jobs",
        files={"contours": ("contours.geojson",
                            open("examples/contours.geojson", "rb").read(),
                            "application/geo+json")},
        data={"cell_size": "1", "solver": "cg"},
    )
    assert contour_only.status_code == 200, contour_only.text
    contour_id = contour_only.json()["id"]
    for _ in range(60):
        contour_state = client.get("/api/jobs/%s" % contour_id).json()
        if contour_state["status"] in ("done", "error"):
            break
        time.sleep(0.2)
    assert contour_state["status"] == "done", contour_state
    assert contour_state["metrics"]["points"] == 0
    assert contour_state["metrics"]["contours"] == 2
    print("PASS: studio job, mesh, .dat, GeoJSON and contour-only")


if __name__ == "__main__":
    main()
