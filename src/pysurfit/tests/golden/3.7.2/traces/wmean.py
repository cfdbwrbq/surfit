# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_wmean')
surfit.set_solver('cg')
surfit.set_tol(1e-06)
surfit.pnts_read('data/7points.txt', '7points')
surfit.surf_load('data/func.func', 'test_func')
surfit.grid_get(-10, 10, 0.1, -10, 10, 0.1)
surfit.points('7points')
surfit.wmean(30, 'test_func', 0)
surfit.completer()
surfit.surfit()
surfit.surf_save('wmean.dat', 'map_wmean')
