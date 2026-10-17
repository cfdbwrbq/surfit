"""Runs every bound command through both front ends and compares the results.

One table describes the steps.  It is rendered twice - into a tclsh script and
into a Python script - so the two sides cannot drift apart, and every result is
printed with the same marker.  Comparing a transcript is stricter than counting
that a command exists: it says the two engines computed the same thing.

A step whose call fails prints `R=ERROR` on that side, so one broken command
does not hide the rest; the failing names are listed at the end.
"""

import os
import re
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

#: Everything is built in sequence, so the state accumulates as a script would.
STEPS = (
    # --- settings and library utilities -------------------------------
    ("map_name", []),
    ("types_info", []),
    ("solvers_info", []),
    ("get_solvers_count", []),
    ("get_solver_short_name", [0]),
    ("get_solver_long_name", [0]),
    ("get_current_solver_short_name", []),
    ("get_current_solver_long_name", []),
    ("set_solver", ["cg"]),
    ("get_threads", []),
    ("init_threads", [2]),
    ("get_threads", []),
    ("mem_info", []),
    ("log_open", []),
    ("putlog", ["hello from the test"]),
    ("log_clear", []),
    ("show_c", []),
    ("show_w", []),
    ("get_tol", []),
    ("set_tol", [1e-005]),
    ("get_tol", []),
    ("get_sor_omega", []),
    ("set_sor_omega", [1.6]),
    ("get_ssor_omega", []),
    ("set_ssor_omega", [1.6]),
    ("get_penalty_max_iter", []),
    ("set_penalty_max_iter", [99]),
    ("get_penalty_weight", []),
    ("set_penalty_weight", [1]),
    ("get_penalty_weight_mult", []),
    ("set_penalty_weight_mult", [10]),
    ("get_reproject_faults", []),
    ("set_reproject_faults", [1]),
    ("get_reproject_undef_areas", []),
    ("set_reproject_undef_areas", [0]),
    ("get_process_isolated_areas", []),
    ("set_process_isolated_areas", [1]),
    ("get_undef_value", []),
    ("get_stop_execution", []),
    ("get_basis_cnt", []),

    # --- points -------------------------------------------------------
    ("pnts_read", ["data/7points.txt", "wells"]),
    ("pnts_read", ["data/11points.txt", "other"]),
    ("pnts_size", []),
    ("pnts_info", ["wells"]),
    ("pnts_minx", ["wells"]),
    ("pnts_maxx", ["wells"]),
    ("pnts_miny", ["wells"]),
    ("pnts_maxy", ["wells"]),
    ("pnts_minz", ["wells"]),
    ("pnts_maxz", ["wells"]),
    ("pnts_mean", ["wells"]),
    ("pnts_std", [1.0, "wells"]),
    ("pnts_abs", ["wells"]),
    ("pnts_plus_real", [1.0, "wells"]),
    ("pnts_minus_real", [0.5, "wells"]),
    ("pnts_mult_real", [2.0, "wells"]),
    ("pnts_div_real", [2.0, "wells"]),
    ("pnts_set_real", [7.0, "wells"]),
    ("pnts_set", ["wells"]),
    ("pnts_plus", ["wells", "other"]),
    ("pnts_minus", ["wells", "other"]),
    ("pnts_mult", ["wells", "other"]),
    ("pnts_div", ["wells", "other"]),
    ("pnts_concat", ["wells", "other"]),
    ("pnts_add_noise", [0.0, "wells"]),
    ("pnts_transform", [1.0, 2.0, 3.0, 4.0, "wells"]),
    ("pnts_inverse_transform", [1.0, 2.0, 3.0, 4.0, "wells"]),
    ("pnts_rotate", [0.0, 0.0, 90.0, "wells"]),
    ("pnts_to_cntrs", ["wells"]),
    ("cntr_size", []),
    ("curv_size", []),

    # --- rules over points --------------------------------------------
    ("grid_get", [-12, 12, 0.2, -12, 12, 0.2]),
    ("grid_check", []),
    ("points", ["wells"]),
    ("points_add", [0.5, "wells"]),
    ("points_geq", ["wells", 0]),
    ("points_leq", ["wells", 0]),
    ("clear_rules", []),

    # --- surface rules and the solve ----------------------------------
    ("set_map_name", ["map"]),
    ("area_read", ["data/area1.txt", "area1"]),
    ("area", [10, "area1"]),
    ("completer", [1, 1.6]),
    ("surfit", []),
    ("surf_size", []),
    ("surfs_info", []),
    ("surf_info", ["map"]),

    # --- surface statistics and arithmetic ----------------------------
    ("surf_minz", ["map"]),
    ("surf_maxz", ["map"]),
    ("surf_mean", ["map"]),
    ("surf_wmean", ["map", "map"]),
    ("surf_sum", ["map"]),
    ("surf_std", [10.0, "map"]),
    ("surf_area_minz", ["area1", "map"]),
    ("surf_area_maxz", ["area1", "map"]),
    ("surf_area_mean", ["area1", "map"]),
    ("surf_area_wmean", ["area1", "map", "map"]),
    ("surf_sum_area", ["area1", "map"]),
    ("surf_cells_in_area", ["area1", "map"]),
    ("surf_plus_value", [1.0, "map"]),
    ("surf_minus_value", [1.0, "map"]),
    ("surf_mult_value", [2.0, "map"]),
    ("surf_div_value", [2.0, "map"]),
    ("surf_set_value", [3.0, "map"]),
    ("surf_undef", [1e30, "map"]),
    ("surf_set_value_area", ["undef", "area1", "map"]),
    ("surf_plus_value_area", [1.0, "map", "area1"]),
    ("surf_minus_value_area", [1.0, "area1", "map"]),
    ("surf_mult_value_area", [2.0, "area1", "map"]),
    ("surf_div_value_area", [2.0, "area1", "map"]),
    ("surf_plus_area", ["map", "area1", "map"]),
    ("surf_minus_area", ["map", "area1", "map"]),
    ("surf_mult_area", ["map", "area1", "map"]),
    ("surf_div_area", ["map", "area1", "map"]),
    ("surf_set_area", ["map", "area1", "map"]),
    ("surf_plus", ["map", "map"]),
    ("surf_minus", ["map", "map"]),
    ("surf_mult", ["map", "map"]),
    ("surf_div", ["map", "map"]),
    ("surf_set", ["map"]),
    ("surf_swapxy", ["map"]),
    ("surf_gradient", ["map", "grad"]),
    ("surf_project", ["map", "coarse"]),
    ("surf_filter_by_surf", [0.0, "map", "coarse"]),
    ("surf_filter_by_mask", ["map", "m1"]),
    ("surf_filter_in_area", ["map", "area1"]),
    ("surf_filter_out_area", ["map", "area1"]),
    ("surf_to_mask", [0.0, 100.0, "map"]),
    ("surf_to_pnts", ["map"]),
    ("surf_trace_cntr", ["map", 5.0, 0.0, 50.0]),
    ("surf_add_noise", [0.0, "map"]),
    ("surf_decomp", ["map"]),
    ("surf_get_details_level", ["map"]),
    ("surf_recons", ["map"]),
    ("surf_auto_decomp", [0.01, "map"]),
    ("surf_full_recons", ["map"]),
    ("surf_adj_hist", ["map"]),
    ("surf_resid", ["resid.txt", "map", "wells"]),
    ("surf_save", ["map.dat", "map"]),
    ("surf_load", ["map.dat", "loaded"]),
    ("surf_info", ["loaded"]),

    # --- masks ---------------------------------------------------------
    ("mask_from_surf", ["loaded"]),
    ("mask_size", []),
    ("mask_info", ["m1"]),
    ("mask_from_surf", ["coarse"]),
    ("mask_and", ["m1", "m2"]),
    ("mask_or", ["m1", "m2"]),
    ("mask_xor", ["m1", "m2"]),
    ("mask_not", ["m1", "m3"]),
    ("mask_add", [1.0, 1, "m1"]),
    ("mask_geq", [10.0, "m1", 0]),
    ("mask_leq", [10.0, "m1", 0]),
    ("mask_mean", [10.0, "m1"]),
    ("mask_surf", ["map", "m1"]),
    ("mask_surf_add", ["map", 1, "m1"]),
    ("mask_surf_geq", ["map", "m1", 0]),
    ("mask_surf_leq", ["map", "m1", 0]),
    ("mask_wmean", [10.0, "m1", "map"]),
    ("mask_apply_to_surf", ["m1", "map"]),
    ("mask_to_surf", ["m1"]),
    ("mask_completer", ["m1", 1, 2, 0, 1]),
    ("mask_completer_add", [1, "m1", 1, 2, 0, 1]),
    ("mask_save", ["masks.dat"]),
    ("mask_load", ["masks.dat", "loaded_mask"]),
    ("mask_del", ["m3"]),
    ("mask_size", []),

    # --- histograms ----------------------------------------------------
    ("hist_from_pnts", ["wells"]),
    ("hist_size", []),
    ("hists_info", []),
    ("hist_from_surf", ["map"]),
    ("hist_write", ["hist.txt", "*"]),
    ("hist_read", ["hist.txt", 0.0, 200.0, "read_hist"]),
    ("hist_size", []),
    ("hist_del", ["*"]),
    ("hist_size", []),

    # --- contours and curves -------------------------------------------
    ("cntr_read", ["data/cntr_center.xyz", "c1"]),
    ("cntr_size", []),
    ("cntr_info", []),
    ("cntr_plus_real", [1.0, "c1"]),
    ("cntr_minus_real", [1.0, "c1"]),
    ("cntr_div_real", [2.0, "c1"]),
    ("cntr_smooth", ["c1", 1]),
    ("cntr_to_curv", ["c1"]),
    ("curv_size", []),
    ("cntr_save", ["cntr.dat", "c1"]),
    ("cntr_write", ["cntr.txt", "c1"]),
    ("cntr_del", ["*"]),

    ("curv_read", ["data/flt_line1.txt", "line"]),
    ("curv_size", []),
    ("curvs_info", []),
    ("curv_plus_real", [1.0, "line"]),
    ("curv_minus_real", [1.0, "line"]),
    ("curv_div_real", [2.0, "line"]),
    ("curv_save", ["curv.dat", "line"]),
    ("curv_write", ["curv.txt", "line"]),
    ("curv_del", ["*"]),

    # --- areas ---------------------------------------------------------
    ("area_read", ["data/area2.txt", "area2"]),
    ("area_size", []),
    ("areas_info", []),
    ("area_info", ["area2"]),
    ("area_invert", ["area2"]),
    ("area_plus_real", [1.0, "area2"]),
    ("area_minus_real", [1.0, "area2"]),
    ("area_mult_real", [2.0, "area2"]),
    ("area_div_real", [2.0, "area2"]),
    ("area_smooth", ["area2", 1]),
    ("area_save", ["areas.dat"]),
    ("area_load", ["areas.dat", "loaded_area"]),
    ("area_write", ["areas.txt"]),
    ("area_del", ["area2"]),
    ("area_size", []),

    # --- grids ---------------------------------------------------------
    ("grid_get_for_pnts", [50, 50, "wells", "g_pnts"]),
    ("grid_save", ["grid.dat"]),
    ("grid_load", ["grid.dat", "g_loaded"]),
    ("grid_unload", []),
    ("grid_get_from_surf", ["map", "g_surf"]),
    ("grid2", [0.1, 0.1, 2, "g_fine"]),

    # --- more rule commands ---------------------------------------------
    ("area", [10, "area1"]),
    ("completer", [1, 1.6]),
    ("surfit", []),
    ("surface", ["map"]),
    ("surface_add", [1, "map"]),
    ("surface_geq", [0.0, "map", 0]),
    ("surface_leq", [100.0, "map", 0]),
    ("trend", ["map"]),
    ("trend_add", [1, "map"]),
    ("mean", ["map"]),
    ("value", [10.0, "map"]),
    ("value_add", [1, 10.0, "map"]),
    ("wmean", ["map"]),
    ("leq", [0.0, "map", 0]),
    ("geq", [0.0, "map", 0]),
    ("smooth_contour", ["line", 0, 0]),
    ("smooth_contour_add", [1, "line", 0, 0]),
    ("triangulate", ["wells"]),
    ("clear_rules", []),
)


