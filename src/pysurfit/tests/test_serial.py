"""Temporary serial-pool mode for sstuff.

``Session(serial=True)`` forces the process-wide internal pool to one worker
for the solve and restores the previous size.  This is a safety valve until
sstuff gets a real per-session context; it is not parallel execution.

  python3 test_serial.py
"""

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
    previous = surfit.get_threads()
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "points.txt")
        with open(path, "w", encoding="ascii") as stream:
            stream.write("0.01 0.01 0\n0.02 0.02 10\n")
        task = surfit.Session(map_name="serial", tol=1e-9, serial=True)
        assert all(task.read_points(path, "p"))
        task.grid(0, 1, 1, 0, 1, 1)
        task.points("p")
        task.solve()
        assert surfit.get_threads() == previous, "pool size was not restored"

    with surfit.serial_threads():
        assert surfit.get_threads() == 1
    assert surfit.get_threads() == previous, "context manager did not restore"

    print("PASS: serial pool mode restores the pool")


if __name__ == "__main__":
    main()
