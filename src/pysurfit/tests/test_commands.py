"""Checks the newly bound commands against the Tcl front end.

Each case runs the same steps twice - once through tclsh with the Tcl module,
once through Python - in separate scratch directories, and compares both the
values printed and the files written. Byte equality is the only claim worth
making about a port.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DATA = os.path.join(REPO, "examples", "surfit", "tests", "data")
BIN = os.environ.get("SURFIT_BIN",
                     os.path.join(os.path.dirname(REPO), "build-cpp", "bin"))

sys.path.insert(0, BIN)

import surfit  # noqa: E402

LOAD = 'load libtclsurfit[info sharedlibextension]\nclear_data\n'


def tcl_areas():
    return LOAD + """
set names {area1 area2 area3}
foreach name $names {
    area_read "data/$name.txt" $name
}
puts "size=[area_size]"
area_save "areas.dat"
area_write "areas.txt"
area_del "area1"
puts "after_del=[area_size]"
area_invert "area2"
area_save "inverted.dat"
puts "final=[area_size]"
"""


def python_areas():
    surfit.clear_data()
    for name in ("area1", "area2", "area3"):
        surfit.area_read(os.path.join("data", "%s.txt" % name), name)
    print("size=%d" % surfit.area_size())
    surfit.area_save("areas.dat")
    surfit.area_write("areas.txt")
    surfit.area_del("area1")
    print("after_del=%d" % surfit.area_size())
    surfit.area_invert("area2")
    surfit.area_save("inverted.dat")
    print("final=%d" % surfit.area_size())


def tcl_points():
    return LOAD + """
pnts_read "data/7points.txt" "wells"
puts "size=[pnts_size]"
pnts_write "wells.txt" "wells"
pnts_save "wells.dat"
pnts_del "wells"
puts "after_del=[pnts_size]"
"""


def python_points():
    surfit.clear_data()
    surfit.pnts_read(os.path.join("data", "7points.txt"), "wells")
    print("size=%d" % surfit.pnts_size())
    surfit.pnts_write("wells.txt", "wells")
    surfit.pnts_save("wells.dat")
    surfit.pnts_del("wells")
    print("after_del=%d" % surfit.pnts_size())


def tcl_settings():
    return LOAD + """
set tol 1e-006
set sor_omega 1.4
puts "tol=$tol"
puts "omega=$sor_omega"
puts "solver=[get_current_solver_short_name]"
puts "threads_positive=[expr {[get_threads] > 0}]"
puts "types=[types_info]"
"""


def python_settings():
    surfit.clear_data()
    surfit.set_tol(1e-006)
    surfit.set_sor_omega(1.4)
    print("tol=%r" % surfit.get_tol())
    print("omega=%r" % surfit.get_sor_omega())
    print("solver=%s" % surfit.get_current_solver_short_name())
    print("threads_positive=%s" % ("1" if surfit.get_threads() > 0 else "0"))
    print("types=%s" % surfit.types_info().strip())


def tcl_surfaces():
    return LOAD + """
area_read "data/area1.txt" "area1"
grid_get -12 12 0.2 -12 12 0.2
area 10 "area1"
surfit
puts "size=[surf_size]"
surf_save "result.dat"
surf_del "*"
puts "after_del=[surf_size]"
"""


def python_surfaces():
    surfit.clear_data()
    surfit.area_read(os.path.join("data", "area1.txt"), "area1")
    surfit.grid_get(-12, 12, 0.2, -12, 12, 0.2)
    surfit.area(10, "area1")
    surfit.surfit()
    print("size=%d" % surfit.surf_size())
    surfit.surf_save("result.dat")
    surfit.surf_del("*")
    print("after_del=%d" % surfit.surf_size())


CASES = (
    ("areas", tcl_areas, python_areas, ("areas.dat", "areas.txt", "inverted.dat")),
    ("points", tcl_points, python_points, ("wells.txt", "wells.dat")),
    ("surfaces", tcl_surfaces, python_surfaces, ("result.dat",)),
    ("settings", tcl_settings, python_settings, ()),
)


def prepare(directory, scratch):
    """Gives a scratch directory the data and the libraries the script needs."""
    os.makedirs(directory, exist_ok=True)
    link = os.path.join(directory, "data")
    if not os.path.islink(link):
        os.symlink(DATA, link)
    for name in os.listdir(BIN):
        if name.endswith(".so"):
            target = os.path.join(directory, name)
            if not os.path.islink(target):
                os.symlink(os.path.join(BIN, name), target)
    del scratch


MARKERS = ("size=", "after_del=", "final=", "tol=", "omega=", "solver=",
           "threads_positive=", "types=")


def only_results(lines):
    """Keeps the lines the case prints, dropping the engine's own chatter."""
    return [line for line in lines if line.startswith(MARKERS)]


