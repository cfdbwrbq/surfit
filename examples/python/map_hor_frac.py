"""The map_hor_frac example -- examples/freeflow/press2/map_hor_frac.tcl.

    python3 examples/python/map_hor_frac.py

A real pressure field from the Arigol oilfield, with the measured pressures,
rates, impermeable zones and faults, plus a horizontal fracture line.  The
script prints the debit, the pressure at one well, their residuals against the
measured values, and the roughness of the result, so the horizontal and vertical
fracture directions can be compared.
"""
import os
import sys

sys.path.insert(0, os.environ.get("SURFIT_BIN", ""))

import surfit  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, os.pardir, "freeflow", "press2")
DAY = 24 * 3600

#: Measured values the script is checked against.
DEBIT = -40.3844832
PRESSURE = 12.0


def build():
    """Solves the example and returns the session."""
    task = surfit.Session(map_name="map_hor_frac", tol=1e-7)

    assert all(task.pnts_read(os.path.join(DATA, "PZab_2001.txt"),
                              "press2001", col1=4, col2=3, col3=5))
    assert all(task.pnts_mult_real(0.1013, "press2001"))   # atm -> MPa
    assert all(task.cntr_read(os.path.join(DATA, "lines", "P_2001_236_hor.txt"),
                              "P_2001_236_hor"))
    assert all(task.cntr_mult_real(0.1013))                # atm -> MPa

    assert all(task.pnts_read(os.path.join(DATA, "Q_2001.txt"),
                              "debits2001", col1=4, col2=3, col3=5))
    assert all(task.pnts_mult_real(-1, "debits2001"))      # injector sign

    for name in ("VNK1", "VNK2", "VNK3"):
        assert all(task.curv_read(os.path.join(DATA, "%s.txt" % name), name,
                                  col1=2, col2=1))
    assert all(task.area_read(os.path.join(DATA, "ZAM1.txt"), "ZAM1",
                              col1=2, col2=1))
    assert all(task.curv_read(os.path.join(DATA, "ZAM2.txt"), "ZAM2",
                              col1=2, col2=1))
    assert all(task.area_read(os.path.join(DATA, "ZAM5.txt"), "ZAM5",
                              col1=2, col2=1))
    assert all(task.curv_read(os.path.join(DATA, "lines", "frac_236_hor.txt"),
                              "frac_236_hor"))

    task.grid(28300, 41400, 30, 45500, 64700, 30)

    task.points("press2001")
    for name in ("VNK1", "VNK2", "VNK3"):
        task.curve(21.4, name)
    task.area("undef", "ZAM1")
    task.area("undef", "ZAM5")
    task.fault("ZAM2")

    task.lcm_simple(16.4, 0.5, 1e-6)
    task.contour_add(1, "P_2001_236_hor")
    task.flow_points("debits2001")
    task.flow_curve(-0.000467413, "frac_236_hor")

    task.solve()
    task.grid_unload()
    return task


def main():
    task = build()
    task.file_save("map_hor_frac.dat")

    debit = DAY * task.surf_debit_rect(34000, 57600, 36000, 59200,
                                       16.4, 0.5, 1e-6)[0]
    pressure = task.surf_getValue(34967, 58314)[0]
    grid = task.values()
    defined = surfit.defined_mask(grid)
    print("saved map_hor_frac.dat, grid %s, %d of %d nodes defined"
          % (grid.shape, defined.sum(), grid.size))
    print("min=%.4f max=%.4f mean=%.4f"
          % (grid[defined].min(), grid[defined].max(), grid[defined].mean()))
    print("debit %.6f (residual %.6f)" % (debit, debit - DEBIT))
    print("pressure %.6f (residual %.6f)"
          % (pressure, pressure - PRESSURE))
    print("roughness (surf_D1) %.6g" % task.surf_D1()[0])


if __name__ == "__main__":
    main()
