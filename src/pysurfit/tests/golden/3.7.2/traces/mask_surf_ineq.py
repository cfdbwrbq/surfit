# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_mask_surf_ineq')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.mask_load('data/mask.mask', 'test_mask')
surfit.surf_load('data/func.func', 'test_func')
surfit.pnts_read('data/points.txt', 'points')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.4)
surfit.points('points')
surfit.mask_surf_leq('test_func', 'test_mask')
surfit.completer()
surfit.surfit()
surfit.surf_save('mask_surf_ineq.dat', 'map_mask_surf_ineq')
