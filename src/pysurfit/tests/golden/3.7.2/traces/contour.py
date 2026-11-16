# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_cntr')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.cntr_read('data/cntr_small_circle.xyz', 'cntr_small_circle')
surfit.cntr_read('data/cntr_big_circle.xyz', 'cntr_big_circle')
surfit.cntr_read('data/cntr_center.xyz', 'cntr_center')
surfit.grid_get(-1000, 1000, 20, -1000, 1000, 20)
surfit.contour('cntr_small_circle')
surfit.contour('cntr_center')
surfit.completer()
surfit.contour_add(0.5, 'cntr_big_circle')
surfit.surfit()
surfit.surf_save('contour.dat', 'map_cntr')
