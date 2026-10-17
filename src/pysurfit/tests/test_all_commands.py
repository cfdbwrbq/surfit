"""Runs every bound command through both front ends and compares the results.

One table describes the steps.  It is rendered twice - into a tclsh script and
into a Python script - so the two sides cannot drift apart, and every result is
printed with the same marker.  Comparing a transcript is stricter than counting
that a command exists: it says the two engines computed the same thing.

Three things are compared, not one:

* every printed result, numerically where possible (`same`);
* every diagnostic either side printed - the lines the core marks with
  `Warning!` or `Error!`.  A command that returns nothing cannot be checked by
  its return value alone, and a command that silently matched no object does
  not differ between the ends - it just does nothing twice.  The diagnostics
  are where that shows up, so the two transcripts must agree on them too;
* every file both sides write, byte for byte.  The same table writes the same
  `.dat` and text files on both sides, and a save that rounds differently or
  serialises memory it never initialised shows up here and nowhere else.

A step whose call fails prints `R=ERROR` on that side, so one broken command
does not hide the rest; the failing names are listed at the end.  A side that
stops early is a failure, not a pass: the steps after it never ran.

The coverage claim is measured against the reference, not written down: the
command list is read from tclsh, and the table fails both when Tcl has a
command Python lacks and when a bound command is never run.

Loading is by name *inside the file*, not by new name: `area_load file name`
looks for an area called `name` in the file, and `surf_load` treats its second
argument as a Tcl pattern over the surfaces stored there.  That is why the
round-trip steps below delete an object before loading it back instead of
renaming it on the way in.
"""

