"""Two tasks in two threads must run at the same time and stay independent.

The engine keeps its working data in globals.  Making those globals
thread-local is what turns "two Sessions, serialized by a process-wide lock"
into "two Sessions that actually run in parallel", so this script measures both
halves of that claim:

1. two real solves in two threads produce exactly the hashes a solo process
   produces (built in the main thread and built inside the worker threads);
2. the two solves overlap in time instead of waiting for a process-wide lock;
3. a task released in one thread while another thread still had it installed
   does not crash or leak into the next task that thread runs;
4. DEMs and freeflow rules stay with their task when the tasks are solved in
   two threads.

  python3 test_threadlocal_state.py
"""

import hashlib
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
DATA = os.path.join(REPO, "examples", "surfit", "tests")
FLOW = os.path.join(REPO, "examples", "freeflow", "press1")

sys.path.insert(0, BIN)

import surfit  # noqa: E402

AREAS = ("area1", "area2", "area3", "area4", "area5")
AREA_CONFIGS = (("map_a", 10), ("map_b", 99))
FLOW_CONFIGS = (("flow_a", 16.4), ("flow_b", 32.8))
DEMS = ("dtm4", "wave")
# The two rasters differ under the same name: a shared DEM container shows up
# as one task reading the other's values.
DEM_PROBES = ((44.0, 43.0, 13.0), (3.0, 3.0, 15.0))


def digest(grid):
    return hashlib.sha256(
        np.ascontiguousarray(grid, dtype="<f8").tobytes()).hexdigest()


def build_area(map_name, first_area_value):
    """The area example, the same task test_sessions.py uses."""
    task = surfit.Session(map_name=map_name, tol=5.01187e-006)
    for name in AREAS:
        task.read_areas(os.path.join(DATA, "data", name + ".txt"), name)
    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(first_area_value, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")
    return task


def build_area_late_grid(map_name, first_area_value):
    """The area example with ``grid()`` as the last command in this thread.

    A Session is installed into another thread through its stored snapshot, so
    a command that changes the globals after the last state switch has to be
    stored too, or the grid would be missing in the other thread.
    """
    task = surfit.Session(map_name=map_name, tol=5.01187e-006)
    for name in AREAS:
        task.read_areas(os.path.join(DATA, "data", name + ".txt"), name)
    task.area(first_area_value, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")
    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    return task


def build_flow(map_name, permeability, dem):
    """The freeflow task of test_plugin_state.py, with a raster of its own."""
    task = surfit.Session(map_name=map_name, tol=5e-7)
    assert all(task.read_curves(os.path.join(FLOW, "press.xyz"), "press"))
    assert all(task.read_points(os.path.join(FLOW, "flow_point.txt"), "center"))
    task.grid(-1000, 1000, 10, -1000, 1000, 10)
    task.curve(250, "press")
    task.lcm_simple(permeability, 1, 1e-6)
    task.flow_points("center")
    if dem == "dtm4":
        assert task.dem_load_dtm(os.path.join(DATA, "data", "dtm4.hdr"),
                                 "dtm4") == [True]
        assert task.dem_setName("shared", "dtm4") == [True]
    else:
        assert task.dem_load(os.path.join(DATA, "data", "wave.dat"),
                             "wave") == [True]
        assert task.dem_setName("shared", "wave") == [True]
    return task


def solve_digest(task):
    task.solve()
    return digest(task.values())


def run_solo_area(index):
    map_name, value = AREA_CONFIGS[index]
    task = build_area(map_name, value)
    try:
        print(solve_digest(task))
    finally:
        task.close()


def run_solo_area_late_grid(index):
    map_name, value = AREA_CONFIGS[index]
    task = build_area_late_grid(map_name, value)
    try:
        print(solve_digest(task))
    finally:
        task.close()


def run_solo_flow(index):
    map_name, permeability = FLOW_CONFIGS[index]
    task = build_flow(map_name, permeability, DEMS[index])
    try:
        print(solve_digest(task))
    finally:
        task.close()


def solo_hashes(runner, count):
    """The reference result of each task, from a fresh process of its own."""
    hashes = []
    for index in range(count):
        result = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--solo",
             runner, str(index)],
            capture_output=True, check=True,
            env=dict(os.environ, SURFIT_BIN=BIN))
        hashes.append(result.stdout.decode().strip().split()[-1])
    return hashes


