"""Progress reporting must work without tqdm in captured output."""
import contextlib
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
sys.path.insert(0, BIN)

import surfit  # noqa: E402


def main():
    task = surfit.Session(map_name="progress", tol=1e-6)
    task.add_points(np.array([0.0, 1.0, 0.0, 1.0]),
                    np.array([0.0, 0.0, 1.0, 1.0]),
                    np.array([1.0, 2.0, 3.0, 4.0]), name="p")
    task.grid(0, 1, 0.25, 0, 1, 0.25)
    task.points("p")
    task.completer(1, 1.6)
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        with surfit.progress(every=0):
            task.solve()
    task.close()
    text = captured.getvalue()
    assert "-- cg" in text, text
    assert "iter" in text, text
    print("PASS: progress lines do not require tqdm")


if __name__ == "__main__":
    main()
