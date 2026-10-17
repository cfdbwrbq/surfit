#!/usr/bin/env python3
"""Checks that every shipped Python example is a real port of its Tcl script.

Each example under ``examples/python/`` that has a Tcl original is run as its
own program, and the same original is run through tclsh in a scratch copy of its
corpus.  Then every file both runs wrote is compared byte for byte: the native
``.dat`` files, but also the BLN and shapefile output of the format examples.

Running the example as a program rather than importing ``build()`` is the point:
the figure in the documentation comes from ``build()``, and the files a reader
gets from ``python3 examples/python/<name>.py`` come from ``main()``.  A port
that only works through ``build()`` would pass the figure and fail the reader.

A Tcl script with no port is a failure unless it is listed in ``CORPORA`` as
deliberately not ported, so a newly added script cannot quietly stay uncovered.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
EXAMPLES = os.path.join(REPO, "examples", "python")
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, HERE)

import run_tcl_suite  # noqa: E402

#: Every corpus that holds Tcl examples, with the scripts not ported and why.
CORPORA = (
    (os.path.join("examples", "surfit", "tests"), {
        "aniso": "not documented in the original manual",
        "area_hist": "not documented in the original manual",
    }),
    (os.path.join("examples", "freeflow", "press1"), {
        "press1": "a pipeline that sources the six examples and calc.tcl",
        "calc": "reports the saved results, has no data of its own",
    }),
    (os.path.join("examples", "freeflow", "press2"), {
        "press2": "a pipeline that sources the two maps and calc.tcl",
        "calc": "reports the saved results, has no data of its own",
    }),
    (os.path.join("examples", "surfit_io", "bln"), {}),
    (os.path.join("examples", "surfit_io", "shp"), {
        "cntr_shp": "needs the shapefile saver to decide the type over all "
                    "contours (known defect)",
        "const_cntr": "reads a shapefile that is not in the repository",
    }),
)

#: The example whose Tcl original has a different file name.
RENAMED = {"faults": "fault"}

#: Ports outside examples/surfit/tests: (example module, corpus, Tcl script).
EXTRA_PORTS = (
    ("press_points", os.path.join("examples", "freeflow", "press1"), "points"),
    ("flow_points", os.path.join("examples", "freeflow", "press1"), "flow_points"),
    ("flow_points2", os.path.join("examples", "freeflow", "press1"), "flow_points2"),
    ("flow_area", os.path.join("examples", "freeflow", "press1"), "flow_area"),
    ("flow_curve", os.path.join("examples", "freeflow", "press1"), "flow_curve"),
    ("flow_cntr", os.path.join("examples", "freeflow", "press1"), "flow_cntr"),
    ("map_hor_frac", os.path.join("examples", "freeflow", "press2"), "map_hor_frac"),
    ("map_ver_frac", os.path.join("examples", "freeflow", "press2"), "map_ver_frac"),
    ("area_bln", os.path.join("examples", "surfit_io", "bln"), "area_bln"),
    ("cntr_bln", os.path.join("examples", "surfit_io", "bln"), "cntr_bln"),
    ("curv_bln", os.path.join("examples", "surfit_io", "bln"), "curv_bln"),
    ("area_shp", os.path.join("examples", "surfit_io", "shp"), "area_shp"),
    ("curv_shp", os.path.join("examples", "surfit_io", "shp"), "curv_shp"),
)


def ports():
    """(example module, corpus, Tcl script) for every port."""
    tests = os.path.join("examples", "surfit", "tests")
    found = []
    for filename in sorted(os.listdir(EXAMPLES)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue
        module = filename[:-3]
        script = RENAMED.get(module, module)
        if os.path.isfile(os.path.join(REPO, tests, "%s.tcl" % script)):
            found.append((module, tests, script))
    found.extend(EXTRA_PORTS)
    return found


def check_coverage(found):
    """Every Tcl script is either ported or listed as deliberately not."""
    problems = []
    ported = {}
    for module, corpus, script in found:
        ported.setdefault(corpus, set()).add(script)
        if not os.path.isfile(os.path.join(REPO, corpus, "%s.tcl" % script)):
            problems.append("%s.py: %s/%s.tcl does not exist"
                            % (module, corpus, script))
        if not os.path.isfile(os.path.join(EXAMPLES, "%s.py" % module)):
            problems.append("%s.py is listed in EXTRA_PORTS but does not exist"
                            % module)

    for corpus, not_ported in CORPORA:
        directory = os.path.join(REPO, corpus)
        names = ported.get(corpus, set())
        for filename in sorted(os.listdir(directory)):
            if not filename.endswith(".tcl"):
                continue
            script = filename[:-4]
            if script in names or script in not_ported:
                continue
            problems.append("%s/%s.tcl has no Python port and is not in "
                            "NOT_PORTED" % (corpus, script))
        for script in not_ported:
            if script in names:
                problems.append("%s/%s.tcl is listed as not ported but has a "
                                "port" % (corpus, script))
    return problems


def run_tcl(corpus, script, directory):
    """Runs one Tcl script in a copy of its corpus."""
    source_dir = os.path.join(REPO, corpus)
    for name in os.listdir(source_dir):
        source = os.path.join(source_dir, name)
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


#: Outputs that are not data and exist on one side only.  The Tcl front end
#: writes PostScript, which run_tcl_suite already ignores; a Python example can
#: write a viewer page.  Neither says anything about the port.
ONE_SIDED = (".html",)


def produced(directory, corpus):
    """The files a side wrote, with the corpus's input copies left out."""
    found = run_tcl_suite.produced_files(directory,
                                         os.path.join(REPO, corpus))
    return {name: content for name, content in found.items()
            if not name.endswith(ONE_SIDED)}


def check(module, corpus, script):
    """Runs both sides and compares every file they wrote."""
    with tempfile.TemporaryDirectory() as tcl_dir, \
            tempfile.TemporaryDirectory() as python_dir:
        run_tcl(corpus, "%s.tcl" % script, tcl_dir)
        run_python(module, python_dir)

        expected = produced(tcl_dir, corpus)
        actual = produced(python_dir, corpus)
        if sorted(expected) != sorted(actual):
            raise AssertionError(
                "different files: tcl=%s python=%s"
                % (sorted(expected), sorted(actual)))
        if not expected:
            raise AssertionError("no files produced")
        for name in sorted(expected):
            if not expected[name]:
                raise AssertionError("%s is empty: the save matched nothing" % name)
            if expected[name] != actual[name]:
                raise AssertionError(
                    "%s differs (%d vs %d bytes)"
                    % (name, len(expected[name]), len(actual[name])))
        return len(expected), sum(len(content) for content in expected.values())


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
    for module, corpus, script in found:
        try:
            files, size = check(module, corpus, script)
        except AssertionError as error:
            failures.append("%s: %s" % (module, error))
            print("FAIL %-18s %s" % (module, error))
        else:
            print("PASS %-18s %d file(s), %d bytes, byte-identical to %s/%s.tcl"
                  % (module, files, size, corpus, script))
        sys.stdout.flush()

    print("\n%d example(s), %d failed, %.1f s"
          % (len(found), len(failures), time.time() - started))
    for failure in failures:
        print("  " + failure.replace("\n", "\n  "))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
