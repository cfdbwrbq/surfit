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


def tcl_surf_debit():
    return LOAD + """
load libfreeflow[info sharedlibextension]
set map_name "map"
grid_get -12 12 1 -12 12 1
pnts_read "data/7points.txt" "wells"
points "wells"
surfit
set undef_value -12345
puts "debit=[lindex [surf_debit 500 500 1 1 1 map] 0]"
puts "rect=[lindex [surf_debit_rect 500 500 600 600 1 1 1 map] 0]"
"""


def python_surf_debit():
    surfit.clear_data()
    surfit.set_map_name("map")
    surfit.grid_get(-12, 12, 1, -12, 12, 1)
    surfit.pnts_read(os.path.join("data", "7points.txt"), "wells")
    surfit.points("wells")
    surfit.surfit()
    surfit.set_undef_value(-12345.0)
    debit = surfit.surf_debit(500.0, 500.0, 1.0, 1.0, 1.0, "map")
    rect = surfit.surf_debit_rect(500.0, 500.0, 600.0, 600.0,
                                  1.0, 1.0, 1.0, "map")
    print("debit=%g" % debit[0])
    print("rect=%g" % rect[0])
    # Both functions answer the configured undef_value outside the grid; the
    # rectangle used to answer FLT_MAX regardless of the setting.
    assert debit[0] == -12345.0, debit
    assert rect[0] == -12345.0, rect


def tcl_dem_wave():
    return LOAD + """
load libglobe[info sharedlibextension]
dem_load "data/wave.dat" "wave"
dem_decomp "wave"
dem_recons "wave"
puts "wave_level=[lindex [dem_get_details_level wave] 0]"
puts "wave_value=[lindex [dem_getValue 1 1 wave] 0]"
"""


def python_dem_wave():
    surfit.clear_data()
    assert surfit.dem_load(os.path.join("data", "wave.dat"), "wave") == [True]
    before = [surfit.dem_getValue(float(x), float(y), "wave")[0]
              for y in range(4) for x in range(4)]
    assert before == [float(v) for v in range(16)], before
    assert surfit.dem_decomp("wave") == [True]
    assert surfit.dem_recons("wave") == [True]
    after = [surfit.dem_getValue(float(x), float(y), "wave")[0]
             for y in range(4) for x in range(4)]
    # The first dem_recons() used to be a no-op: it stayed on the coarse level.
    assert after == before, after
    # full_recons must report success after it has returned to the original.
    assert surfit.dem_decomp("wave") == [True]
    assert surfit.dem_full_recons("wave") == [True]
    assert [surfit.dem_getValue(float(x), float(y), "wave")[0]
            for y in range(4) for x in range(4)] == before
    print("wave_level=%d" % surfit.dem_get_details_level("wave")[0])
    print("wave_value=%g" % surfit.dem_getValue(1.0, 1.0, "wave")[0])


def tcl_dem_zip():
    return LOAD + """
load libglobe[info sharedlibextension]
dem_load_hgt_zip "data/N00E006.hgt.zip"
puts "dems=[dem_size]"
puts "dem_x=[lindex [dem_getCountX N00E006] 0]"
puts "dem_y=[lindex [dem_getCountY N00E006] 0]"
puts "dem_minz=[lindex [dem_minz] 0]"
puts "dem_maxz=[lindex [dem_maxz] 0]"
"""


def python_dem_zip():
    surfit.clear_data()
    result = surfit.dem_load_hgt_zip(
        os.path.join("data", "N00E006.hgt.zip"))
    assert result == [True], result
    print("dems=%d" % surfit.dem_size())
    print("dem_x=%d" % surfit.dem_getCountX("N00E006")[0])
    print("dem_y=%d" % surfit.dem_getCountY("N00E006")[0])
    print("dem_minz=%g" % surfit.dem_minz()[0])
    print("dem_maxz=%g" % surfit.dem_maxz()[0])
    assert surfit.dem_getCountX("N00E006")[0] == 1201
    assert surfit.dem_getCountY("N00E006")[0] == 1201
    assert surfit.dem_minz()[0] == -50.0
    assert surfit.dem_maxz()[0] == 100.0


