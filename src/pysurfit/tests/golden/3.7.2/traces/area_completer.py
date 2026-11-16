# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_area_completer')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.pnts_read('data/11points.txt', '11points')
surfit.area_read('data/some_area.txt', 'some_area')
surfit.grid()
surfit.points('11points')
surfit.area_completer('some_area', 1, 2, 30, 2, 1)
surfit.completer()
surfit.surfit()
surfit.surf_save('area_completer.dat', 'map_area_completer')
