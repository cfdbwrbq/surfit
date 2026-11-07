"""Opt-in strict rules turn an empty match into an error.

The default stays compatible with Tcl: a missing area name returns ``[]`` and
the rule is not added.  ``Session(..., strict=True)`` refuses that silent no-op
and names the rule.

  python3 test_strict.py
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
    with tempfile.TemporaryDirectory() as directory:
        area = os.path.join(directory, "area.txt")
        with open(area, "w", encoding="ascii") as stream:
            stream.write("0 0\n1 0\n1 1\n0 1\n0 0\n")
        task = surfit.Session(map_name="strict", tol=1e-9, strict=True)
        assert all(task.read_areas(area, "known"))
        task.grid(0, 1, 1, 0, 1, 1)
        assert task.area_leq(1, "known") == [True]
        try:
            task.area_geq(0, "missing")
        except ValueError as error:
            assert "area_geq" in str(error)
        else:
            raise AssertionError("strict mode accepted an empty match")
    print("PASS: strict mode rejects an empty rule match")


if __name__ == "__main__":
    main()
