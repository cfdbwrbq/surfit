"""Two tasks in one process must give exactly the results they give alone.

Interleaved solves are compared byte for byte against the same task run by
itself in a fresh process, so "independent" is measured, not assumed.

  python3 test_sessions.py
"""

import hashlib
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
DATA = os.path.join(REPO, "examples", "surfit", "tests", "data")
AREAS = ("area1", "area2", "area3", "area4", "area5")

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def build(map_name, first_area_value):
    """One task: the area example with a different value for area1."""
    task = surfit.Session(map_name=map_name, tol=5.01187e-006)
    for name in AREAS:
        task.read_areas(os.path.join(DATA, "%s.txt" % name), name)
    task.grid(-12, 12, 0.2, -12, 12, 0.2)
    task.area(first_area_value, "area1")
    task.area(30, "area3")
    task.area("undef", "area5")
    task.completer(1, 1.6)
    task.area_add(20, 0.07, "area2")
    task.area_add(40, 0.07, "area4")
    return task


CONFIGS = (("map_a", 10), ("map_b", 99))


def digest(grid):
    return hashlib.sha256(np.ascontiguousarray(grid, dtype="<f8").tobytes()).hexdigest()


def run_solo(index):
    """Solves one task alone and prints the digest of its grid."""
    map_name, value = CONFIGS[index]
    task = build(map_name, value)
    task.solve()
    print(digest(task.values()))


def main():
    # Solo runs, one per process, as the reference.
    solo = []
    for index in range(len(CONFIGS)):
        result = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "--solo", str(index)],
            capture_output=True, check=True,
            env=dict(os.environ, SURFIT_BIN=BIN))
        solo.append(result.stdout.decode().strip().split()[-1])

    # Both at once, interleaved, in this process.
    tasks = [build(name, value) for name, value in CONFIGS]
    tasks[0].solve()
    tasks[1].solve()
    interleaved = [digest(task.values()) for task in tasks]

    # And again with the solves alternating in smaller pieces.
    tasks = [build(name, value) for name, value in CONFIGS]
    for task in tasks:
        task.solve()
    again = [digest(task.values()) for task in tasks]

    print("solo        :", solo)
    print("interleaved :", interleaved)
    print("repeated    :", again)

    assert interleaved == solo, "interleaving changed the result"
    assert again == solo, "a repeated run changed the result"
    assert solo[0] != solo[1], "the two tasks produced the same grid"
    print("PASS: each task keeps its own result")

    # A task has to survive the comings and goings of others; releasing a state
    # is the part most likely to free something still in use.
    keeper = build("keeper", 10)
    keeper.solve()
    expected = digest(keeper.values())
    for _ in range(5):
        extra = build("extra", 99)
        extra.solve()
        del extra
    assert digest(keeper.values()) == expected, "a neighbour's lifetime changed it"
    keeper.close()
    assert surfit.Session("fresh").surf_names() == [], "a closed state left data"
    print("PASS: creating and releasing other tasks changed nothing")
    return 0


if __name__ == "__main__":
    if "--solo" in sys.argv:
        run_solo(int(sys.argv[sys.argv.index("--solo") + 1]))
        sys.exit(0)
    sys.exit(main())