def tcl_pnts_to_cntrs():
    return LOAD + """
pnts_read "data/7points.txt" "wells"
puts "converted=[lindex [pnts_to_cntrs "wells"] 0]"
puts "cntrs=[cntr_size]"
"""


def python_pnts_to_cntrs():
    surfit.clear_data()
    surfit.pnts_read(os.path.join("data", "7points.txt"), "wells")
    result = surfit.pnts_to_cntrs("wells")
    assert result == [True], result
    print("converted=%d" % int(result == [True]))
    print("cntrs=%d" % surfit.cntr_size())
    assert surfit.cntr_size() > 0
    assert surfit.pnts_to_cntrs("nosuch") in (None, [])


def tcl_minmax():
    return LOAD + """
pnts_read "data/minmax.txt" "mm"
puts "minz=[pnts_minz]"
puts "maxz=[pnts_maxz]"
"""


def python_minmax():
    surfit.clear_data()
    surfit.pnts_read(os.path.join("data", "minmax.txt"), "mm")
    print("minz=%g" % surfit.pnts_minz())
    print("maxz=%g" % surfit.pnts_maxz())
    # The first z is the minimum; a reduction that starts at begin+1 misses it.
    assert surfit.pnts_minz() == -100.0, surfit.pnts_minz()
    assert surfit.pnts_maxz() == 20.0, surfit.pnts_maxz()


def tcl_hist_datafile():
    return LOAD + """
pnts_read "data/points.txt" "wells"
hist_from_pnts "wells" 8 0 1 "h1"
hist_from_pnts "wells" 4 -1 1 "h2"
file_save "task.dat"
clear_data
puts "empty=[hist_size]"
file_load "task.dat"
puts "size=[hist_size]"
puts "names=[join [lsort [hist_getName]] ,]"
"""


def python_hist_datafile():
    surfit.clear_data()
    surfit.pnts_read(os.path.join("data", "points.txt"), "wells")
    surfit.hist_from_pnts("wells", 8, 0.0, 1.0, "h1")
    surfit.hist_from_pnts("wells", 4, -1.0, 1.0, "h2")
    for name in ("h1", "h2"):
        assert surfit.hist_write("before_%s.txt" % name, name, 3) == [True]
    assert surfit.file_save("task.dat") is True
    surfit.clear_data()
    print("empty=%d" % surfit.hist_size())
    surfit.file_load("task.dat")
    print("size=%d" % surfit.hist_size())
    names = sorted(surfit.hist_getName())
    print("names=%s" % ",".join(names))
    assert names == ["h1", "h2"], names
    for name in ("h1", "h2"):
        assert surfit.hist_write("after_%s.txt" % name, name, 3) == [True]
        before = open("before_%s.txt" % name, encoding="utf-8").read()
        after = open("after_%s.txt" % name, encoding="utf-8").read()
        assert before == after, "histogram %s changed in the task file" % name


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


def tcl_surf_math():
    return LOAD + """
set map_name "s"
area_read "data/area1.txt" "area1"
grid_get -12 12 0.2 -12 12 0.2
area 10 "area1"
surfit
puts "minz=[lindex [surf_minz $map_name] 0]"
puts "maxz=[lindex [surf_maxz $map_name] 0]"
puts "sum=[lindex [surf_sum $map_name] 0]"
puts "cells=[lindex [surf_cells_in_area "area1" $map_name] 0]"
surf_mult_value 2 "$map_name"
puts "doubled=[lindex [surf_maxz $map_name] 0]"
surf_save "math.dat" "$map_name"
surf_plus_value_area 5 "$map_name" "area1"
surf_save "plus.dat" "$map_name"
puts "after_plus=[lindex [surf_minz $map_name] 0]"
"""