#: Names Python has and Tcl does not, because Tcl uses traced variables or
#: Python-only helpers.  test_commands.py compares the settings through `set`
#: instead, which is how a Tcl script reaches them.
#: Exercised, but not compared: their return value is a front-end artefact
#: (Tcl's `set` returns the value it set, log_open returns a handle).
NO_COMPARE = {"log_open", "log_clear", "set_map_name"}

NOT_IN_TCL = {
    "map_name", "get_current_solver_short_name",
    "get_current_solver_long_name",
    "get_tol", "set_tol", "get_sor_omega", "set_sor_omega",
    "get_ssor_omega", "set_ssor_omega", "get_penalty_max_iter",
    "set_penalty_max_iter", "get_penalty_weight", "set_penalty_weight",
    "get_penalty_weight_mult", "set_penalty_weight_mult",
    "get_reproject_faults", "set_reproject_faults",
    "get_reproject_undef_areas", "set_reproject_undef_areas",
    "get_process_isolated_areas", "set_process_isolated_areas",
    "get_undef_value", "get_stop_execution", "get_basis_cnt",
}


#: Names that mean something different in Tcl: the map name is a traced
#: variable, so a script writes `set map_name` where Python calls set_map_name.
TCL_INSTEAD = {
    "set_map_name": lambda args: "set map_name %s" % tcl_quote(args[0]),
}


