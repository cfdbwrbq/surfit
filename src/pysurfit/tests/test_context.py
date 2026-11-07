"""Each task owns its manager list, not only its data containers.

``grid_auto`` and ``clear_data`` go through the data_manager.  Two live tasks
must not clear or auto-size through each other's manager.

  python3 test_context.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
DATA = os.path.join(REPO, "examples", "surfit", "tests", "data")

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def build(name):
    task = surfit.Session(map_name=name, tol=1e-6)
    for index in range(1, 6):
        assert all(task.read_areas(
            os.path.join(DATA, "area%d.txt" % index), "area%d" % index))
    task.grid_auto()
    task.area(10, "area1")
    task.completer(1, 1.6)
    return task


def main():
    first = build("first")
    second = build("second")
    assert first.area_size() == 5
    assert second.area_size() == 5

    first.clear_data()
    assert first.area_size() == 0
    assert second.area_size() == 5, "clear_data crossed the session boundary"

    second.solve()
    assert "second" in second.names()
    assert second.values().shape[0] > 1
    print("PASS: data managers are per session")


if __name__ == "__main__":
    main()