def test_area_parallel(solo):
    """Two area tasks, built in the main thread, solved in two threads."""
    tasks = [build_area(name, value) for name, value in AREA_CONFIGS]
    with ThreadPoolExecutor(max_workers=2) as pool:
        threaded = list(pool.map(solve_digest, tasks))
    assert threaded == solo, "two threads changed the result: %r" % (threaded,)
    # The main thread never solved these tasks; reading them back installs the
    # state the worker threads stored.
    for task, expected in zip(tasks, solo):
        assert digest(task.values()) == expected, (
            "the result did not survive the trip back to the main thread")
        task.close()
    assert surfit.Session("probe").surf_names() == []
    print("PASS: two Sessions in two threads match the solo hashes")


def build_and_solve(config):
    """One task built and solved entirely inside its own thread."""
    task = build_area(config[0], config[1])
    try:
        return solve_digest(task)
    finally:
        task.close()


def test_last_command_crosses_threads(solo):
    """A task whose last command created the grid still solves in a thread."""
    tasks = [build_area_late_grid(name, value)
             for name, value in AREA_CONFIGS]
    with ThreadPoolExecutor(max_workers=2) as pool:
        threaded = list(pool.map(solve_digest, tasks))
    for task in tasks:
        task.close()
    assert threaded == solo, (
        "the last command before the thread switch was not stored: %r"
        % (threaded,))
    print("PASS: the last command of a task crosses a thread boundary")


def test_created_in_threads(solo):
    """A Session created in a worker thread gets complete library defaults."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        threaded = list(pool.map(build_and_solve, AREA_CONFIGS))
    assert threaded == solo, (
        "a Session created in a worker thread got different defaults: %r"
        % (threaded,))
    print("PASS: Sessions created and solved in their own threads match solo")


def build_flow_and_probe(config):
    """Build a plugin task in this thread and read the DEM this task loaded."""
    (name, permeability), dem, probe = config
    task = build_flow(name, permeability, dem)
    try:
        x, y, value = probe
        return task.dem_size(), float(task.dem_getValue(x, y, "shared")[0])
    finally:
        task.close()


def test_plugin_managers_in_threads():
    """A Session created in a worker thread has the plugin managers too.

    The worker thread's library state is a copy of the defaults captured at
    import time; if that copy missed the globe/freeflow/surfit_io managers, a
    task created there could not load a DEM or a flow file at all.
    """
    configs = list(zip(FLOW_CONFIGS, DEMS, DEM_PROBES))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(build_flow_and_probe, configs))
    expected = [(1, probe[2]) for probe in DEM_PROBES]
    assert results == expected, (
        "a Session created in a worker thread missed a plugin manager: %r"
        % (results,))
    print("PASS: plugin managers are available to Sessions created in threads")


def test_release_while_installed(solo):
    """A task closed in the main thread while its solver thread keeps running.

    The worker threads stay alive between rounds, so the next round installs a
    fault state in a thread whose slot still points at the task released by the
    main thread.  Without the per-thread clearing that is a use-after-free; the
    result of the next task shows it too.
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        for round_index in range(3):
            tasks = [
                build_area("round%d_a" % round_index, 10),
                build_area("round%d_b" % round_index, 99),
            ]
            threaded = list(pool.map(solve_digest, tasks))
            assert threaded == solo, (
                "round %d changed the result: %r" % (round_index, threaded))
            for task in tasks:
                task.close()
    print("PASS: releasing a task another thread had installed is safe")