def tcl_quote(value):
    if isinstance(value, str):
        return '"%s"' % value
    return repr(value)


def render_tcl(steps):
    lines = ["load libtclsurfit[info sharedlibextension]", "clear_data"]
    for index, (command, args) in enumerate(steps):
        if command in NOT_IN_TCL:
            continue
        if command in TCL_INSTEAD:
            call = TCL_INSTEAD[command](args)
        else:
            call = " ".join([command] + [tcl_quote(a) for a in args])
        lines.append('if {[catch {%s} _r]} { puts "R%d=ERROR" } else { puts "R%d=$_r" }'
                     % (call, index, index))
    return "\n".join(lines) + "\n"


def render_python(steps):
    lines = [
        "import sys",
        "sys.path.insert(0, %r)" % BIN,
        "import surfit",
        "surfit.clear_data()",
        "",
        "def _format(value):",
        "    if value is None:",
        "        return ''",
        "    if isinstance(value, bool):",
        "        return '1' if value else '0'",
        "    if isinstance(value, (list, tuple)):",
        "        return ' '.join(_format(item) for item in value)",
        "    try:",
        "        import numpy",
        "        if isinstance(value, numpy.ndarray):",
        "            return ' '.join(_format(item) for item in value.tolist())",
        "    except ImportError:",
        "        pass",
        "    return str(value)",
        "",
    ]
    for index, (command, args) in enumerate(steps):
        rendered = ", ".join(repr(a) for a in args)
        lines.append("try:")
        lines.append("    _r = surfit.%s(%s)" % (command, rendered))
        lines.append('    print("R%d=" + _format(_r))' % index)
        lines.append("except Exception:")
        lines.append('    print("R%d=ERROR")' % index)
    return "\n".join(lines) + "\n"


