# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_surface_ineq')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.surf_load('data/func.func', 'test_func')
surfit.surf_plus_value(80, 'test_func')
surfit.surf_setName('test_func_geq', 'test_func')
surfit.surf_load('data/func.func', 'test_func')
surfit.surf_plus_value(90, 'test_func')
surfit.surf_setName('test_func_leq', 'test_func')
surfit.pnts_read('data/7points.txt', '7points')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.2)
surfit.surface_geq('test_func_geq')
surfit.points('7points')
surfit.completer(2, 1)
surfit.surfit()
surfit.surf_save('surface_ineq.dat', 'map_surface_ineq')
