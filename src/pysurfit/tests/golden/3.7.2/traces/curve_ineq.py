# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_curve_ineq')
surfit.set_solver('cg')
surfit.set_tol(5e-05)
surfit.curv_read('data/iso1.xy', 'iso1')
surfit.curv_read('data/iso2.xy', 'iso2')
surfit.curv_read('data/iso3.xy', 'iso3')
surfit.curv_read('data/iso4.xy', 'iso4')
surfit.grid(10, 10)
surfit.curve_leq(10, 'iso1')
surfit.curve_geq(50, 'iso3')
surfit.curve_leq(30, 'iso4')
surfit.curve_leq(40, 'iso2')
surfit.completer(1, 1.6)
surfit.surfit()
surfit.surf_save('curve_ineq.dat', 'map_curve_ineq')
