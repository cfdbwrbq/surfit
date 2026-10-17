/*------------------------------------------------------------------------------
 *	Python bindings for the globe (DEM) and freeflow (LCM) modules.
 *
 *	In the Tcl front end these are two more shared libraries, loaded with
 *	`load libglobe[info sharedlibextension]` and the same for libfreeflow.
 *	Each declares its commands in the same C++ API layer the core uses, and
 *	each registers a data manager that lets file_save and file_load carry its
 *	objects.  Python has no plugin loader, so the extension links both
 *	libraries and registers them when the module is imported, which is the
 *	same order a Tcl script loads the plugins in.
 *
 *	The defaults below are the ones in the C++ headers, not the ones in the
 *	.interface files: the checked-in Tcl wrappers were generated from the
 *	headers, so a call with an omitted argument uses the header's default.  A
 *	python front end that used the .i default would answer differently.
 *
 *	Licensed under the GNU General Public License, version 2, like the rest of
 *	surfit.
 *----------------------------------------------------------------------------*/

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <cstdint>
#include <string>

// The export/visibility macros live in these headers and must come first,
// exactly as in every core translation unit.
#include "sstuff_ie.h"
#include "surfit_ie.h"
#include "globe_ie.h"
#include "flow_ie.h"

#include "bind_common.h"

#include "real.h"

// globe: the digital elevation model
#include "dem.h"
#include "globe.h"
#include "globe_variables.h"
#include "dem_tcl.h"
#include "dems_tcl.h"
#include "globe_surf_tcl.h"

// freeflow: the law-of-conservation-of-mass rules
#include "flow_variables.h"
#include "flow_points_tcl.h"
#include "flow_curvs_tcl.h"
#include "flow_surf_tcl.h"
#include "f_lcm_simple_tcl.h"

namespace py = pybind11;

using surfit_py::cstr_or_empty;
using surfit_py::drain_boolvec;
using surfit_py::drain_intvec;
using surfit_py::drain_strvec;
using surfit_py::drain_vec;
using surfit_py::opt_cstr;

