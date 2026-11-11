"""Benchmark helper returns direct/sequential/parallel timings.

The assertion is structural; wall-clock speed is not a CI criterion.

  python3 test_benchmark.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402


def layer(value):
    task = surfit.Session(map_name="bench", tol=1e-7)
    assert all(task.add_points([0, 1, 0, 1], [0, 0, 1, 1],
                               [value] * 4, name="p"))
    task.grid(0, 1, 0.5, 0, 1, 0.5)
    task.points("p")
    task.completer(1, 1.6)
    return task


def main():
    result = surfit.benchmark_stack(
        {"one": lambda: layer(1.0), "two": lambda: layer(2.0)},
        repeats=1, workers=2)
    for mode in ("direct", "sequential", "parallel"):
        assert len(result[mode]["seconds"]) == 1
        assert result[mode]["median"] >= 0.0
    assert "speedup_parallel" in result
    print("PASS: stack benchmark summary")


if __name__ == "__main__":
    main()