import os
import re
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
#: Each object is created before the command that needs it, and names are the
#: ones the engine really stores (a mask made from a surface takes the
#: surface's name; a grid is only loadable by name if it was created with one).
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
    #: Two sets of the *same* size: pnts_plus/minus/mult/div/set are pairwise
    #: and return false when the sizes differ, so unequal files would leave
    #: five steps silently doing nothing.
    ("pnts_read", ["data/7points.txt", "wells"]),
    ("pnts_read", ["data/7points.txt", "other"]),
    ("pnts_size", []),
    ("pnts_info", []),
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
    ("pnts_set", ["wells", "other"]),
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

    #: round trip: save, delete, load back by the name stored in the file
    ("pnts_save", ["pnts.dat", "wells"]),
    ("pnts_write", ["pnts.txt", "wells"]),
    ("pnts_del", ["wells"]),
    ("pnts_size", []),
    ("pnts_load", ["pnts.dat", "wells"]),
    ("pnts_size", []),
    ("pnts_minz", ["wells"]),
    ("curv_size", []),

    # --- rules over points --------------------------------------------
    ("grid_get", [-12, 12, 0.2, -12, 12, 0.2, "g_base"]),
    ("grid_check", []),
    ("grid2", [0.1, 0.1, 2, "g_fine"]),
    ("grid_get", [-12, 12, 0.2, -12, 12, 0.2, "g_base"]),
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
    ("surf_swapxy", ["map"]),

    #: A second surface on the same grid (so surf_set can copy into it), and a
    #: surface on another grid (so surf_project has something to project onto).
    ("surf_gradient", ["map", "grad"]),
    ("surf_set", ["grad", "map"]),
    ("grid2", [1.0, 1.0, 2, "g_coarse"]),
    ("surf_project", ["map", "coarse"]),

    # --- the rest of the surface operations ----------------------------
    ("surf_filter_by_surf", [0.0, "map", "coarse"]),
    #: in-area then out-area on the same surface leaves nothing defined, which
    #: is exactly the edge case the grid step below has to survive: converting
    #: it to points yields a set with no points.
    ("surf_filter_in_area", ["coarse", "area1"]),
    ("surf_filter_out_area", ["coarse", "area1"]),
    ("surf_to_pnts", ["coarse"]),
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

    # --- points and surfaces together ----------------------------------
    ("pnts_update_by_surf", ["wells", "map"]),
    ("pnts_plus_surf", ["wells", "map"]),
    ("pnts_minus_surf", ["wells", "map"]),
    ("pnts_mult_surf", ["wells", "map"]),
    ("pnts_set_surf", ["wells", "map"]),
    ("pnts_div_surf", ["wells", "map"]),
    ("pnts_filter_by_surf", [0.0, "wells", "map"]),

    # --- masks ---------------------------------------------------------
    ("surf_to_mask", [0.0, 100.0, "map"]),
    ("mask_size", []),
    ("mask_info", ["map"]),
    ("mask_from_surf", ["grad"]),
    ("mask_size", []),
    ("mask_and", ["map", "grad"]),
    ("mask_or", ["map", "grad"]),
    ("mask_xor", ["map", "grad"]),
    ("mask_not", ["map", "grad"]),
    ("mask_info", ["map"]),
    ("surf_mask_mean", ["map", "map"]),
    ("surf_mask_wmean", ["map", "map", "map"]),
    ("mask_apply_to_surf", ["map", "map"]),
    ("mask_save", ["masks.dat"]),
    ("mask_del", ["grad"]),
    ("mask_size", []),
    ("mask_load", ["masks.dat", "grad"]),
    ("mask_size", []),
    ("surf_filter_by_mask", ["map", "map"]),
    ("pnts_filter_by_mask", ["wells", "map"]),

    #: the filters above may leave few points; start again from the file
    ("pnts_del", ["wells"]),
    ("pnts_read", ["data/7points.txt", "wells"]),
    ("pnts_filter_in_area", ["wells", "area1"]),
    ("pnts_filter_out_area", ["wells", "area1"]),
    ("pnts_del", ["wells"]),
    ("pnts_read", ["data/7points.txt", "wells"]),

    #: the mask becomes a surface again, after the surface it came from is
    #: gone - otherwise both would carry the same name.
    ("surf_del", ["grad"]),
    ("mask_to_surf", ["grad"]),
    ("surf_info", ["grad"]),

    #: surface round trip, by the name stored in the file
    ("surf_save", ["map.dat", "map"]),
    ("surf_del", ["map"]),
    ("surf_size", []),
    ("surf_load", ["map.dat", "map"]),
    ("surf_size", []),
    ("surf_info", ["map"]),

    # --- histograms ----------------------------------------------------
    ("hist_from_pnts", ["wells", 64, 0.0, 200.0, "h_wells"]),
    ("hist_size", []),
    ("hists_info", []),
    ("hist_from_surf", ["map", 64, 0.0, 20.0, "h_map"]),
    ("hist_size", []),
    ("hist_write", ["hist.txt", "*"]),
    ("hist_read", ["hist.txt", 0.0, 200.0, "read_hist"]),
    ("hist_size", []),
    ("hist_del", ["h_wells"]),
    ("hist_size", []),

    # --- contours and curves -------------------------------------------
    ("cntr_read", ["data/cntr_center.xyz", "c1"]),
    ("cntr_size", []),
    ("cntrs_info", []),
    ("cntr_plus_real", [1.0, "c1"]),
    ("cntr_minus_real", [1.0, "c1"]),
    ("cntr_mult_real", [2.0, "c1"]),
    ("cntr_div_real", [2.0, "c1"]),
    ("cntr_smooth", ["c1", 1]),
    ("cntr_to_pnts", [1.0, "c1"]),
    ("cntr_to_curv", ["c1"]),
    ("curv_size", []),
    ("cntr_save", ["cntr.dat", "c1"]),
    ("cntr_write", ["cntr.txt", "c1"]),
    ("cntr_del", ["c1"]),
    ("cntr_size", []),
    ("cntr_load", ["cntr.dat", "c1"]),
    ("cntr_size", []),

    ("curv_read", ["data/flt_line1.txt", "line"]),
    ("curv_size", []),
    ("curvs_info", []),
    ("curv_to_cntr", [0.0, "line"]),
    ("curv_save", ["curv.dat", "line"]),
    ("curv_write", ["curv.txt", "line"]),
    ("curv_del", ["line"]),
    ("curv_size", []),
    ("curv_load", ["curv.dat", "line"]),
    ("curv_size", []),

    # --- areas ---------------------------------------------------------
    ("area_read", ["data/area2.txt", "area2"]),
    ("area_size", []),
    ("areas_info", []),
    ("area_invert", ["area2"]),
    ("area_save", ["areas.dat"]),
    ("area_del", ["area2"]),
    ("area_size", []),
    ("area_load", ["areas.dat", "area2"]),
    ("area_size", []),
    ("area_write", ["areas.txt"]),
    ("area_del", ["area2"]),
    ("area_size", []),

    # --- grids ---------------------------------------------------------
    ("grid_get_for_pnts", [50, 50, "wells", "g_pnts"]),
    ("grid_info", []),
    ("grid_save", ["grid.dat"]),
    ("grid_unload", []),
    ("grid_check", []),
    ("grid_load", ["grid.dat", "g_pnts"]),
    ("grid_check", []),
    ("grid_get_from_surf", ["map", "g_surf"]),
    ("grid_get2", [0.0, 10.0, 1.0, 0.0, 10.0, 1.0, "g_fixed"]),
    ("grid_get_for_pnts_step", [0.5, 0.5, "wells", "g_step"]),
    ("grid", [0.3, 0.3, 2, "g_auto"]),
    ("grid_info", []),

    # --- rules over areas, masks, curves, contours and surfaces --------
    #: The result goes to a new name, so the surface the rules use as data
    #: ("map") is not replaced by the rule result.
    ("set_map_name", ["solved"]),
    ("area", [10, "area1"]),
    ("completer", [1, 1.6]),
    ("completer_add", [1, 1, 1.6, 0, 1]),
    ("area_add", [10, 1, "area1"]),
    ("area_geq", [0, "area1", 0, 1]),
    ("area_leq", [100, "area1", 0, 1]),
    ("area_mean", [10, "area1", -2, 1]),
    ("area_wmean", [10, "area1", "map", -2, 1]),
    ("area_surf", ["map", "area1", 1]),
    ("area_surf_add", ["map", 1, "area1", 1]),
    ("area_surf_geq", ["map", "area1", 0, 1]),
    ("area_surf_leq", ["map", "area1", 0, 1]),
    ("area_completer", ["area1", 1, 2, 0, 1, 1]),
    ("area_completer_add", [1, "area1", 1, 2, 0, 1, 1]),
    ("area_hist", ["area1", "h_map", -1, 1]),
    ("hist", ["h_map", -1, 5]),
    ("mask", [10, "map"]),
    ("mask_add", [10, 1, "map"]),
    ("mask_geq", [10, "map", 0]),
    ("mask_leq", [10, "map", 0]),
    ("mask_mean", [10, "map", -2]),
    ("mask_wmean", [10, "map", "map", -2]),
    ("mask_surf", ["map", "map"]),
    ("mask_surf_add", ["map", 1, "map"]),
    ("mask_surf_geq", ["map", "map", 0]),
    ("mask_surf_leq", ["map", "map", 0]),
    ("mask_completer", ["map", 1, 2, 0, 1]),
    ("mask_completer_add", [1, "map", 1, 2, 0, 1]),
    ("contour", ["c1"]),
    ("contour_add", [50, "c1"]),
    #: smooth_contour_add() attaches to the last modifiable rule, so it belongs
    #: right after contour(), not after smooth_contour(), which pushes a
    #: non-modifiable condition of its own.
    ("smooth_contour_add", [1, "c1"]),
    ("contour_geq", ["c1", 0]),
    ("contour_leq", ["c1", 0]),
    ("curve", [10, "line"]),
    ("curve_add", [10, 1, "line"]),
    ("curve_geq", [10, "line", 0]),
    ("curve_leq", [10, "line", 0]),
    ("curve_surf", ["map", "line"]),
    ("curve_surf_add", ["map", 1, "line"]),
    ("curve_surf_geq", ["map", "line", 0]),
    ("curve_surf_leq", ["map", "line", 0]),
    ("fault", ["line"]),
    ("surface", ["map"]),
    ("surface_add", [1, "map"]),
    ("surface_geq", ["map", 0]),
    ("surface_leq", ["map", 100]),
    ("trend", [1, 2, "map"]),
    ("trend_add", [1, 1, 0, "map"]),
    ("mean", [10, -2]),
    ("value", ["undef"]),
    ("value_add", [1, 10]),
    ("wmean", [10, "map", -2]),
    ("leq", [0, 0]),
    ("geq", [0, 0]),
    ("smooth_contour", ["c1", 0]),
    ("triangulate", []),
    ("surfit", []),
    ("clear_rules", []),

    # --- the whole task in one datafile --------------------------------
    #: The task file carries the grid, surfaces, masks, points, contours, curves,
    #: areas and histograms.  After file_load the two histograms alive at save
    #: time - h_map and read_hist - are back; h_wells was deleted earlier and
    #: stays deleted.  The two hist_size steps below check both states.
    ("file_save", ["all.dat"]),
    ("file_info", ["all.dat"]),
    ("clear_data", []),
    ("pnts_size", []),
    ("surf_size", []),
    ("area_size", []),
    ("mask_size", []),
    ("hist_size", []),
    ("cntr_size", []),
    ("curv_size", []),
    ("grid_check", []),
    ("file_load", ["all.dat"]),
    ("pnts_size", []),
    ("surf_size", []),
    ("area_size", []),
    ("mask_size", []),
    ("hist_size", []),
    ("cntr_size", []),
    ("curv_size", []),
    ("grid_check", []),

    # --- object accessors -----------------------------------------------
    #: Names, ids, positions and per-object geometry, on the state the task
    #: file restored.  Exercised here rather than next to each collection so
    #: the accessors and the serialisation are checked against each other.
    #: `*_getNameAt 99` asks for a position that does not exist: it answers an
    #: empty name, and on the Tcl side that goes through the typemap that would
    #: dereference a NULL string.
    ("pnts_getName", []),
    ("pnts_getNameAt", [0]),
    ("pnts_getNameAt", [99]),
    ("pnts_getId", ["wells"]),
    ("pnts_getCount", ["wells"]),
    ("pnts_setName", ["wells2", "wells"]),
    ("pnts_getName", []),
    ("pnts_setName", ["wells", "wells2"]),

    ("surf_getName", []),
    ("surf_getNameAt", [0]),
    ("surf_getNameAt", [99]),
    ("surf_getId", ["map"]),
    ("surf_getCountX", ["map"]),
    ("surf_getCountY", ["map"]),
    ("surf_getStepX", ["map"]),
    ("surf_getStepY", ["map"]),
    ("surf_getValue", [10.0, 10.0, "map"]),
    ("surf_getValueIJ", [0, 0, "map"]),
    ("surf_D1", ["map"]),
    ("surf_D2", ["map"]),
    ("surf_setName", ["map2", "map"]),
    ("surf_getName", []),
    ("surf_setName", ["map", "map2"]),

    ("mask_getName", []),
    ("mask_getNameAt", [0]),
    ("mask_getNameAt", [99]),
    ("mask_getId", ["map"]),
    ("mask_getValue", [10.0, 10.0, "map"]),
    ("mask_setName", ["map2", "map"]),
    ("mask_getName", []),
    ("mask_setName", ["map", "map2"]),

    #: the task file restores the histograms, so h_map and read_hist are here;
    #: the rename targets one of them, and h_wells is still gone
    ("hist_getName", []),
    ("hist_getNameAt", [0]),
    ("hist_setName", ["h2", "h_map"]),
    ("hist_getName", []),

    ("cntr_getName", []),
    ("cntr_getNameAt", [0]),
    ("cntr_getNameAt", [99]),
    ("cntr_getId", ["c1"]),
    ("cntr_setName", ["c2", "c1"]),
    ("cntr_getName", []),
    ("cntr_setName", ["c1", "c2"]),

    ("curv_getName", []),
    ("curv_getNameAt", [0]),
    ("curv_getNameAt", [99]),
    ("curv_getId", ["line"]),
    ("curv_setName", ["line2", "line"]),
    ("curv_getName", []),
    ("curv_setName", ["line", "line2"]),

    ("area_getName", []),
    ("area_getNameAt", [0]),
    ("area_getNameAt", [99]),
    ("area_getId", ["area1"]),
    ("area_setName", ["area9", "area1"]),
    ("area_getName", []),
    ("area_setName", ["area1", "area9"]),

    #: the setters change the target grid's step, so they come last
    ("grid_getCountX", []),
    ("grid_getCountY", []),
    ("grid_getStepX", []),
    ("grid_getStepY", []),
    ("grid_getCoordNodeX", [0]),
    ("grid_getCoordNodeY", [0]),
    ("grid_setCountX", [50]),
    ("grid_getCountX", []),
    ("grid_getStepX", []),
    ("grid_setCountY", [50]),
    ("grid_getCountY", []),

    # --- how file_save treats an existing file --------------------------
    ("datafile_mode", []),
    ("datafile_append", []),
    ("datafile_mode", []),
    ("datafile_new", []),
    ("datafile_mode", []),

    # --- globe: the digital elevation model -------------------------------
    #: The DEMs are built from the surface the task file restored, so the whole
    #: family is exercised on data that travelled through the task file.
    ("dem_size", []),
    ("dems_info", []),
    ("surf_to_dem", ["map"]),
    ("dem_size", []),
    ("dem_getName", []),
    ("dem_getNameAt", [0]),
    ("dem_getNameAt", [99]),
    ("dem_getId", ["map"]),
    ("dem_getCountX", ["map"]),
    ("dem_getCountY", ["map"]),
    ("dem_getStepX", ["map"]),
    ("dem_getStepY", ["map"]),
    ("dem_minz", ["map"]),
    ("dem_maxz", ["map"]),
    ("dem_getValue", [10.0, 10.0, "map"]),
    ("dem_D1", ["map"]),
    ("dem_D2", ["map"]),
    ("dem_save", ["dem.dat", "map"]),
    ("dem_save_grd", ["dem.grd", "map"]),
    ("dem_save_xyz", ["dem.xyz", "map"]),
    ("dem_resid", ["dem_resid.txt", "map", "wells"]),
    #: not implemented upstream: it logs "Not implemented!" and fails.  Listed
    #: in EXPECTED_FAILURE, so the step still has to fail on both sides.
    ("dem_save_dtm", ["dem.dtm"]),
    ("dem_decomp", ["map"]),
    ("dem_get_details_level", ["map"]),
    ("dem_recons", ["map"]),
    ("dem_full_recons", ["map"]),
    ("dem_auto_decomp", [0.01, "map"]),
    ("dem_project", ["proj", "map"]),
    ("dem_gradient", ["grad", "map"]),
    ("dem_to_pnts", ["map"]),
    ("dem_to_surf", ["map"]),
    ("dem_to_mask", [0, 1000, "map"]),
    ("dem_plus", ["map", "proj"]),
    ("dem_minus", ["map", "proj"]),
    ("dem_mult", ["map", "proj"]),
    ("dem_div", ["proj", "map"]),
    ("dem_set", ["proj", "map"]),
    ("dem_plus_real", [1.0, "map"]),
    ("dem_minus_real", [1.0, "map"]),
    ("dem_mult_real", [2.0, "map"]),
    ("dem_div_real", [2.0, "map"]),
    ("dem_set_real", [7.0, "map"]),
    ("dem_undef", [1e30, "map"]),
    ("dem_setName", ["map2", "map"]),
    ("dem_getName", []),
    ("dem_setName", ["map", "map2"]),
    ("dem_del", ["map"]),
    ("dem_size", []),
    ("dem_load", ["dem.dat", "map"]),
    ("dem_size", []),
    ("dem_load_grd", ["dem.grd", "map"]),
    ("dem_size", []),
    #: a DTM fixture in data/ (dtm4.hdr + dtm4.DEM, 4x4 int16): the loader
    #: derives the binary's name from the header's, so only the header is named.
    ("dem_load_dtm", ["data/dtm4.hdr", "dtm4"]),
    ("dem_getName", []),
    ("dem_getCountX", ["dtm4"]),
    ("dem_getValue", [44.0, 43.0, "dtm4"]),
    #: These read a file, so the data directory holds empty fixtures under the
    #: names the loaders parse: a missing file would make find_first() match
    #: nothing and every one of them would quietly return an empty result.
    ("dem_load_hgt", ["data/N00E006.hgt"]),
    ("dem_load_hgt_zip", ["data/N00E006.hgt.zip"]),
    ("dem_load_globe", ["data/a16g"]),
    #: rules over the DEMs, after the loaders so there is something to match
    ("dem", ["*"]),
    ("dem_add", [1.0, "*"]),
    ("dem_del", ["*"]),
    ("dem_size", []),

    # --- freeflow: conservation of mass ----------------------------------
    #: flow_points/area/curve/contour attach to the last modifiable rule, so
    #: lcm_simple() has to come first - without it each of them answers false.
    ("lcm_simple", [1, 1, 1]),
    ("flow_points", ["wells"]),
    ("flow_area", [10.0, "area1"]),
    ("flow_curve", [5.0, "line"]),
    ("flow_contour", ["c1"]),
    ("lcm_simple_add", [1, 1, 1, 1]),
    ("flow_points", ["*"]),
    #: a cell inside the surface, and a point outside it: the second one has no
    #: neighbours to difference against, and used to read past the array
    ("surf_debit", [0.0, 0.0, 1, 1, 1, "map"]),
    ("surf_debit", [500.0, 500.0, 1, 1, 1, "map"]),
    ("surf_debit_rect", [-5.0, -5.0, 5.0, 5.0, 1, 1, 1, "map"]),
    ("clear_rules", []),

    # --- the format plugin ----------------------------------------------
    #: Each saver writes, and the matching loader reads the file back under a
    #: name of its own, so the pair is checked on the file itself.  The written
    #: files are then compared byte for byte between the two front ends.
    ("surf_save_grd", ["fmt.grd", "map"]),
    ("surf_load_grd", ["fmt.grd", "grd_map"]),
    ("surf_save_xyz", ["fmt.xyz", "map"]),
    ("surf_load_xyz", ["fmt.xyz", "xyz_map"]),
    ("surf_save_gmt", ["fmt.gmt", "map"]),
    ("surf_load_gmt", ["fmt.gmt", "gmt_map"]),
    ("surf_save_grass", ["fmt.grass", "map"]),
    ("surf_load_grass", ["fmt.grass", "grass_map"]),
    ("surf_save_arcgis", ["fmt.asc", "map"]),
    ("surf_load_arcgis", ["fmt.asc", "arcgis_map"]),
    ("surf_save_bmp", ["fmt.bmp", "map"]),
    ("surf_load_bmp", ["fmt.bmp", "bmp_map"]),
    ("surf_save_jpg", ["fmt.jpg", "map"]),
    ("surf_load_jpg", ["fmt.jpg", "jpg_map"]),
    ("mask_save_grd", ["fmt_mask.grd", "map"]),
    ("mask_save_xyz", ["fmt_mask.xyz", "map"]),

    ("area_save_bln", ["fmt_area.bln", "area1"]),
    ("area_load_bln", ["fmt_area.bln", "bln_area"]),
    ("area_save_shp", ["fmt_area.shp", "area1"]),
    ("area_load_shp", ["fmt_area.shp", "shp_area"]),

    ("curv_save_bln", ["fmt_curv.bln", "line"]),
    ("curv_load_bln", ["fmt_curv.bln", "bln_curv"]),
    ("curv_save_shp", ["fmt_curv.shp", "line"]),
    ("curv_load_shp", ["fmt_curv.shp", "shp_curv"]),

    ("cntr_save_bln", ["fmt_cntr.bln", "c1"]),
    ("cntr_load_bln", ["fmt_cntr.bln", "bln_cntr"]),
    ("cntr_save_shp", ["fmt_cntr.shp", "c1"]),
    #: A contour with one Z value is written as a 2D arc with a Z column, so the
    #: loader has to be told which column holds it; without a field name it
    #: expects a 3D shape and refuses this file.
    ("cntr_load_shp", ["fmt_cntr.shp", "shp_cntr", "Z"]),

    ("pnts_save_shp", ["fmt_pnts.shp", "wells"]),
    ("pnts_load_shp", ["fmt_pnts.shp", "shp_pnts"]),
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