def python_surf_math():
    surfit.clear_data()
    surfit.set_map_name("s")
    surfit.area_read(os.path.join("data", "area1.txt"), "area1")
    surfit.grid_get(-12, 12, 0.2, -12, 12, 0.2)
    surfit.area(10, "area1")
    surfit.surfit()
    print("minz=%r" % float(surfit.surf_minz("s")[0]))
    print("maxz=%r" % float(surfit.surf_maxz("s")[0]))
    print("sum=%r" % float(surfit.surf_sum("s")[0]))
    print("cells=%r" % float(surfit.surf_cells_in_area("area1", "s")[0]))
    surfit.surf_mult_value(2, "s")
    print("doubled=%r" % float(surfit.surf_maxz("s")[0]))
    surfit.surf_save("math.dat", "s")
    surfit.surf_plus_value_area(5, "s", "area1")
    surfit.surf_save("plus.dat", "s")
    print("after_plus=%r" % float(surfit.surf_minz("s")[0]))


def tcl_pnts_math():
    return LOAD + """
pnts_read "data/7points.txt" "wells"
puts "minx=[lindex [pnts_minx "wells"] 0]"
puts "maxz=[lindex [pnts_maxz "wells"] 0]"
pnts_plus_real 1 "wells"
puts "shifted=[lindex [pnts_maxz "wells"] 0]"
pnts_write "shifted.txt" "wells"
pnts_rotate 0 0 90 "wells"
pnts_write "rotated.txt" "wells"
puts "rotated_minx=[lindex [pnts_minx "wells"] 0]"
mask_from_surf "nosuchsrf"
puts "mask_size=[mask_size]"
grid_get_for_pnts 50 50 "wells" "from_pnts"
puts "grid_check=[grid_check]"
"""


def python_pnts_math():
    surfit.clear_data()
    surfit.pnts_read(os.path.join("data", "7points.txt"), "wells")
    print("minx=%r" % float(surfit.pnts_minx("wells")[0]))
    print("maxz=%r" % float(surfit.pnts_maxz("wells")[0]))
    surfit.pnts_plus_real(1, "wells")
    print("shifted=%r" % float(surfit.pnts_maxz("wells")[0]))
    surfit.pnts_write("shifted.txt", "wells")
    surfit.pnts_rotate(0, 0, 90, "wells")
    surfit.pnts_write("rotated.txt", "wells")
    print("rotated_minx=%r" % float(surfit.pnts_minx("wells")[0]))
    surfit.mask_from_surf("nosuchsrf")
    print("mask_size=%d" % surfit.mask_size())
    surfit.grid_get_for_pnts(50, 50, "wells", "from_pnts")
    print("grid_check=%d" % int(surfit.grid_check()))


CASES = (
    ("areas", tcl_areas, python_areas, ("areas.dat", "areas.txt", "inverted.dat")),
    ("points", tcl_points, python_points, ("wells.txt", "wells.dat")),
    ("surfaces", tcl_surfaces, python_surfaces, ("result.dat",)),
    ("surf math", tcl_surf_math, python_surf_math, ("math.dat", "plus.dat")),
    ("pnts math", tcl_pnts_math, python_pnts_math,
     ("shifted.txt", "rotated.txt")),
    ("settings", tcl_settings, python_settings, ()),
    ("hist datafile", tcl_hist_datafile, python_hist_datafile, ("task.dat",)),
    ("minmax", tcl_minmax, python_minmax, ()),
    ("pnts to cntrs", tcl_pnts_to_cntrs, python_pnts_to_cntrs, ()),
    ("surf debit", tcl_surf_debit, python_surf_debit, ()),
    ("dem zip", tcl_dem_zip, python_dem_zip, ()),
    ("dem wave", tcl_dem_wave, python_dem_wave, ()),
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
           "converted=", "cntrs=", "debit=", "rect=", "dems=", "dem_x=",
           "dem_y=", "dem_minz=", "dem_maxz=", "wave_level=", "wave_value=",
           "empty=", "names=",
           "minz=", "maxz=", "sum=", "cells=", "doubled=", "after_plus=",
           "minx=", "shifted=", "rotated_minx=", "mask_size=", "grid_check=",
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
