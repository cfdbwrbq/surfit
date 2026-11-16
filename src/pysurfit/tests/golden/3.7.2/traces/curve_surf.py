# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_curv_surf')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.curv_read('data/spiral.xy', 'spiral')
surfit.curv_read('data/spiral2.xy', 'spiral2')
surfit.surf_load('data/func.func', 'test_func')
surfit.grid()
surfit.curve_surf('test_func', 'spiral')
surfit.completer()
surfit.curve_surf_add('test_func', 0.5, 'spiral2')
surfit.surfit()
surfit.surf_save('curve_surf.dat', 'map_curv_surf')
