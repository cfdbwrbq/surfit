"""Dip/azimuth points constrain local derivatives.

  python3 test_gradient.py
"""

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
    n = 5
    x = []
    y = []
    for i in range(n):
        for j in range(n):
            x.append(i / (n - 1))
            y.append(j / (n - 1))
    task = surfit.Session(map_name="gradient", tol=1e-9)
    task.add_dip_points(x, y, [30.0] * len(x), [0.0] * len(x), name="dip")
    task.grid(0, 1, 0.2, 0, 1, 0.2)
    task.gradient("dip")
    task.completer(1, 1.6)
    task.solve()
    values = task.values()
    step = 1.0 / (values.shape[0] - 1)
    slope = np.diff(values, axis=0) / step
    assert abs(float(np.nanmedian(slope)) - np.tan(np.deg2rad(30.0))) < 0.08
    assert task.rule_report()["rules"][0]["name"] == "f_gradient"
    task.close()
    print("PASS: dip/azimuth gradient constraints")


if __name__ == "__main__":
    main()
