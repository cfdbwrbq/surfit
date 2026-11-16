# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_curv_surf_ineq')
surfit.set_solver('cg')
surfit.set_tol(0.0001)
surfit.curv_read('data/spiral2.xy', 'spiral2')
surfit.curv_read('data/spiral.xy', 'spiral')
surfit.surf_load('data/func.func', 'test_func')
surfit.grid()
surfit.curve_surf_leq('test_func', 'spiral')
surfit.curve_surf_geq('test_func', 'spiral2')
surfit.completer()
surfit.surfit()
surfit.surf_save('curve_surf_ineq.dat', 'map_curv_surf_ineq')
