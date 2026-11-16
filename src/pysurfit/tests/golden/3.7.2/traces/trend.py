# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_trend')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.pnts_read('data/7points.txt', '7points')
surfit.curv_read('data/1fault2.txt', '1fault2')
surfit.curv_read('data/1fault.txt', '1fault')
surfit.surf_load('data/func.func', 'test_func')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.2)
surfit.points('7points')
surfit.fault('1fault')
surfit.fault('1fault2')
surfit.trend(1, 10, 'test_func')
surfit.surfit()
surfit.surf_save('trend.dat', 'map_trend')
