# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_mask_mean')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.pnts_read('data/points.txt', 'points')
surfit.mask_load('data/mask.mask', 'test_mask')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.4)
surfit.mask_mean(-2, 'test_mask')
surfit.points('points')
surfit.completer(1, 10)
surfit.surfit()
surfit.surf_save('mask_mean.dat', 'map_mask_mean')
