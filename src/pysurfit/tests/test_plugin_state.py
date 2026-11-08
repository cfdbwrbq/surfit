"""The globe and freeflow plugins keep their state per task.

The engine cannot own the plugins' state -- the plugins depend on the engine,
not the other way round -- so each plugin hands out per-task handles that a
Session creates, installs before its calls and releases with it.  This test
drives those handles directly, then checks the real thing: two Sessions with
different DEMs under one name and different flow rules must each produce the
result they produce alone.

  python3 test_plugin_state.py
"""

import hashlib
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
DATA = os.path.join(REPO, "examples", "surfit", "tests", "data")
FLOW = os.path.join(REPO, "examples", "freeflow", "press1")

sys.path.insert(0, BIN)

import surfit  # noqa: E402
from surfit import _surfit as _core  # noqa: E402


CONFIGS = (("flow_a", 16.4), ("flow_b", 32.8))
DEMS = ("dtm4", "wave")
# The two rasters differ under the same name, so a shared container shows up
# as one task reading the other's values.
DEM_PROBES = ((44.0, 43.0, 13.0), (3.0, 3.0, 15.0))


def digest(grid):
    return hashlib.sha256(
        np.ascontiguousarray(grid, dtype="<f8").tobytes()).hexdigest()


def build(map_name, permeability, dem):
    """One flow task, optionally with its own raster under the name "shared"."""
    task = surfit.Session(map_name=map_name, tol=5e-7)
    assert all(task.read_curves(os.path.join(FLOW, "press.xyz"), "press"))
    assert all(task.read_points(os.path.join(FLOW, "flow_point.txt"),
                                "center"))
    task.grid(-1000, 1000, 10, -1000, 1000, 10)
    task.curve(250, "press")
    task.lcm_simple(permeability, 1, 1e-6)
    task.flow_points("center")
    if dem == "dtm4":
        assert task.dem_load_dtm(os.path.join(DATA, "dtm4.hdr"), "dtm4") == [True]
        assert task.dem_setName("shared", "dtm4") == [True]
    elif dem == "wave":
        assert task.dem_load(os.path.join(DATA, "wave.dat"), "wave") == [True]
        assert task.dem_setName("shared", "wave") == [True]
    return task


def run_solo(index):
    """Solves one task alone, in its own process."""
    map_name, permeability = CONFIGS[index]
    task = build(map_name, permeability, DEMS[index])
    task.solve()
    print(digest(task.values()))


def raw_containers():
    """The container layer behind the context, driven the way a host does."""
    origin = _core.globe_dems_origin()
    assert origin == _core.globe_dems_origin(), "the library's container changed"
    first = _core.globe_dems_create()
    second = _core.globe_dems_create()
    assert first not in (0, origin) and second not in (0, origin)
    assert first != second

    _core.globe_dems_install(first)
    assert surfit.dem_load_dtm(os.path.join(DATA, "dtm4.hdr"), "dtm4") == [True]
    assert surfit.dem_size() == 1

    _core.globe_dems_install(second)
    assert surfit.dem_size() == 0, "a DEM leaked into the other container"
    assert surfit.dem_load(os.path.join(DATA, "wave.dat"), "wave") == [True]

    # Freeing one task's container while a neighbour is installed must not
    # touch the neighbour's DEM.
    _core.globe_dems_release(first)
    assert surfit.dem_size() == 1
    assert float(surfit.dem_getValue(3.0, 3.0, "wave")[0]) == 15.0

    # The library's own container belongs to the library, not to the caller.
    _core.globe_dems_install(origin)
    _core.globe_dems_release(origin)
    assert surfit.dem_size() == 0
    assert _core.globe_dems_origin() == origin

    # Releasing the installed container restores the library's own.
    _core.globe_dems_install(second)
    assert surfit.dem_size() == 1
    _core.globe_dems_release(second)
    assert surfit.dem_size() == 0
    assert _core.globe_dems_origin() == origin
    print("PASS: DEM containers belong to the task that creates them")


def main():
    raw_containers()

    solo = []
    for index in range(len(CONFIGS)):
        result = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--solo", str(index)],
            capture_output=True, check=True,
            env=dict(os.environ, SURFIT_BIN=BIN))
        solo.append(result.stdout.decode().strip().split()[-1])

    # Two tasks: different flow rules, and different rasters under one name.
    tasks = [build(name, permeability, dem)
             for (name, permeability), dem in zip(CONFIGS, DEMS)]
    assert (tasks[0].dem_size(), tasks[1].dem_size()) == (1, 1), "a DEM leaked"
    for task, probe in zip(tasks, DEM_PROBES):
        x, y, value = probe
        assert float(task.dem_getValue(x, y, "shared")[0]) == value

    tasks[0].solve()
    tasks[1].solve()
    interleaved = [digest(task.values()) for task in tasks]
    print("solo        :", solo)
    print("interleaved :", interleaved)
    assert interleaved == solo, "the flow rules of two tasks mixed"
    assert solo[0] != solo[1], "the two tasks produced the same grid"

    # The DEMs belong to the task that loaded them and survive a neighbour.
    for task, probe in zip(tasks, DEM_PROBES):
        x, y, value = probe
        assert float(task.dem_getValue(x, y, "shared")[0]) == value
    tasks[0].close()
    assert tasks[1].dem_size() == 1, "releasing a task freed another task's DEM"
    assert float(tasks[1].dem_getValue(3.0, 3.0, "shared")[0]) == 15.0
    assert digest(tasks[1].values()) == interleaved[1], "a neighbour changed it"
    tasks[1].close()

    # A task built after its neighbours are gone must still give the solo
    # result, including the raster it loads itself.
    fresh = build(CONFIGS[0][0], CONFIGS[0][1], DEMS[0])
    fresh.solve()
    assert digest(fresh.values()) == solo[0], "a stale task state leaked"
    fresh.close()
    assert surfit.dem_size() == 0, "a closed task left a DEM behind"
    assert surfit.Session("fresh").surf_names() == [], "a closed state left data"
    print("PASS: globe and freeflow state stay per task")
    return 0


if __name__ == "__main__":
    if "--solo" in sys.argv:
        run_solo(int(sys.argv[sys.argv.index("--solo") + 1]))
        sys.exit(0)
    sys.exit(main())
