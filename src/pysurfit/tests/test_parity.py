#!/usr/bin/env python3
"""Acceptance checks for the L1 Python bindings.

The bindings reuse the C++ API layer that the Tcl commands are generated from,
so the same gridding task must produce the same answer through both front ends.

Check 1 (parity): runs examples/surfit/tests/area.tcl through tclsh and the same
sequence through the bindings, then verifies that both produce a byte-identical
surfit data file and that surf_values() returns exactly the coefficient block
stored in that file, in row-major (count_y, count_x) order.

Check 2 (numpy in/out): registers a numpy array as a surface and reads it back.

Environment:
  SURFIT_BIN  directory holding the built packages and libraries
              (default: <repo>/../build-cpp/bin)

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

import surfit  # noqa: E402

AREAS = ["area1", "area2", "area3", "area4", "area5"]

# The coefficient block is a "coeff" tag, a NUL, a 4-byte element count, then
# the doubles.  The tag is searched for, so a version string in the header does
# not move the offsets.
COEFF_TAG = b"coeff\x00"


def core_libraries():
    """The shared libraries the Tcl module needs, next to the built package."""
    return [name for name in os.listdir(BIN) if name.endswith(".so")]


def run_tcl(workdir):
    """Runs the reference Tcl script; returns the path to its data file."""
    os.symlink(os.path.join(TESTS, "data"), os.path.join(workdir, "data"))
    for name in core_libraries():
        os.symlink(os.path.join(BIN, name), os.path.join(workdir, name))

    env = dict(os.environ, LD_LIBRARY_PATH=BIN)
    subprocess.run(["tclsh", TCL_TEST], cwd=workdir, env=env, check=True)
    return os.path.join(workdir, "area.dat")


def run_python():
    """Mirrors area.tcl through the bindings; returns the solved surface."""
    surfit.clear_data()
    surfit.set_map_name("map_area")
    surfit.set_tol(5.01187e-006)  # `set tol ...` in area.tcl

    for name in AREAS:
        assert all(surfit.area_read("data/%s.txt" % name, name)), name

    surfit.grid_get(-12, 12, 0.2, -12, 12, 0.2)

    surfit.area("10", "area1")
    surfit.area("30", "area3")
    surfit.area("undef", "area5")
    surfit.completer(1, 1.6)
    surfit.area_add(20, 0.07, "area2")
    surfit.area_add(40, 0.07, "area4")

    surfit.surfit()

    assert surfit.surf_count() == 1, surfit.surf_count()
    assert surfit.surf_names() == ["map_area"], surfit.surf_names()
    assert all(surfit.surf_save("area.dat", "map_area"))

    return surfit.values("map_area")


def coeff_from_file(path):
    """Reads the coefficient block back out of a surfit data file."""
    with open(path, "rb") as handle:
        raw = handle.read()
    tag_at = raw.find(COEFF_TAG)
    if tag_at < 0:
        raise ValueError("no coefficient block in %s" % path)
    count_at = tag_at + len(COEFF_TAG)
    count = int.from_bytes(raw[count_at:count_at + 4], "little")
    data_at = count_at + 4
    return np.frombuffer(raw, dtype="<f8", count=count, offset=data_at)


def check_parity(failures):
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
            print("OK   values() matches the stored coefficients "
                  "(%d values, %s)" % (flat.size, values.shape))
        else:
            failures.append("values() does not match the stored coefficients")

        defined = surfit.defined_mask(values)
        print("     %d/%d nodes defined, min=%.6f max=%.6f mean=%.6f" % (
            defined.sum(), values.size, values[defined].min(),
            values[defined].max(), values[defined].mean()))


def check_numpy_roundtrip(failures):
    """A numpy array must survive a trip through add_surface()/values()."""
    surfit.clear_data()

    count_x, count_y = 7, 5
    source = (np.arange(count_x * count_y, dtype="float64")
              .reshape(count_y, count_x) * 1.5)

    surfit.add_surface(source, start_x=-1.0, step_x=0.5,
                       start_y=10.0, step_y=2.0, name="trend")

    pos = surfit.surf_index("trend")
    if pos < 0:
        failures.append("add_surface() did not register the surface")
        return

    back = surfit.surf_values(pos)
    if back.shape == source.shape and np.array_equal(back, source):
        print("OK   numpy round-trip through add_surface() (%s)" % (back.shape,))
    else:
        failures.append("numpy round-trip mismatch: %s vs %s"
                        % (back.shape, source.shape))


def main():
    failures = []
    check_parity(failures)
    check_numpy_roundtrip(failures)

    if failures:
        for line in failures:
            print("FAIL " + line)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
