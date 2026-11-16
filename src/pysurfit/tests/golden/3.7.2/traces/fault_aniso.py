# Generated from Tcl by run_tcl_suite.py --write-python.
# The original front end is no longer needed to run this script.
import os
import surfit
os.chdir(os.path.dirname(os.path.abspath(__file__)))

surfit.clear_data()
surfit.set_map_name('map_faults_aniso')
surfit.set_solver('cg')
surfit.set_tol(1e-05)
surfit.pnts_read('data/11points.txt', '11points')
surfit.curv_read('data/flt_line1.txt', 'flt_line1')
surfit.curv_read('data/flt_line2.txt', 'flt_line2')
surfit.curv_read('data/flt_line3.txt', 'flt_line3')
surfit.curv_read('data/flt_line4.txt', 'flt_line4')
surfit.grid_get(1, 99, 1, -50, 50, 1)
surfit.points('11points')
surfit.fault('flt_line1')
surfit.fault('flt_line2')
surfit.fault('flt_line3')
surfit.fault('flt_line4')
surfit.completer(0.5, 2, 45, 2)
surfit.surfit()
surfit.surf_save('fault_aniso.dat', 'map_faults_aniso')
