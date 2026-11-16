# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_mask_completer')
surfit.set_solver('cg')
surfit.set_tol(1e-07)
surfit.pnts_read('data/points.txt', 'points')
surfit.mask_load('data/mask.mask', 'test_mask')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.4)
surfit.points('points')
surfit.mask_completer('test_mask', 1, 2, 30, 2)
surfit.completer()
surfit.surfit()
surfit.surf_save('mask_completer.dat', 'map_mask_completer')