def test_dem_and_flow_parallel(solo):
    """Freeflow tasks with different rasters solve in parallel, per task."""
    tasks = [build_flow(name, permeability, dem)
             for (name, permeability), dem in zip(FLOW_CONFIGS, DEMS)]
    assert (tasks[0].dem_size(), tasks[1].dem_size()) == (1, 1)
    for task, probe in zip(tasks, DEM_PROBES):
        x, y, value = probe
        assert float(task.dem_getValue(x, y, "shared")[0]) == value

    with ThreadPoolExecutor(max_workers=2) as pool:
        threaded = list(pool.map(solve_digest, tasks))
    assert threaded == solo, (
        "freeflow tasks in two threads changed the result: %r" % (threaded,))

    # Each task still sees its own raster, not the neighbour's.
    for task, probe in zip(tasks, DEM_PROBES):
        x, y, value = probe
        assert float(task.dem_getValue(x, y, "shared")[0]) == value
    tasks[0].close()
    assert tasks[1].dem_size() == 1, "releasing a task freed another task's DEM"
    assert float(tasks[1].dem_getValue(3.0, 3.0, "shared")[0]) == 15.0
    tasks[1].close()
    assert surfit.dem_size() == 0, "a closed task left a DEM behind"
    print("PASS: DEMs and freeflow rules stay per task across threads")


def test_solves_overlap(solo):
    """Two single-worker solves in two threads really run at the same time.

    The old implementation held one process-wide lock across the state switch
    and the command, so two solves took twice as long as one.  With the lock
    replaced by one lock per Session, the process accumulates two threads' CPU
    time while both are in flight.
    """
    if (os.cpu_count() or 1) < 2:
        print("NOTE: single CPU, skipping the overlap measurement")
        return
    tasks = [build_area(name, value) for name, value in AREA_CONFIGS]
    for task in tasks:
        task._serial = True
    start_wall = time.time()
    start_cpu = time.process_time()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            threaded = list(pool.map(solve_digest, tasks))
    finally:
        for task in tasks:
            task.close()
    wall = time.time() - start_wall
    cpu = time.process_time() - start_cpu
    assert threaded == solo, "the overlap run changed the result"
    ratio = cpu / wall if wall > 0 else 0.0
    print("PASS: two solves overlap (cpu/wall = %.2f)" % ratio)
    assert ratio > 1.2, (
        "two solves did not overlap (cpu/wall = %.2f): a process-wide lock is "
        "still serializing them" % ratio)


def main():
    probe = surfit.Session("probe")
    try:
        if not hasattr(probe, "_lock"):
            raise AssertionError("Session has no per-session lock")
    finally:
        probe.close()
    if hasattr(surfit, "_STATE_LOCK"):
        raise AssertionError("the process-wide _STATE_LOCK is back")

    solo_area = solo_hashes("area", len(AREA_CONFIGS))
    solo_late = solo_hashes("late-grid", len(AREA_CONFIGS))
    solo_flow = solo_hashes("flow", len(FLOW_CONFIGS))

    test_area_parallel(solo_area)
    test_last_command_crosses_threads(solo_late)
    test_created_in_threads(solo_area)
    test_plugin_managers_in_threads()
    test_release_while_installed(solo_area)
    test_dem_and_flow_parallel(solo_flow)
    test_solves_overlap(solo_area)
    print("PASS: the engine's state is per thread")
    return 0


if __name__ == "__main__":
    if "--solo" in sys.argv:
        position = sys.argv.index("--solo")
        kind = sys.argv[position + 1]
        index = int(sys.argv[position + 2])
        if kind == "area":
            run_solo_area(index)
        elif kind == "late-grid":
            run_solo_area_late_grid(index)
        elif kind == "flow":
            run_solo_flow(index)
        else:
            raise SystemExit("unknown solo task %r" % (kind,))
        sys.exit(0)
    sys.exit(main())