void bind_globe(py::module_ & m) {
	// The Tcl plugin does this from %init; on the Python side the module is
	// already loaded, so the manager has to be registered here.
	surfit::globe_init_variables();

	// --- rules over DEMs ------------------------------------------------
	m.def("dem", [](const std::string & name) {
		return drain_boolvec(surfit::dem(name.c_str()));
	}, py::arg("dem_name") = "*",
	   "rule: the surface approximates the DEM in least squares");
	m.def("dem_add", [](double weight, const std::string & name) {
		return drain_boolvec(surfit::dem_add(REAL(weight), name.c_str()));
	}, py::arg("weight"), py::arg("dem_name") = "*",
	   "rule: add a weighted approximation of the DEM to the previous rule");

	// --- loading and saving ---------------------------------------------
	// A loader's second argument is a name *inside* the file, not a new name,
	// exactly as for the core's own loaders.
	m.def("dem_load", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(
			surfit::dem_load(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("filename"), py::arg("dem_name") = py::none(),
	   "load a DEM from a surfit datafile");
	m.def("dem_load_grd", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(
			surfit::dem_load_grd(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("filename"), py::arg("dem_name") = py::none(),
	   "load a DEM from a Surfer GRD-ASCII file");
	m.def("dem_load_dtm", [](const std::string & hdr, const std::string & name,
	                         py::object binary) {
		std::string storage;
		return drain_boolvec(
			surfit::dem_load_dtm(hdr.c_str(), name.c_str(),
			                     opt_cstr(binary, storage)));
	}, py::arg("hdr_filename"), py::arg("name"),
	   py::arg("bin_filename") = py::none(),
	   "load a DEM from a DTM header, with the binary as a separate file");
	m.def("dem_load_hgt", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(
			surfit::dem_load_hgt(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("hgt_filename"), py::arg("dem_name") = py::none(),
	   "load a DEM from an SRTM HGT file");
	m.def("dem_load_hgt_zip", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(
			surfit::dem_load_hgt_zip(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("hgt_filename"), py::arg("dem_name") = py::none(),
	   "load a DEM from a zipped SRTM HGT file (needs zlib)");
	m.def("dem_load_globe", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(
			surfit::dem_load_globe(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("filename"), py::arg("dem_name") = py::none(),
	   "load a DEM from a GTOPO30 tile");

	m.def("dem_save", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surfit::dem_save(path.c_str(), name.c_str()));
	}, py::arg("filename"), py::arg("dem_name") = "*",
	   "write DEMs to a surfit datafile");
	m.def("dem_save_grd", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surfit::dem_save_grd(path.c_str(), name.c_str()));
	}, py::arg("filename"), py::arg("dem_name") = "*",
	   "write DEMs as Surfer GRD-ASCII");
	m.def("dem_save_xyz", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surfit::dem_save_xyz(path.c_str(), name.c_str()));
	}, py::arg("filename"), py::arg("dem_name") = "*",
	   "write DEMs as XYZ text");
	m.def("dem_save_dtm", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surfit::dem_save_dtm(path.c_str(), name.c_str()));
	}, py::arg("filename"), py::arg("dem_name") = "*",
	   "write DEMs as a DTM header plus binary");

	// --- arithmetic and statistics --------------------------------------
	m.def("dem_getValue", [](double x, double y, const std::string & name) {
		return drain_vec(surfit::dem_getValue(REAL(x), REAL(y), name.c_str()));
	}, py::arg("x"), py::arg("y"), py::arg("dem_name") = "*",
	   "DEM value at a point, one per matching DEM");
	m.def("dem_D1", [](const std::string & name) {
		return drain_vec(surfit::dem_D1(name.c_str()));
	}, py::arg("dem_name") = "*", "approximation term of the DEM");
	m.def("dem_D2", [](const std::string & name) {
		return drain_vec(surfit::dem_D2(name.c_str()));
	}, py::arg("dem_name") = "*", "roughness term of the DEM");
	m.def("dem_minz", [](const std::string & name) {
		return drain_vec(surfit::dem_minz(name.c_str()));
	}, py::arg("dem_name") = "*");
	m.def("dem_maxz", [](const std::string & name) {
		return drain_vec(surfit::dem_maxz(name.c_str()));
	}, py::arg("dem_name") = "*");
	m.def("dem_resid", [](const std::string & path, const std::string & name,
	                      const std::string & points_name) {
		return drain_boolvec(surfit::dem_resid(path.c_str(), name.c_str(),
		                                       points_name.c_str()));
	}, py::arg("filename"), py::arg("dem_name") = "*",
	   py::arg("points_name") = "*",
	   "residuals between points and the DEM, written to a text file");

	m.def("dem_gradient", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::dem_gradient(new_name.c_str(), name.c_str()));
	}, py::arg("newname"), py::arg("dem_name") = "*",
	   "a new DEM holding the gradient of the matched ones");
	m.def("dem_project", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::dem_project(new_name.c_str(), name.c_str()));
	}, py::arg("newname"), py::arg("dem_name") = "*",
	   "project the matched DEMs onto the target grid, as a new DEM");

	m.def("dem_plus", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::dem_plus(first.c_str(), second.c_str()));
	}, py::arg("dem1_name"), py::arg("dem2_name"));
	m.def("dem_minus", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::dem_minus(first.c_str(), second.c_str()));
	}, py::arg("dem1_name"), py::arg("dem2_name"));
	m.def("dem_mult", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::dem_mult(first.c_str(), second.c_str()));
	}, py::arg("dem1_name"), py::arg("dem2_name"));
	m.def("dem_div", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::dem_div(first.c_str(), second.c_str()));
	}, py::arg("dem1_name"), py::arg("dem2_name"));
	m.def("dem_set", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::dem_set(first.c_str(), second.c_str()));
	}, py::arg("dem1_name"), py::arg("dem2_name"));
	m.def("dem_plus_real", [](double val, const std::string & name) {
		return drain_boolvec(surfit::dem_plus_real(REAL(val), name.c_str()));
	}, py::arg("val"), py::arg("dem_name") = "*");
	m.def("dem_minus_real", [](double val, const std::string & name) {
		return drain_boolvec(surfit::dem_minus_real(REAL(val), name.c_str()));
	}, py::arg("val"), py::arg("dem_name") = "*");
	m.def("dem_mult_real", [](double val, const std::string & name) {
		return drain_boolvec(surfit::dem_mult_real(REAL(val), name.c_str()));
	}, py::arg("val"), py::arg("dem_name") = "*");
	m.def("dem_div_real", [](double val, const std::string & name) {
		return drain_boolvec(surfit::dem_div_real(REAL(val), name.c_str()));
	}, py::arg("val"), py::arg("dem_name") = "*");
	m.def("dem_set_real", [](double val, const std::string & name) {
		return drain_boolvec(surfit::dem_set_real(REAL(val), name.c_str()));
	}, py::arg("val"), py::arg("dem_name") = "*");

	// --- wavelets --------------------------------------------------------
	m.def("dem_get_details_level", [](const std::string & name) {
		return drain_intvec(surfit::dem_get_details_level(name.c_str()));
	}, py::arg("dem_name") = "*");
	m.def("dem_decomp", [](const std::string & name) {
		return drain_boolvec(surfit::dem_decomp(name.c_str()));
	}, py::arg("dem_name") = "*", "one wavelet decomposition step");
	m.def("dem_auto_decomp", [](double eps, const std::string & name) {
		return drain_boolvec(surfit::dem_auto_decomp(REAL(eps), name.c_str()));
	}, py::arg("eps"), py::arg("dem_name") = "*",
	   "decompose until the details fall below eps");
	m.def("dem_recons", [](const std::string & name) {
		return drain_boolvec(surfit::dem_recons(name.c_str()));
	}, py::arg("dem_name") = "*", "one wavelet reconstruction step");
	m.def("dem_full_recons", [](const std::string & name) {
		return drain_boolvec(surfit::dem_full_recons(name.c_str()));
	}, py::arg("dem_name") = "*", "reconstruct all levels");

	// --- conversion to the other object types ---------------------------
	m.def("dem_to_pnts", [](const std::string & name) {
		return drain_boolvec(surfit::dem_to_pnts(name.c_str()));
	}, py::arg("dem_name") = "*", "make a point set out of every DEM value");
	m.def("dem_to_surf", [](const std::string & name) {
		return drain_boolvec(surfit::dem_to_surf(name.c_str()));
	}, py::arg("dem_name") = "*", "make a surface out of the DEM");
	m.def("dem_to_mask", [](int true_from, int true_to, const std::string & name) {
		return drain_boolvec(surfit::dem_to_mask(short(true_from),
		                                         short(true_to), name.c_str()));
	}, py::arg("true_from"), py::arg("true_to"), py::arg("dem_name") = "*",
	   "make a mask where the DEM value lies between the two bounds");
	// The C++ default is the position "0", not the pattern "*": the checked-in
	// Tcl wrapper calls the header's default, so `surf_to_dem` with no
	// argument matches a surface literally named "0".  The same here, or the
	// two front ends would answer differently.
	m.def("surf_to_dem", [](const std::string & name) {
		return drain_boolvec(surfit::surf_to_dem(name.c_str()));
	}, py::arg("surface_name") = "0", "make a DEM out of the surface");

	// --- the DEM collection ---------------------------------------------
	m.def("dem_getCountX", [](const std::string & name) {
		return drain_intvec(surfit::dem_getCountX(name.c_str()));
	}, py::arg("dem_name") = "*", "cell count of each matching DEM in X");
	m.def("dem_getCountY", [](const std::string & name) {
		return drain_intvec(surfit::dem_getCountY(name.c_str()));
	}, py::arg("dem_name") = "*", "cell count of each matching DEM in Y");
	m.def("dem_getStepX", [](const std::string & name) {
		return drain_vec(surfit::dem_getStepX(name.c_str()));
	}, py::arg("dem_name") = "*", "cell size of each matching DEM in X");
	m.def("dem_getStepY", [](const std::string & name) {
		return drain_vec(surfit::dem_getStepY(name.c_str()));
	}, py::arg("dem_name") = "*", "cell size of each matching DEM in Y");
	m.def("dem_undef", [](double value, const std::string & name) {
		return drain_boolvec(surfit::dem_undef(REAL(value), name.c_str()));
	}, py::arg("new_undef_value"), py::arg("dem_name") = "*",
	   "treat cells holding this value as undefined");
	m.def("dem_getName", [](const std::string & name) {
		return drain_strvec(surfit::dem_getName(name.c_str()));
	}, py::arg("dem_name") = "*", "names of the matching DEMs");
	m.def("dem_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::dem_getNameAt(pos));
	}, py::arg("pos"), "name of the DEM at that position; empty if there is none");
	m.def("dem_getId", [](const std::string & name) {
		return drain_intvec(surfit::dem_getId(name.c_str()));
	}, py::arg("dem_name") = "*", "ids of the matching DEMs");
	m.def("dem_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::dem_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("dem_name") = "*");
	m.def("dem_del", [](const std::string & name) {
		surfit::dem_del(name.c_str());
	}, py::arg("dem_name") = "*", "unload DEMs");
	m.def("dem_size", &surfit::dem_size, "number of DEMs in memory");
	m.def("dems_info", []() { surfit::dems_info(); }, "print the DEMs in memory");
}

