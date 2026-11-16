# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_cntr_ineq')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.cntr_read('data/cntr_big_circle2.xyz', 'cntr_big_circle2')
surfit.cntr_read('data/cntr_big_circle.xyz', 'cntr_big_circle')
surfit.cntr_read('data/cntr_center2.xyz', 'cntr_center2')
surfit.cntr_read('data/cntr_center.xyz', 'cntr_center')
surfit.cntr_read('data/cntr_small_circle2.xyz', 'cntr_small_circle2')
surfit.cntr_read('data/cntr_small_circle.xyz', 'cntr_small_circle')
surfit.grid_get(-1000, 1000, 20, -1000, 1000, 20)
surfit.contour_geq('cntr_big_circle')
surfit.contour_leq('cntr_big_circle2')
surfit.contour_geq('cntr_center')
surfit.contour_leq('cntr_center2')
surfit.contour_geq('cntr_small_circle')
surfit.contour_leq('cntr_small_circle2')
surfit.completer()
surfit.surfit()
surfit.surf_save('contour_ineq.dat', 'map_cntr_ineq')
