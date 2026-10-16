#!/usr/bin/env python3
"""Acceptance check for the L1 Python bindings.

The bindings reuse the C++ API layer that the Tcl commands are generated from,
so the same gridding task must produce the same answer through both front ends.

This script runs examples/surfit/tests/area.tcl through tclsh and the same
sequence through the pybind11 module, then verifies that

  * both produce a byte-identical surfit data file, and
  * surf_values() returns exactly the coefficient block stored in that file,
    in row-major (count_y, count_x) order.

Environment:
  SURFIT_BIN  directory holding the built libraries (default: <repo>/../build-cpp/bin)

Usage: python3 test_parity.py
"""
import os
import subprocess
import sys
import tempfile

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
BIN = os.environ.get("SURFIT_BIN", os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))
TESTS = os.path.join(REPO, "examples", "surfit", "tests")
TCL_TEST = os.path.join(TESTS, "area.tcl")

sys.path.insert(0, BIN)

import _surfit as sf  # noqa: E402

AREAS = ["area1", "area2", "area3", "area4", "area5"]

# Layout of the coefficient block in a surfit data file: the "coeff" tag, a NUL,
# a 4-byte element count, then the doubles.
COEFF_COUNT_OFFSET = 273
COEFF_DATA_OFFSET = 277


def run_tcl(workdir):
    """Runs the reference Tcl script; returns the path to its data file."""
    os.symlink(os.path.join(TESTS, "data"), os.path.join(workdir, "data"))
    for name in os.listdir(BIN):
        if name.endswith(".so"):
            os.symlink(os.path.join(BIN, name), os.path.join(workdir, name))

    env = dict(os.environ, LD_LIBRARY_PATH=BIN)
    subprocess.run(["tclsh", TCL_TEST], cwd=workdir, env=env, check=True)
    return os.path.join(workdir, "area.dat")


def run_python():
    """Mirrors area.tcl through the bindings; returns the solved surface."""
    sf.clear_data()
    sf.set_map_name("map_area")
    sf.set_tol(5.01187e-006)  # `set tol ...` in area.tcl

    for name in AREAS:
        assert all(sf.area_read("data/%s.txt" % name, name)), name

    sf.grid_get(-12, 12, 0.2, -12, 12, 0.2)

    sf.area("10", "area1")
    sf.area("30", "area3")
    sf.area("undef", "area5")
    sf.completer(1, 1.6)
    sf.area_add(20, 0.07, "area2")
    sf.area_add(40, 0.07, "area4")

    sf.surfit()

    assert sf.surf_count() == 1, sf.surf_count()
    assert sf.surf_name_at(0) == "map_area", sf.surf_name_at(0)
    assert all(sf.surf_save("area.dat", "map_area"))

    return sf.surf_values(0)


def coeff_from_file(path):
    """Reads the coefficient block back out of a surfit data file."""
    with open(path, "rb") as handle:
        raw = handle.read()
    count = int.from_bytes(raw[COEFF_COUNT_OFFSET:COEFF_DATA_OFFSET], "little")
    return np.frombuffer(raw, dtype="<f8", count=count, offset=COEFF_DATA_OFFSET)


def main():
    failures = []

    with tempfile.TemporaryDirectory() as tcl_dir, \
            tempfile.TemporaryDirectory() as py_dir:
        tcl_dat = run_tcl(tcl_dir)

        cwd = os.getcwd()
        os.chdir(py_dir)
        try:
            os.symlink(os.path.join(TESTS, "data"), "data")
            values = run_python()
            py_dat = os.path.join(py_dir, "area.dat")
        finally:
            os.chdir(cwd)

        with open(tcl_dat, "rb") as handle:
            tcl_bytes = handle.read()
        with open(py_dat, "rb") as handle:
            py_bytes = handle.read()

        if tcl_bytes == py_bytes:
            print("OK   data files are byte-identical (%d bytes)" % len(py_bytes))
        else:
            failures.append("data files differ (%d vs %d bytes)"
                            % (len(tcl_bytes), len(py_bytes)))

        flat = coeff_from_file(py_dat)
        if values.shape != (121, 121):
            failures.append("unexpected array shape %s" % (values.shape,))
        elif np.array_equal(values, flat.reshape(values.shape)):
            print("OK   surf_values() matches the stored coefficients "
                  "(%d values, %s)" % (flat.size, values.shape))
        else:
            failures.append("surf_values() does not match the stored coefficients")

        defined = ~np.isclose(values, np.finfo(np.float32).max, rtol=1e-6)
        print("     %d/%d nodes defined, min=%.6f max=%.6f mean=%.6f" % (
            defined.sum(), values.size, values[defined].min(),
            values[defined].max(), values[defined].mean()))

    if failures:
        for line in failures:
            print("FAIL " + line)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
