# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_mean')
surfit.set_solver('cg')
surfit.set_tol(1e-06)
surfit.pnts_read('data/7points.txt', '7points')
surfit.grid_get(-10, 10, 0.1, -10, 10, 0.1)
surfit.points('7points')
surfit.mean(30, 0)
surfit.completer()
surfit.surfit()
surfit.surf_save('mean.dat', 'map_mean')