def run_tcl(script, directory):
    path = os.path.join(directory, "script.tcl")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(script)
    result = subprocess.run(
        ["tclsh", path], cwd=directory, capture_output=True,
        env=dict(os.environ, LD_LIBRARY_PATH=BIN))
    if result.returncode != 0:
        raise AssertionError("tclsh failed: %s" % result.stderr.decode()[:500])
    return result.stdout.decode().strip().splitlines()


def run_python(function, directory):
    """Runs the Python side in a subprocess, so its state starts clean."""
    runner = ("import sys\n"
              "sys.path.insert(0, %r)\n"
              "import test_commands as module\n"
              "module.%s()\n" % (HERE, function.__name__))
    result = subprocess.run(
        [sys.executable, "-c", runner], cwd=directory, capture_output=True,
        env=dict(os.environ, SURFIT_BIN=BIN))
    if result.returncode != 0:
        raise AssertionError("python failed: %s" % result.stderr.decode()[:800])
    return result.stdout.decode().strip().splitlines()


def same_value(left, right):
    """Compares one `key=value` line, numerically when both values are numbers.

    Tcl and Python print a double differently - 9.999999974752427e-7 against
    1e-06 - and the text is not what matters.
    """
    if "=" not in left or "=" not in right:
        return left == right
    left_key, _, left_value = left.partition("=")
    right_key, _, right_value = right.partition("=")
    if left_key != right_key:
        return False
    try:
        return abs(float(left_value) - float(right_value)) <= 1e-12 * max(
            1.0, abs(float(left_value)))
    except ValueError:
        return left_value == right_value


def compare(tcl_lines, python_lines, tcl_dir, python_dir, files):
    problems = []
    if len(tcl_lines) != len(python_lines) or not all(
            same_value(a, b) for a, b in zip(tcl_lines, python_lines)):
        problems.append("printed values differ:\n    tcl    %s\n    python %s"
                        % (tcl_lines, python_lines))
    for name in files:
        left = os.path.join(tcl_dir, name)
        right = os.path.join(python_dir, name)
        if not os.path.exists(left) or not os.path.exists(right):
            problems.append("%s was not written by both sides" % name)
            continue
        with open(left, "rb") as handle:
            first = handle.read()
        with open(right, "rb") as handle:
            second = handle.read()
        if first != second:
            problems.append("%s differs (%d vs %d bytes)"
                            % (name, len(first), len(second)))
    return problems


def main():
    failures = 0
    for name, tcl_case, python_case, files in CASES:
        with tempfile.TemporaryDirectory() as tcl_dir, \
                tempfile.TemporaryDirectory() as python_dir:
            prepare(tcl_dir, None)
            prepare(python_dir, None)
            try:
                tcl_lines = only_results(run_tcl(tcl_case(), tcl_dir))
                python_lines = only_results(run_python(python_case, python_dir))
                problems = compare(tcl_lines, python_lines,
                                   tcl_dir, python_dir, files)
            except AssertionError as error:
                problems = [str(error)]

        if problems:
            failures += 1
            print("FAIL %s" % name)
            for problem in problems:
                print("     %s" % problem)
        else:
            print("PASS %-10s %d value(s), %d file(s)"
                  % (name, len(tcl_lines), len(files)))

    print("\n%d case(s), %d failed" % (len(CASES), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
