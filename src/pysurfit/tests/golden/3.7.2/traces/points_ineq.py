# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_points_ineq')
surfit.set_tol(0.0001)
surfit.pnts_read('data/points_geq.txt', 'points_geq')
surfit.pnts_read('data/points_leq.txt', 'points_leq')
surfit.grid()
surfit.points_geq('points_geq')
surfit.points_leq('points_leq')
surfit.completer(0, 1)
surfit.surfit()
surfit.surf_save('points_ineq.dat', 'map_points_ineq')