#: The modules a Tcl script loads, in the order `import surfit` registers their
#: managers: the engine, the format plugin, then globe and freeflow.
TCL_MODULE_LOADS = ("load libtclsurfit[info sharedlibextension]\n"
                    "load libsurfit_io[info sharedlibextension]\n"
                    "load libglobe[info sharedlibextension]\n"
                    "load libfreeflow[info sharedlibextension]")


def tcl_quote(value):
    if isinstance(value, str):
        return '"%s"' % value
    return repr(value)


def render_tcl(steps):
    # Every plugin the Python side registers when it is imported, in that order:
    # a Tcl script has to load them, where import surfit does it itself.  The
    # managers are registered in load order, and types_info lists them in it.
    lines = [TCL_MODULE_LOADS, "clear_data"]
    for index, (command, args) in enumerate(steps):
        if command in NOT_IN_TCL:
            continue
        if command in TCL_INSTEAD:
            call = TCL_INSTEAD[command](args)
        else:
            call = " ".join([command] + [tcl_quote(a) for a in args])
        # The leading newline separates the marker from output that a command
        # left without a trailing newline (file_info writes its listing that
        # way), and a multi-line result is folded onto one line so that the
        # transcript stays parseable.
        lines.append('if {[catch {%s} _r]} { puts "\nR%d=ERROR" }'
                     ' else { puts "\nR%d=[string map [list "\n" "|" "\r" "|"] $_r]" }'
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
        lines.append('    print("\\nR%d=" + _format(_r)'
                     '.replace("\\r", "|").replace("\\n", "|"))' % index)
        lines.append("except Exception:")
        lines.append('    print("\\nR%d=ERROR")' % index)
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
    """Runs one side, returning its results and the output it produced."""
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
    return out, result.stdout.decode()


#: Files each side writes that are either the script itself or a log carrying
#: wall-clock timestamps; everything else must be identical.
NOT_AN_ARTEFACT = ("script.tcl", "script.py", "surfit.log")


def artefacts(directory):
    """The files a side wrote, as name -> content."""
    found = {}
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if name in NOT_AN_ARTEFACT or os.path.islink(path):
            continue
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            found[name] = handle.read()
    return found


#: The core tags diagnostics with these prefixes; the tclsh wrapper adds one
#: more when it catches the exception an error raises.  Lines are compared
#: without their timestamp.
DIAGNOSTIC = re.compile(r"(Warning!|Error!)")
WRAPPER_ONLY = "Error! Execution stopped"


def diagnostics(output):
    """The warning and error lines a side printed, in order."""
    found = []
    for line in output.splitlines():
        line = re.sub(r"^\d\d/\d\d/\d\d \d\d:\d\d:\d\d : ", "", line)
        if DIAGNOSTIC.search(line) and line.strip() != WRAPPER_ONLY:
            found.append(line)
    return found


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


#: Commands the Tcl front end has and Python deliberately does not.  The list
#: is the only place where the coverage check accepts a gap, so it stays short
#: and every entry says why.
NOT_BOUND = {
    # CreEPS: draws PostScript through the Tcl front end's own graphics code,
    # and the viewer closes the canvas the Tcl side opens.
    "surf_plot",
}

#: Commands that raise on both sides by design, with the reason.  They stay in
#: the table: a call that stops failing - or starts failing on one side only -
#: is a change worth failing on.
EXPECTED_FAILURE = {
    "dem_save_dtm": "not implemented: _dem_save_dtm() logs and returns false",
    "dem_load_hgt": "needs a real SRTM tile: the grid comes from the file name "
                    "and the size",
    "dem_load_hgt_zip": "same, and this build has no zlib (HAVE_ZLIB_H unset)",
    "dem_load_globe": "needs a real GTOPO30 tile: 10800 x 4800 or 6000 cells",
}

TCL_COMMANDS = "foreach c [info commands] { puts $c }"


def tcl_commands():
    """The commands the Tcl front end has, asked of tclsh itself.

    Asking the reference beats keeping a list by hand: the hand-written list
    this replaced was missing 44 commands of the core alone, and the check
    could not see them because it intersected the two sets instead of
    comparing them.  A command that Tcl has and Python lacks is invisible to an
    intersection.  The plugins are loaded here for the same reason: their
    commands are part of the front end only once a script has loaded them.
    """
    def names(script):
        result = subprocess.run(
            ["tclsh"], input=script, capture_output=True, text=True,
            env=dict(os.environ, LD_LIBRARY_PATH=BIN))
        if result.returncode != 0:
            raise SystemExit("tclsh failed while listing commands:\n" + result.stderr)
        # A command name is one token; the banner the module prints on load is
        # prose and has spaces in it.
        return {line.strip() for line in result.stdout.splitlines()
                if line.strip() and " " not in line}

    bare = names(TCL_COMMANDS + "\n")
    loaded = names(TCL_MODULE_LOADS + "\n" + TCL_COMMANDS + "\n")
    return loaded - bare


def coverage_problems():
    """What the table fails to bind, and what it fails to exercise.

    Two claims, kept apart on purpose: "Tcl has it and Python does not" used to
    disappear into the intersection, so it is checked first and reported on its
    own.  The second claim - every bound command is run - is the strictness the
    table exists for: a command that is bound but never run is a claim, not a
    fact.
    """
    declared = tcl_commands()
    covered = {command for command, _ in STEPS}
    accessible = {name for name in dir(surfit) if not name.startswith("_")}
    unbound = sorted(declared - accessible - NOT_BOUND)
    unexercised = sorted((declared & accessible) - covered - NOT_IN_TCL)
    return unbound, unexercised


def main():
    with tempfile.TemporaryDirectory() as tcl_dir, \
            tempfile.TemporaryDirectory() as python_dir:
        prepare(tcl_dir)
        prepare(python_dir)
        tcl, tcl_output = run(render_tcl(STEPS), tcl_dir, "tclsh",
                              {"LD_LIBRARY_PATH": BIN})
        python, python_output = run(render_python(STEPS), python_dir, sys.executable,
                                    {"SURFIT_BIN": BIN})
        # Both sides write the same files from the same table.  Comparing the
        # bytes is stricter than comparing the printed results: a save that
        # rounds differently, or writes memory it never initialised, shows up
        # here and nowhere else.
        tcl_files = artefacts(tcl_dir)
        python_files = artefacts(python_dir)

    problems, errors, unexpected_passes = [], [], []
    expected = 0
    lost_python = [i for i in range(len(STEPS)) if i not in python]
    lost_tcl = [i for i in range(len(STEPS))
                if i not in tcl and STEPS[i][0] not in NOT_IN_TCL]

    for side, lost in (("python", lost_python), ("tcl", lost_tcl)):
        if lost:
            print("STOPPED on the %s side at step %d (%s); %d step(s) not run"
                  % (side, lost[0], STEPS[lost[0]][0], len(lost)))

    for index, (command, args) in enumerate(STEPS):
        if index in lost_python or index in lost_tcl or command in NOT_IN_TCL:
            continue
        if command in NO_COMPARE:
            continue
        left, right = tcl[index], python[index]
        if "ERROR" in (left, right):
            sides = [name for name, value in (("tcl", left), ("python", right))
                     if "ERROR" in value]
            if command in EXPECTED_FAILURE and len(sides) == 2:
                expected += 1
                continue
            errors.append((index, command, "/".join(sides)))
            continue
        if command in EXPECTED_FAILURE:
            unexpected_passes.append((index, command))
            continue
        if not same(left, right):
            problems.append((index, command, left, right))

    for index, command, side in errors:
        print("ERROR %-22s step %3d on the %s side" % (command, index, side))
    for index, command in unexpected_passes:
        print("PASSED %-21s step %3d should fail on both sides"
              % (command, index))
    for index, command, left, right in problems:
        print("DIFF  %-22s\n      tcl    %s\n      python %s" % (command, left, right))

    # Diagnostics are compared as well: a command can return nothing, or
    # match nothing on both sides, and only the warnings and errors say so.
    tcl_problems = diagnostics(tcl_output)
    python_problems = diagnostics(python_output)
    if tcl_problems != python_problems:
        print("DIFF  diagnostics")
        for line in unified(tcl_problems, python_problems):
            print("      " + line)
    elif tcl_problems:
        print("\n%d warning/error line(s), the same on both sides:" % len(tcl_problems))
        for line in tcl_problems:
            print("  " + line)

    only_tcl = sorted(set(tcl_files) - set(python_files))
    only_python = sorted(set(python_files) - set(tcl_files))
    file_diffs = []
    for name in sorted(set(tcl_files) & set(python_files)):
        if tcl_files[name] != python_files[name]:
            file_diffs.append(name)

    for name in only_tcl:
        print("FILE  %-22s only tcl wrote it" % name)
    for name in only_python:
        print("FILE  %-22s only python wrote it" % name)
    for name in file_diffs:
        offset = next((i for i, (a, b) in enumerate(zip(tcl_files[name],
                                                        python_files[name]))
                       if a != b), min(len(tcl_files[name]), len(python_files[name])))
        print("FILE  %-22s differs at byte %d (%d vs %d bytes)"
              % (name, offset, len(tcl_files[name]), len(python_files[name])))
    if not (only_tcl or only_python or file_diffs):
        print("%d written file(s), byte-identical on both sides" % len(tcl_files))

    print("\n%d step(s): %d differ, %d errored, %d missing from python, %d from tcl"
          % (len(STEPS), len(problems), len(errors), len(lost_python), len(lost_tcl)))

    if expected:
        print("\n%d step(s) failed on both sides, as expected:" % expected)
        for name in sorted({command for command, _ in STEPS
                            if command in EXPECTED_FAILURE}):
            print("  %-22s %s" % (name, EXPECTED_FAILURE[name]))

    unbound, missing = coverage_problems()
    if unbound:
        print("\nthe Tcl front end has these and Python does not (%d):" % len(unbound))
        for start_at in range(0, len(unbound), 6):
            print("  " + " ".join("%-22s" % n for n in unbound[start_at:start_at + 6]))
    if missing:
        print("\nnot exercised by this table (%d):" % len(missing))
        for start_at in range(0, len(missing), 6):
            print("  " + " ".join("%-22s" % n for n in missing[start_at:start_at + 6]))
    if not (unbound or missing):
        print("every command of the Tcl front end is bound and exercised")

    # A side that stopped early is a crash, not a pass: the steps after it
    # were never run, so there is nothing to compare.
    failed = bool(problems or errors or unexpected_passes or unbound or missing
                  or lost_python or lost_tcl
                  or tcl_problems != python_problems
                  or only_tcl or only_python or file_diffs)
    return 1 if failed else 0


def unified(left, right):
    """A readable line diff without pulling in difflib, which reports fuzzily."""
    import difflib
    return list(difflib.unified_diff(left, right, "tcl", "python", lineterm="", n=2))


if __name__ == "__main__":
    sys.exit(main())