def prepare(directory):
    os.makedirs(directory, exist_ok=True)
    link = os.path.join(directory, "data")
    if not os.path.islink(link):
        os.symlink(DATA, link)
    for name in os.listdir(BIN):
        if name.endswith(".so"):
            target = os.path.join(directory, name)
            if not os.path.islink(target):
                os.symlink(os.path.join(BIN, name), target)


def run(script, directory, interpreter, env_extra):
    path = os.path.join(directory, "script" + (".tcl" if interpreter == "tclsh" else ".py"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(script)
    # -u, so a crash still leaves the results it produced: buffered output is
    # lost with the process, and that output is where the crash shows.
    command = [interpreter, os.path.basename(path)]
    if interpreter != "tclsh":
        command.insert(1, "-u")
    result = subprocess.run(command, cwd=directory, capture_output=True,
                            env=dict(os.environ, **env_extra))
    # A crash still leaves the results it produced, which is what tells us
    # where it happened; that is more useful than an exception here.
    out = {}
    for line in result.stdout.decode().splitlines():
        found = re.match(r"R(\d+)=(.*)$", line)
        if found:
            out[int(found.group(1))] = found.group(2)
    return out


def same(left, right):
    """Compares two result strings, numerically where possible."""
    left_parts = left.split()
    right_parts = right.split()
    if len(left_parts) != len(right_parts):
        return False
    for a, b in zip(left_parts, right_parts):
        try:
            if abs(float(a) - float(b)) > 1e-9 * max(1.0, abs(float(a))):
                return False
        except ValueError:
            if a != b:
                return False
    return True


def commands_file():
    return os.path.join(HERE, "tcl_commands.txt")


def uncovered():
    """The bound commands the table never exercises.

    Strictness is the point: a command that is bound but never run is a claim,
    not a fact.
    """
    with open(commands_file(), encoding="utf-8") as handle:
        declared = {line.strip() for line in handle if line.strip()}
    covered = {command for command, _ in STEPS}
    accessible = {name for name in dir(surfit) if not name.startswith("_")}
    return sorted((declared & accessible) - covered - NOT_IN_TCL)


def main():
    with tempfile.TemporaryDirectory() as tcl_dir, \
            tempfile.TemporaryDirectory() as python_dir:
        prepare(tcl_dir)
        prepare(python_dir)
        tcl = run(render_tcl(STEPS), tcl_dir, "tclsh", {"LD_LIBRARY_PATH": BIN})
        python = run(render_python(STEPS), python_dir, sys.executable,
                     {"SURFIT_BIN": BIN})

    problems, errors = [], []
    lost_python = [i for i in range(len(STEPS)) if i not in python]
    lost_tcl = [i for i in range(len(STEPS))
                if i not in tcl and STEPS[i][0] not in NOT_IN_TCL]

    for side, lost in (("python", lost_python), ("tcl", lost_tcl)):
        if lost:
            print("STOPPED on the %s side at step %d (%s); %d step(s) not run"
                  % (side, lost[0], STEPS[lost[0]][0], len(lost)))
            lost = lost[1:]

    for index, (command, args) in enumerate(STEPS):
        if index in lost_python or index in lost_tcl or command in NOT_IN_TCL:
            continue
        if command in NO_COMPARE:
            continue
        left, right = tcl[index], python[index]
        if "ERROR" in (left, right):
            errors.append((index, command, "tcl" if "ERROR" in left else "python"))
            continue
        if not same(left, right):
            problems.append((index, command, left, right))

    for index, command, side in errors:
        print("ERROR %-22s on the %s side" % (command, side))
    for index, command, left, right in problems:
        print("DIFF  %-22s\n      tcl    %s\n      python %s" % (command, left, right))

    print("\n%d step(s): %d differ, %d errored, %d missing from python, %d from tcl"
          % (len(STEPS), len(problems), len(errors), len(lost_python), len(lost_tcl)))

    missing = uncovered()
    if missing:
        print("\nnot exercised by this table (%d):" % len(missing))
        for start_at in range(0, len(missing), 6):
            print("  " + " ".join("%-22s" % n for n in missing[start_at:start_at + 6]))
    else:
        print("every bound command is exercised")
    return 1 if (problems or errors or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
