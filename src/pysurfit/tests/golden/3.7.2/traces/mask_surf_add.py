# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_mask_surf_add')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.mask_load('data/mask.mask', 'test_mask')
surfit.surf_load('data/func.func', 'test_func')
surfit.grid_get(-10, 10, 0.2, -10, 10, 0.4)
surfit.completer()
surfit.mask_surf_add('test_func', 1, 'test_mask')
surfit.surfit()
surfit.surf_save('mask_surf_add.dat', 'map_mask_surf_add')
