# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_area_surf')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.area_read('data/area1.txt', 'area1')
surfit.area_read('data/area2.txt', 'area2')
surfit.area_read('data/area3.txt', 'area3')
surfit.area_read('data/area4.txt', 'area4')
surfit.area_read('data/area6.txt', 'area6')
surfit.surf_load('data/func.func', 'test_func')
surfit.grid_get(-12, 12, 0.2, -12, 12, 0.2)
surfit.area_surf('test_func', 'area6')
surfit.completer()
surfit.area_surf_add('test_func', 0.07, 'area1')
surfit.area_surf_add('test_func', 0.1, 'area2')
surfit.area_surf_add('test_func', 0.1, 'area3')
surfit.area_surf_add('test_func', 0.05, 'area4')
surfit.surfit()
surfit.surf_save('area_surf.dat', 'map_area_surf')
