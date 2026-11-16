# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_surface')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.surf_load('data/func.func', 'test_func')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.2)
surfit.surface('test_func')
surfit.completer()
surfit.surfit()
surfit.surf_save('surface.dat', 'map_surface')
