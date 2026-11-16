# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_area_ineq')
surfit.set_tol(1e-06)
surfit.area_read('data/area1.txt', 'area1')
surfit.area_read('data/area2.txt', 'area2')
surfit.area_read('data/area3.txt', 'area3')
surfit.area_read('data/area4.txt', 'area4')
surfit.area_read('data/area5.txt', 'area5')
surfit.area_read('data/area6.txt', 'area6')
surfit.grid_get(-12, 12, 0.2, -12, 12, 0.2)
surfit.area(30, 'area3')
surfit.area_leq(20, 'area6')
surfit.area_geq(15, 'area6')
surfit.area(10, 'area1')
surfit.area('undef', 'area5')
surfit.completer(1, 0)
surfit.area_add(20, 0.07, 'area2')
surfit.area_add(40, 0.07, 'area4')
surfit.surfit()
surfit.surf_save('area_ineq.dat', 'map_area_ineq')
