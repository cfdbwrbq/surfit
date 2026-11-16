# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_ineq')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.pnts_read('data/7points.txt', '7points')
surfit.grid()
surfit.leq(120)
surfit.geq(80)
surfit.points('7points')
surfit.completer()
surfit.surfit()
surfit.surf_save('ineq.dat', 'map_ineq')