void bind_freeflow(py::module_ & m) {
	// As for globe: the Tcl plugin registers this from %init.
	surfit::freeflow_init_variables();

	// --- the rules ------------------------------------------------------
	m.def("flow_points", [](const std::string & name) {
		return drain_boolvec(surfit::flow_points(name.c_str()));
	}, py::arg("points_name") = "*",
	   "flow through points: the surface is a potential, points are its values");
	m.def("flow_area", [](double value, const std::string & name) {
		return drain_boolvec(surfit::flow_area(REAL(value), name.c_str()));
	}, py::arg("value"), py::arg("area_name") = "*",
	   "constant flow inside an area");
	m.def("flow_curve", [](double value, const std::string & name) {
		return drain_boolvec(surfit::flow_curve(REAL(value), name.c_str()));
	}, py::arg("value"), py::arg("curve_name") = "*",
	   "constant flow along a curve");
	m.def("flow_contour", [](const std::string & name) {
		return drain_boolvec(surfit::flow_contour(name.c_str()));
	}, py::arg("contour_name") = "*",
	   "flow through the points of a contour");

	// --- conservation of mass -------------------------------------------
	m.def("lcm_simple", [](double permeability, double viscosity,
	                       double multiplier) {
		return surfit::lcm_simple(REAL(permeability), REAL(viscosity),
		                          REAL(multiplier));
	}, py::arg("permeability") = 1, py::arg("viscosity") = 1,
	   py::arg("multiplier") = 1,
	   "rule: conservation of mass with constant permeability and viscosity");
	m.def("lcm_simple_add", [](double weight, double permeability,
	                           double viscosity, double multiplier) {
		return surfit::lcm_simple_add(REAL(weight), REAL(permeability),
		                              REAL(viscosity), REAL(multiplier));
	}, py::arg("weight"), py::arg("permeability") = 1,
	   py::arg("viscosity") = 1, py::arg("multiplier") = 1);

	// --- statistics ------------------------------------------------------
	m.def("surf_debit", [](double x, double y, double permeability,
	                       double viscosity, double multiplier,
	                       const std::string & name) {
		return drain_vec(surfit::surf_debit(REAL(x), REAL(y),
		                                    REAL(permeability), REAL(viscosity),
		                                    REAL(multiplier), name.c_str()));
	}, py::arg("x"), py::arg("y"), py::arg("perm"), py::arg("visc"),
	   py::arg("mult"), py::arg("surface_name") = "*",
	   "flow rate through one cell of the surface");
	m.def("surf_debit_rect", [](double x1, double y1, double x2, double y2,
	                            double permeability, double viscosity,
	                            double multiplier, const std::string & name) {
		return drain_vec(surfit::surf_debit_rect(
			REAL(x1), REAL(y1), REAL(x2), REAL(y2), REAL(permeability),
			REAL(viscosity), REAL(multiplier), name.c_str()));
	}, py::arg("x1"), py::arg("y1"), py::arg("x2"), py::arg("y2"),
	   py::arg("perm"), py::arg("visc"), py::arg("mult"),
	   py::arg("surface_name") = "*",
	   "flow rate through a rectangle of the surface");

	// --- the DEM container of one task -----------------------------------
	// The DEM commands work on one container; a Session creates its own, so
	// two tasks can load different rasters under the same name.  The handles
	// are opaque, like state_create(), and the Python side owns the lifetime.
	m.def("globe_dems_create", []() {
		return reinterpret_cast<std::uintptr_t>(surfit::globe_dems_create());
	}, "a new empty DEM container, as a handle");
	m.def("globe_dems_install", [](std::uintptr_t handle) {
		surfit::globe_dems_install(
			reinterpret_cast<surfit::dems_container *>(handle));
	}, py::arg("handle"), "makes that DEM container the active one");
	m.def("globe_dems_origin", []() {
		return reinterpret_cast<std::uintptr_t>(surfit::globe_dems_origin());
	}, "the library's own DEM container, as a handle");
	m.def("globe_dems_release", [](std::uintptr_t handle) {
		surfit::globe_dems_release(
			reinterpret_cast<surfit::dems_container *>(handle));
	}, py::arg("handle"), "frees a DEM container and its DEMs");
}
