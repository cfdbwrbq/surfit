#!/usr/bin/env python3
"""Checks that every shipped Python example is a real port of its Tcl script.

Each example under ``examples/python/`` that has a Tcl original is run as its
own program, and the same original is run through tclsh in a scratch directory.
Then the data file both write is compared byte for byte.

Running the example as a program rather than importing ``build()`` is the point:
the figure in the documentation comes from ``build()``, and the file a reader
gets from ``python3 examples/python/<name>.py`` comes from ``main()``.  A port
that only works through ``build()`` would pass the figure and fail the reader.

``aniso.tcl`` and ``area_hist.tcl`` are not documented in the original manual
and have no Python port; anything else without one is a failure, so a newly
added test script cannot quietly stay uncovered.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TESTS = os.path.join(REPO, "examples", "surfit", "tests")
EXAMPLES = os.path.join(REPO, "examples", "python")
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

#: Examples whose Tcl original has a different file name.
RENAMED = {"faults": "fault"}

#: Scripts that are deliberately not ported, with the reason.
NOT_PORTED = {
    "aniso": "not documented in the original manual",
    "area_hist": "not documented in the original manual",
}


def ports():
    """(example module, tcl script, data file) for every port."""
    found = []
    for filename in sorted(os.listdir(EXAMPLES)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        module = filename[:-3]
        script = RENAMED.get(module, module)
        if os.path.isfile(os.path.join(TESTS, "%s.tcl" % script)):
            found.append((module, script, "%s.dat" % script))
    return found


def check_coverage(found):
    """Every Tcl script is either ported or listed as deliberately not."""
    problems = []
    ported = {script for _module, script, _data in found}
    for filename in sorted(os.listdir(TESTS)):
        if not filename.endswith(".tcl"):
            continue
        script = filename[:-4]
        if script in ported or script in NOT_PORTED:
            continue
        problems.append("%s.tcl has no Python port and is not in NOT_PORTED"
                        % script)
    for script in NOT_PORTED:
        if script in ported:
            problems.append("%s.tcl is listed as not ported but has a port"
                            % script)
    return problems


def run_tcl(script, directory):
    """Runs one Tcl script in a copy of the test corpus."""
    for name in os.listdir(TESTS):
        source = os.path.join(TESTS, name)
        target = os.path.join(directory, name)
        if os.path.isdir(source):
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    env = dict(os.environ, LD_LIBRARY_PATH=BIN)
    result = subprocess.run(["tclsh", os.path.join(directory, script)],
                            cwd=directory, env=env, capture_output=True)
    if result.returncode:
        raise AssertionError("tclsh exited %d:\n%s" % (
            result.returncode, result.stdout.decode(errors="replace")[-2000:]))


def run_python(module, directory):
    """Runs one example the way its docstring tells the reader to."""
    example = os.path.join(EXAMPLES, "%s.py" % module)
    result = subprocess.run([sys.executable, "-u", example], cwd=directory,
                            env=dict(os.environ, SURFIT_BIN=BIN),
                            capture_output=True)
    if result.returncode:
        raise AssertionError("python exited %d:\n%s\n%s" % (
            result.returncode,
            result.stdout.decode(errors="replace")[-2000:],
            result.stderr.decode(errors="replace")[-3000:]))


def check(module, script, data):
    """Runs both sides and compares the data file."""
    with tempfile.TemporaryDirectory() as tcl_dir, \
            tempfile.TemporaryDirectory() as python_dir:
        run_tcl("%s.tcl" % script, tcl_dir)
        run_python(module, python_dir)

        written = os.path.join(tcl_dir, data)
        produced = os.path.join(python_dir, data)
        if not os.path.isfile(written):
            raise AssertionError("tclsh wrote no %s" % data)
        if not os.path.isfile(produced):
            raise AssertionError(
                "the example wrote no %s (it wrote %s)"
                % (data, sorted(os.listdir(python_dir))))

        with open(written, "rb") as handle:
            expected = handle.read()
        with open(produced, "rb") as handle:
            actual = handle.read()
        if not expected:
            raise AssertionError("%s is empty: the save matched nothing" % data)
        if expected != actual:
            raise AssertionError("%s differs (%d vs %d bytes)"
                                 % (data, len(expected), len(actual)))
        return len(actual)


def main():
    #: The reference is the Tcl front end, so tclsh and its module have to be here.
    if shutil.which("tclsh") is None:
        raise SystemExit("tclsh is required: it is the reference front end")
    if not any(name.startswith("libtclsurfit.")
               for name in os.listdir(BIN)):
        raise SystemExit("no Tcl front end in %s; build with "
                         "-DSURFIT_BUILD_TCL=ON" % BIN)

    found = ports()
    failures = check_coverage(found)

    started = time.time()
    for module, script, data in found:
        try:
            size = check(module, script, data)
        except AssertionError as error:
            failures.append("%s: %s" % (module, error))
            print("FAIL %-18s %s" % (module, error))
        else:
            print("PASS %-18s %s, %d bytes, byte-identical to %s.tcl"
                  % (module, data, size, script))
        sys.stdout.flush()

    print("\n%d example(s), %d failed, %.1f s"
          % (len(found), len(failures), time.time() - started))
    for failure in failures:
        print("  " + failure.replace("\n", "\n  "))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
