/*------------------------------------------------------------------------------
 *	Python bindings for the surfit core (stage L1).
 *
 *	This module reuses the existing C++ API layer -- the same free functions
 *	that SWIG turns into Tcl commands -- so the Python and Tcl front ends
 *	drive exactly the same code path.  Whatever is Tcl-ish about that layer
 *	(name globs, the global data manager, the single global grid) is a known
 *	L1/L2 refactoring target, see PORT_TO_PYTHON.md.
 *
 *	Licensed under the GNU General Public License, version 2, like the rest
 *	of surfit.
 *----------------------------------------------------------------------------*/

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <pybind11/stl.h>

#include <cfloat>
#include <cstdlib>
#include <cstring>
#include <string>

// The export/visibility macros live in these two headers and must come first,
// exactly as in every core translation unit.
#include "sstuff_ie.h"
#include "surfit_ie.h"

#include "real.h"
#include "vec.h"
#include "boolvec.h"
#include "fileio.h"
#include "interp.h"

#include "other_tcl.h"
#include "others_tcl.h"
#include "f_points_tcl.h"
#include "surfs_tcl.h"
#include "grid_tcl.h"
#include "grid.h"
#include "solvers.h"
#include "pnts_tcl.h"
#include "curv_tcl.h"
#include "cntr_tcl.h"
#include "mask_tcl.h"
#include "area_tcl.h"
#include "curvs_tcl.h"
#include "hist_tcl.h"
#include "surf_tcl.h"
#include "cmofs.h"
#include "variables_tcl.h"
#include "variables.h"
#include "surf.h"

// surfit_io: the file-format plugin.
#include "surfit_io_ie.h"
#include "surfit_io_variables.h"
#include "surfit_io_data_manager.h"
#include "area_io_tcl.h"
#include "cntr_io_tcl.h"
#include "curv_io_tcl.h"
#include "mask_io_tcl.h"
#include "pnts_io_tcl.h"
#include "surf_io_tcl.h"

namespace py = pybind11;

namespace surfit {
/*! Defined in surfit_io_variables.cpp but not declared in any header upstream,
	so the definition is repeated here to let the module register the plugin's
	manager without going through Tcl. */
extern surfit_io_manager * my_surfit_io_manager;
}  // namespace surfit

using surfit::area;
using surfit::area_add;
using surfit::area_read;
using surfit::boolvec;
using surfit::clear_data;
using surfit::completer;
using surfit::create_grid;
using surfit::create_surf;
using surfit::d_grid;
using surfit::d_surf;
using surfit::grid_get;
using surfit::map_name;
using surfit::surf_save;
using surfit::surfit_surfs;
// extvec and create_extvec are macros for vec / create_vec in a normal build.
using surfit::extvec;
using surfit::create_extvec;
// NB: `surfit` itself is not imported by a using-declaration -- the function
// surfit::surfit() would clash with the namespace name in the global scope.

namespace {

/*! Drains a boolvec of per-file success flags and releases it. */
py::list drain_boolvec(boolvec * flags) {
	py::list result;
	if (flags == NULL)
		return result;
	for (size_t i = 0; i < flags->size(); i++)
		result.append(py::bool_((*flags)(i)));
	flags->release();
	return result;
}

/*! Optional-string helper: Python None becomes a NULL C string, matching the
	C++ API, where NULL means "derive the name" or "no name". */
const char * opt_cstr(const py::object & value, std::string & storage) {
	if (value.is_none())
		return NULL;
	storage = std::string(py::str(value));
	return storage.c_str();
}

/*! Registers the surfit_io data manager.

	The Tcl plugin does this in surfit_io_init_variables(), which first calls
	init_surfit_lib() -- and that one evaluates Tcl code, so it cannot run
	without an interpreter.  Everything else it does is reproduced here.
*/
void ensure_io_manager() {
	if (surfit::my_surfit_io_manager != NULL)
		return;
	surfit::my_surfit_io_manager = new surfit::surfit_io_manager;
	surfit::add_manager(surfit::my_surfit_io_manager);
}

/*! Python observer of the core's log messages.

	Deliberately leaked rather than held in a static py::object: a static one
	would be destroyed while the interpreter is finalising, which is a crash
	waiting to happen.  At most one object is ever allocated and it is replaced
	in place.
*/
py::object * log_observer = NULL;

void forward_log_message(int level, const char * message) {
	if (log_observer == NULL || !*log_observer)
		return;
	// writelog() and log_printf() run while surfit() has released the GIL, and
	// possibly on a worker thread, so take it back for the duration of the call.
	py::gil_scoped_acquire acquire;
	try {
		(*log_observer)(level, std::string(message));
	} catch (py::error_already_set & error) {
		// An observer that raises must not take the solve down with it.
		error.discard_as_unraisable(__func__);
	}
}

/*! The core names the resulting surface after the global `map_name`, which the
	Tcl front end exposes as a traced variable.  Here it is an explicit call. */
void set_map_name(const std::string & name) {
	free(map_name);
	map_name = strdup(name.c_str());
}

std::string get_map_name() {
	return map_name != NULL ? std::string(map_name) : std::string();
}

size_t surf_count() {
	return surfit_surfs->size();
}

d_surf * surf_at(size_t pos) {
	if (pos >= surfit_surfs->size())
		throw py::index_error("surface index out of range");
	return (*surfit_surfs)[pos];
}

std::string surf_name_at(size_t pos) {
	const char * name = surf_at(pos)->getName();
	return name != NULL ? std::string(name) : std::string();
}

/*! Copies a surface into a (count_y, count_x) array of doubles. */
py::array_t<double> surf_values(size_t pos) {
	d_surf * srf = surf_at(pos);
	size_t count_x = srf->getCountX();
	size_t count_y = srf->getCountY();

	py::array_t<double> result({count_y, count_x});
	py::buffer_info info = result.request();
	double * row = static_cast<double *>(info.ptr);

	for (size_t j = 0; j < count_y; j++)
		for (size_t i = 0; i < count_x; i++)
			row[j * count_x + i] = static_cast<double>(srf->getValue(j * count_x + i));

	return result;
}

/*! Creates a surface from a (count_y, count_x) float64 array and registers it,
	so it can be used as a trend or an inequality source by the other rules. */
void add_surface(py::array_t<double, py::array::c_style | py::array::forcecast> values,
                 double start_x, double step_x,
                 double start_y, double step_y,
                 const std::string & name) {
	py::buffer_info info = values.request();
	if (info.ndim != 2)
		throw py::value_error("expected a 2-D array shaped (count_y, count_x)");

	size_t count_y = static_cast<size_t>(info.shape[0]);
	size_t count_x = static_cast<size_t>(info.shape[1]);
	if (count_x == 0 || count_y == 0)
		throw py::value_error("surface array must not be empty");

	// d_grid derives its node count from start/end/step, so choose end points
	// that reproduce the array shape exactly: count = (end - start)/step + 1.
	double end_x = start_x + (count_x - 1) * step_x;
	double end_y = start_y + (count_y - 1) * step_y;

	extvec * coeff = create_extvec(count_x * count_y, REAL(0), false);
	const double * src = static_cast<const double *>(info.ptr);
	for (size_t i = 0; i < count_x * count_y; i++)
		(*coeff)(i) = REAL(src[i]);

	d_grid * grd = create_grid(start_x, end_x, step_x,
	                           start_y, end_y, step_y, name.c_str());
	d_surf * srf = create_surf(coeff, grd, name.c_str());
	srf->undef_value = surfit::undef_value;

	surfit_surfs->push_back(srf);
}

/*! Geometry of a surface, in the coordinates of its nodes.
 *
 *	d_surf::getMinX() and getMaxX() return the edges of the outer cells, half
 *	a step beyond the first and last node, so they are corrected here: the
 *	values sit on the nodes, and a caller placing them on a map wants those.
 */
py::dict surf_extent(size_t pos) {
	d_surf * srf = surf_at(pos);
	const double step_x = static_cast<double>(srf->getStepX());
	const double step_y = static_cast<double>(srf->getStepY());
	py::dict extent;
	extent["count_x"] = srf->getCountX();
	extent["count_y"] = srf->getCountY();
	extent["min_x"] = static_cast<double>(srf->getMinX()) + step_x / 2;
	extent["max_x"] = static_cast<double>(srf->getMaxX()) - step_x / 2;
	extent["min_y"] = static_cast<double>(srf->getMinY()) + step_y / 2;
	extent["max_y"] = static_cast<double>(srf->getMaxY()) - step_y / 2;
	extent["step_x"] = step_x;
	extent["step_y"] = step_y;
	return extent;
}

/*! Index of the first surface whose name matches, or -1. */int surf_index(const std::string & name) {
	for (size_t i = 0; i < surfit_surfs->size(); i++) {
		const char * current = (*surfit_surfs)[i]->getName();
		if (current != NULL && name == current)
			return static_cast<int>(i);
	}
	return -1;
}

}  // namespace

PYBIND11_MODULE(_surfit, m) {
	m.doc() = "surfit gridding engine -- C++ core bindings (stage L1)";

	// Registers the file-format plugin, which the Tcl front end would load as
	// a separate shared library.
	ensure_io_manager();

	// Without a Tcl interpreter the core suppresses console output; log_open()
	// still writes the log file.  A real logging bridge is the next L1 step.
	// NB: the log levels are macros, so LOG_MESSAGE cannot be namespace-qualified.
	m.def("log_open", [](int level, const std::string & path) {
		return surfit::log_open(level, path.empty() ? NULL : path.c_str());
	}, py::arg("level") = 1 /* LOG_MESSAGE */, py::arg("path") = std::string());

	m.def("clear_data", &clear_data, "drop all loaded data and gridding rules");

	// Object selection by name is the one thing the engine used to borrow from
	// Tcl; the matcher is local now, and this exposes it so it can be checked
	// against Tcl itself.
	m.def("string_match", [](const std::string & pattern, const std::string & string) {
		return ::StringMatch(pattern.c_str(), string.c_str());
	}, py::arg("pattern"), py::arg("string"),
	   "Tcl-style name matching: *, ?, [sets], backslash escapes");

	// The core reports progress and diagnostics through writelog() and
	// log_printf(); an observer can turn that into a progress bar.
	m.def("set_log_handler", [](py::object handler) {
		if (handler.is_none()) {
			surfit::set_log_hook(NULL);
			return;
		}
		if (log_observer == NULL)
			log_observer = new py::object(handler);
		else
			*log_observer = handler;
		surfit::set_log_hook(forward_log_message);
	}, py::arg("handler"),
	   "call handler(level, message) for every message the core emits");
	m.def("clear_log_handler", []() { surfit::set_log_hook(NULL); },
	      "stop observing the core's messages");
	m.def("set_map_name", &set_map_name, "name given to the resulting surface");
	m.def("map_name", &get_map_name);

	// Global solver settings.  In the Tcl front end these are traced variables
	// (that is why scripts do `set tol 1e-5`).
	m.def("set_tol", [](float value) { surfit::tol = value; },
	      "tolerance for the iterative solver");
	m.def("get_tol", []() { return surfit::tol; });

	m.def("area_read", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(area_read(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("path"), py::arg("name") = py::none());

	// `name` is optional in the C++ API (NULL means "unnamed grid"), so accept
	// None here instead of inventing a name.
	m.def("grid_get", [](double start_x, double end_x, double step_x,
	                     double start_y, double end_y, double step_y,
	                     py::object name) {
		std::string name_str;
		const char * name_ptr = NULL;
		if (!name.is_none()) {
			name_str = py::str(name);
			name_ptr = name_str.c_str();
		}
		return grid_get(start_x, end_x, step_x,
		                start_y, end_y, step_y,
		                name_ptr);
	}, py::arg("start_x"), py::arg("end_x"), py::arg("step_x"),
	   py::arg("start_y"), py::arg("end_y"), py::arg("step_y"),
	   py::arg("name") = py::none());

	// In Tcl every argument is a string, so the value may arrive as a number
	// ("10") or as the literal "undef"; accept both.
	m.def("area", [](const py::object & value, const std::string & name,
	                 int inside) {
		std::string text = std::string(py::str(value));
		return drain_boolvec(area(text.c_str(), name.c_str(), inside));
	}, py::arg("value"), py::arg("name") = "*", py::arg("inside") = 1);

	m.def("area_add", [](double value, double weight, const std::string & name,
	                     int inside) {
		return drain_boolvec(area_add(value, weight, name.c_str(), inside));
	}, py::arg("value"), py::arg("weight"), py::arg("name") = "*",
	   py::arg("inside") = 1);

	m.def("completer", &completer,
	      py::arg("D1") = 1, py::arg("D2") = 2,
	      py::arg("alpha") = 0, py::arg("w") = 1);

	// The solve can run for minutes and touches no Python object, so let the
	// interpreter keep running: other threads (progress reporting, servers)
	// stay responsive.  Calls that build Python results cannot do this, because
	// drain_boolvec() needs the GIL.
	m.def("surfit", []() { surfit::surfit(); }, "run the gridding algorithm",
	      py::call_guard<py::gil_scoped_release>());

	m.def("surf_save", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surf_save(path.c_str(), name.c_str()));
	}, py::arg("path"), py::arg("name") = "*");

	m.def("surf_count", &surf_count, "number of surfaces in memory");
	m.def("surf_name_at", &surf_name_at, py::arg("pos"));
	m.def("surf_index", &surf_index, py::arg("name"),
	      "index of the surface with this exact name, or -1");
	m.def("surf_values", &surf_values, py::arg("pos"),
	      "surface values as a (count_y, count_x) float64 array");
	m.def("surf_extent", &surf_extent, py::arg("pos"),
	      "node counts and extent of a surface, as a dict");
	m.def("add_surface", &add_surface,
	      py::arg("values"), py::arg("start_x"), py::arg("step_x"),
	      py::arg("start_y"), py::arg("step_y"), py::arg("name"),
	      "register a (count_y, count_x) float64 array as a named surface");

	// ---- solvers -----------------------------------------------------------

	m.def("set_solver", &surfit::set_solver, py::arg("short_name"));
	m.def("get_solvers_count", &surfit::get_solvers_count);
	m.def("get_solver_short_name", &surfit::get_solver_short_name, py::arg("pos"));
	m.def("get_current_solver_short_name",
	      &surfit::get_current_solver_short_name);
	m.def("get_current_solver_long_name",
	      &surfit::get_current_solver_long_name);

	// ---- grid sizing -------------------------------------------------------

	m.def("grid", [](double step_x, double step_y, double percent, py::object name) {
		std::string storage;
		return surfit::grid(step_x, step_y, percent, opt_cstr(name, storage));
	}, py::arg("step_x") = 0, py::arg("step_y") = 0,
	   py::arg("percent") = 2, py::arg("name") = py::none(),
	   "derive the grid from the loaded data");

	// ---- data loading ------------------------------------------------------

	m.def("pnts_read", [](const std::string & path, py::object name,
	                      int col1, int col2, int col3, int col4,
	                      const std::string & delimiter, int skip_lines,
	                      int grow_by) {
		std::string storage;
		return drain_boolvec(surfit::pnts_read(path.c_str(), opt_cstr(name, storage),
		                                       col1, col2, col3, col4,
		                                       delimiter.c_str(), skip_lines, grow_by));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("col1") = 1, py::arg("col2") = 2, py::arg("col3") = 3,
	   py::arg("col4") = 0, py::arg("delimiter") = " \t",
	   py::arg("skip_lines") = 0, py::arg("grow_by") = 250);

	m.def("pnts_load", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(surfit::pnts_load(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("path"), py::arg("name") = py::none());

	m.def("curv_read", [](const std::string & path, py::object name,
	                      int col1, int col2, const std::string & delimiter,
	                      int skip_lines, int grow_by) {
		std::string storage;
		return drain_boolvec(surfit::curv_read(path.c_str(), opt_cstr(name, storage),
		                                       col1, col2, delimiter.c_str(),
		                                       skip_lines, grow_by));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("col1") = 1, py::arg("col2") = 2, py::arg("delimiter") = " \t",
	   py::arg("skip_lines") = 0, py::arg("grow_by") = 250);

	m.def("curv_load", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(surfit::curv_load(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("path"), py::arg("name") = py::none());

	m.def("cntr_read", [](const std::string & path, py::object name,
	                      int col1, int col2, int col3,
	                      const std::string & delimiter, int skip_lines,
	                      int grow_by) {
		std::string storage;
		return drain_boolvec(surfit::cntr_read(path.c_str(), opt_cstr(name, storage),
		                                       col1, col2, col3, delimiter.c_str(),
		                                       skip_lines, grow_by));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("col1") = 1, py::arg("col2") = 2, py::arg("col3") = 3,
	   py::arg("delimiter") = " \t", py::arg("skip_lines") = 0,
	   py::arg("grow_by") = 250);

	m.def("cntr_load", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(surfit::cntr_load(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("path"), py::arg("name") = py::none());

	m.def("surf_load", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(surfit::surf_load(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("path"), py::arg("name") = py::none());

	m.def("mask_load", [](const std::string & path, py::object name) {
		std::string storage;
		return drain_boolvec(surfit::mask_load(path.c_str(), opt_cstr(name, storage)));
	}, py::arg("path"), py::arg("name") = py::none());

	// ---- gridding rules ----------------------------------------------------
	// Pattern arguments keep the C++ default "*", which selects every object;
	// this mirrors the Tcl front end.

	m.def("points", [](const std::string & name) {
		return drain_boolvec(surfit::points(name.c_str()));
	}, py::arg("name") = "*");
	m.def("points_add", [](double weight, const std::string & name) {
		return drain_boolvec(surfit::points_add(weight, name.c_str()));
	}, py::arg("weight") = 1, py::arg("name") = "*");
	m.def("points_leq", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::points_leq(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("points_geq", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::points_geq(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);

	m.def("surface", [](const std::string & name) {
		return drain_boolvec(surfit::surface(name.c_str()));
	}, py::arg("name") = "*");
	m.def("surface_add", [](double weight, const std::string & name) {
		return drain_boolvec(surfit::surface_add(weight, name.c_str()));
	}, py::arg("weight"), py::arg("name") = "*");
	m.def("surface_leq", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::surface_leq(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("surface_geq", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::surface_geq(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);

	m.def("trend", [](double d1, double d2, const std::string & name) {
		return drain_boolvec(surfit::trend(d1, d2, name.c_str()));
	}, py::arg("D1") = 1, py::arg("D2") = 2, py::arg("name") = "*");
	m.def("trend_add", [](double weight, double d1, double d2, const std::string & name) {
		return drain_boolvec(surfit::trend_add(weight, d1, d2, name.c_str()));
	}, py::arg("weight"), py::arg("D1") = 1, py::arg("D2") = 0,
	   py::arg("name") = "*");

	m.def("fault", [](const std::string & name) {
		return drain_boolvec(surfit::fault(name.c_str()));
	}, py::arg("name") = "*");

	m.def("curve", [](double value, const std::string & name) {
		return drain_boolvec(surfit::curve(value, name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");
	m.def("curve_add", [](double value, double weight, const std::string & name) {
		return drain_boolvec(surfit::curve_add(value, weight, name.c_str()));
	}, py::arg("value"), py::arg("weight") = 1, py::arg("name") = "*");
	m.def("curve_leq", [](double value, const std::string & name, double penalty) {
		return drain_boolvec(surfit::curve_leq(value, name.c_str(), penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("curve_geq", [](double value, const std::string & name, double penalty) {
		return drain_boolvec(surfit::curve_geq(value, name.c_str(), penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("penalty_factor") = 0);

	m.def("contour", [](const std::string & name) {
		return drain_boolvec(surfit::contour(name.c_str()));
	}, py::arg("name") = "*");
	m.def("contour_add", [](double weight, const std::string & name) {
		return drain_boolvec(surfit::contour_add(weight, name.c_str()));
	}, py::arg("weight") = 50, py::arg("name") = "*");
	m.def("contour_leq", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::contour_leq(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("contour_geq", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::contour_geq(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);

	m.def("mask", [](const py::object & value, const std::string & name) {
		std::string text = std::string(py::str(value));
		return drain_boolvec(surfit::mask(text.c_str(), name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");
	m.def("mask_add", [](double value, double weight, const std::string & name) {
		return drain_boolvec(surfit::mask_add(value, weight, name.c_str()));
	}, py::arg("value"), py::arg("weight") = 1, py::arg("name") = "*");
	m.def("mask_leq", [](double value, const std::string & name, double penalty) {
		return drain_boolvec(surfit::mask_leq(value, name.c_str(), penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("mask_geq", [](double value, const std::string & name, double penalty) {
		return drain_boolvec(surfit::mask_geq(value, name.c_str(), penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("penalty_factor") = 0);

	// ---- global rules ------------------------------------------------------

	m.def("value", [](const py::object & val) {
		std::string text = std::string(py::str(val));
		return surfit::value(text.c_str());
	}, py::arg("value") = "undef");
	m.def("value_add", [](double weight, double val) {
		return surfit::value_add(weight, val);
	}, py::arg("weight") = 1, py::arg("value") = 0);
	m.def("mean", [](double value, double penalty) {
		return surfit::mean(value, penalty);
	}, py::arg("value"), py::arg("penalty_factor") = -2);
	m.def("wmean", [](double value, const std::string & name, double penalty) {
		return drain_boolvec(surfit::wmean(value, name.c_str(), penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("penalty_factor") = -2);
	m.def("leq", [](double value, double penalty) {
		return surfit::leq(value, penalty);
	}, py::arg("value"), py::arg("penalty_factor") = 0);
	m.def("geq", [](double value, double penalty) {
		return surfit::geq(value, penalty);
	}, py::arg("value"), py::arg("penalty_factor") = 0);

	// ---- area + surface combinations ---------------------------------------

	m.def("area_surf_add", [](const std::string & surf, double weight,
	                          const std::string & area, int inside) {
		return drain_boolvec(surfit::area_surf_add(surf.c_str(), weight,
		                                           area.c_str(), inside));
	}, py::arg("surf") = "*", py::arg("weight") = 1,
	   py::arg("area") = "*", py::arg("inside") = 1);
	m.def("area_surf_leq", [](const std::string & surf, const std::string & area,
	                          double penalty, int inside) {
		return drain_boolvec(surfit::area_surf_leq(surf.c_str(), area.c_str(),
		                                           penalty, inside));
	}, py::arg("surf") = "*", py::arg("area") = "*",
	   py::arg("penalty_factor") = 0, py::arg("inside") = 1);
	m.def("area_surf_geq", [](const std::string & surf, const std::string & area,
	                          double penalty, int inside) {
		return drain_boolvec(surfit::area_surf_geq(surf.c_str(), area.c_str(),
		                                           penalty, inside));
	}, py::arg("surf") = "*", py::arg("area") = "*",
	   py::arg("penalty_factor") = 0, py::arg("inside") = 1);

	m.def("area_leq", [](double value, const std::string & area, double penalty,
	                     int inside) {
		return drain_boolvec(surfit::area_leq(value, area.c_str(), penalty, inside));
	}, py::arg("value"), py::arg("area") = "*", py::arg("penalty_factor") = 0,
	   py::arg("inside") = 1);
	m.def("area_geq", [](double value, const std::string & area, double penalty,
	                     int inside) {
		return drain_boolvec(surfit::area_geq(value, area.c_str(), penalty, inside));
	}, py::arg("value"), py::arg("area") = "*", py::arg("penalty_factor") = 0,
	   py::arg("inside") = 1);
	m.def("area_mean", [](double value, const std::string & area, double penalty,
	                      int inside) {
		return drain_boolvec(surfit::area_mean(value, area.c_str(), penalty, inside));
	}, py::arg("value"), py::arg("area") = "*", py::arg("penalty_factor") = -2,
	   py::arg("inside") = 1);
	m.def("area_wmean", [](double value, const std::string & area,
	                       const std::string & surf, double penalty, int inside) {
		return drain_boolvec(surfit::area_wmean(value, area.c_str(), surf.c_str(),
		                                        penalty, inside));
	}, py::arg("value"), py::arg("area") = "*", py::arg("surf") = "*",
	   py::arg("penalty_factor") = -2, py::arg("inside") = 1);
	m.def("area_completer", [](const std::string & area, double d1, double d2,
	                           double alpha, double w, int inside) {
		return drain_boolvec(surfit::area_completer(area.c_str(), d1, d2, alpha,
		                                            w, inside));
	}, py::arg("area") = "*", py::arg("D1") = 1, py::arg("D2") = 2,
	   py::arg("alpha") = 0, py::arg("w") = 1, py::arg("inside") = 1);
	m.def("area_surf", [](const std::string & surf, const std::string & area,
	                      int inside) {
		return drain_boolvec(surfit::area_surf(surf.c_str(), area.c_str(), inside));
	}, py::arg("surf") = "*", py::arg("area") = "*", py::arg("inside") = 1);

	m.def("curve_surf", [](const std::string & surf, const std::string & curv) {
		return drain_boolvec(surfit::curve_surf(surf.c_str(), curv.c_str()));
	}, py::arg("surf") = "*", py::arg("curv") = "*");
	m.def("curve_surf_add", [](const std::string & surf, double weight,
	                           const std::string & curv) {
		return drain_boolvec(surfit::curve_surf_add(surf.c_str(), weight,
		                                            curv.c_str()));
	}, py::arg("surf") = "*", py::arg("weight") = 1, py::arg("curv") = "*");
	m.def("curve_surf_leq", [](const std::string & surf, const std::string & curv,
	                           double penalty) {
		return drain_boolvec(surfit::curve_surf_leq(surf.c_str(), curv.c_str(),
		                                            penalty));
	}, py::arg("surf") = "*", py::arg("curv") = "*", py::arg("penalty_factor") = 0);
	m.def("curve_surf_geq", [](const std::string & surf, const std::string & curv,
	                           double penalty) {
		return drain_boolvec(surfit::curve_surf_geq(surf.c_str(), curv.c_str(),
		                                            penalty));
	}, py::arg("surf") = "*", py::arg("curv") = "*", py::arg("penalty_factor") = 0);

	m.def("mask_mean", [](double value, const std::string & name, double penalty) {
		return drain_boolvec(surfit::mask_mean(value, name.c_str(), penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("penalty_factor") = -2);
	m.def("mask_wmean", [](double value, const std::string & name,
	                       const std::string & surf, double penalty) {
		return drain_boolvec(surfit::mask_wmean(value, name.c_str(), surf.c_str(),
		                                        penalty));
	}, py::arg("value"), py::arg("name") = "*", py::arg("surf") = "*",
	   py::arg("penalty_factor") = -2);
	m.def("mask_completer", [](const std::string & name, double d1, double d2,
	                           double alpha, double w) {
		return drain_boolvec(surfit::mask_completer(name.c_str(), d1, d2, alpha, w));
	}, py::arg("name") = "*", py::arg("D1") = 1, py::arg("D2") = 2,
	   py::arg("alpha") = 0, py::arg("w") = 1);
	m.def("mask_surf", [](const std::string & surf, const std::string & name) {
		return drain_boolvec(surfit::mask_surf(surf.c_str(), name.c_str()));
	}, py::arg("surf") = "*", py::arg("name") = "*");
	m.def("mask_surf_add", [](const std::string & surf, double weight,
	                          const std::string & name) {
		return drain_boolvec(surfit::mask_surf_add(surf.c_str(), weight, name.c_str()));
	}, py::arg("surf") = "*", py::arg("weight") = 1, py::arg("name") = "*");
	m.def("mask_surf_leq", [](const std::string & surf, const std::string & name,
	                          double penalty) {
		return drain_boolvec(surfit::mask_surf_leq(surf.c_str(), name.c_str(), penalty));
	}, py::arg("surf") = "*", py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("mask_surf_geq", [](const std::string & surf, const std::string & name,
	                          double penalty) {
		return drain_boolvec(surfit::mask_surf_geq(surf.c_str(), name.c_str(), penalty));
	}, py::arg("surf") = "*", py::arg("name") = "*", py::arg("penalty_factor") = 0);

	m.def("surf_set", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::surf_set(first.c_str(), second.c_str()));
	}, py::arg("surface1_name"), py::arg("surface2_name"));
	m.def("surf_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::surf_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("name") = "*");
	m.def("surf_plus_value", [](double value, const std::string & name) {
		return drain_boolvec(surfit::surf_plus_value(value, name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");

	// ---- histograms --------------------------------------------------------

	m.def("hist", [](const std::string & name, double penalty, size_t treshold) {
		return drain_boolvec(surfit::hist(name.c_str(), penalty, treshold));
	}, py::arg("name") = "*", py::arg("penalty_factor") = -1,
	   py::arg("treshold") = 5);
	m.def("hist_from_surf", [](const std::string & name, size_t intervs,
	                           double from, double to, py::object histname) {
		std::string storage;
		return drain_boolvec(surfit::hist_from_surf(name.c_str(), intervs, from, to,
		                                            opt_cstr(histname, storage)));
	}, py::arg("name") = "*", py::arg("intervs") = 64,
	   py::arg("from") = FLT_MAX, py::arg("to") = FLT_MAX,
	   py::arg("histname") = py::none());
	m.def("hist_from_pnts", [](const std::string & name, size_t intervs,
	                           double from, double to, py::object histname) {
		std::string storage;
		return drain_boolvec(surfit::hist_from_pnts(name.c_str(), intervs, from, to,
		                                            opt_cstr(histname, storage)));
	}, py::arg("name") = "*", py::arg("intervs") = 64,
	   py::arg("from") = FLT_MAX, py::arg("to") = FLT_MAX,
	   py::arg("histname") = py::none());
	m.def("hist_read", [](const std::string & path, double minz, double maxz,
	                      py::object histname, int col1,
	                      const std::string & delimiter, int skip_lines,
	                      int grow_by) {
		std::string storage;
		return drain_boolvec(surfit::hist_read(path.c_str(), minz, maxz,
		                                       opt_cstr(histname, storage),
		                                       col1, delimiter.c_str(),
		                                       skip_lines, grow_by));
	}, py::arg("path"), py::arg("minz"), py::arg("maxz"),
	   py::arg("histname") = py::none(), py::arg("col1") = 1,
	   py::arg("delimiter") = " \t", py::arg("skip_lines") = 0,
	   py::arg("grow_by") = 250);
	m.def("hist_write", [](const std::string & path, const std::string & name,
	                       bool three_columns) {
		return drain_boolvec(surfit::hist_write(path.c_str(), name.c_str(),
		                                        three_columns));
	}, py::arg("path"), py::arg("name") = "*", py::arg("three_columns") = true);
	m.def("hist_del", [](const std::string & name) {
		surfit::hist_del(name.c_str());
	}, py::arg("name") = "*");

	// ---- dataset utilities -------------------------------------------------

	m.def("pnts_save", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surfit::pnts_save(path.c_str(), name.c_str()));
	}, py::arg("path"), py::arg("name") = "*");
	m.def("pnts_write", [](const std::string & path, const std::string & name,
	                       const std::string & delimiter) {
		return drain_boolvec(surfit::pnts_write(path.c_str(), name.c_str(),
		                                        delimiter.c_str()));
	}, py::arg("path"), py::arg("name") = "*", py::arg("delimiter") = "\t");
	m.def("pnts_set", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::pnts_set(first.c_str(), second.c_str()));
	}, py::arg("points1"), py::arg("points2"));
	m.def("pnts_mult_real", [](double value, const std::string & name) {
		return drain_boolvec(surfit::pnts_mult_real(value, name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");
	m.def("pnts_filter_in_area", [](const std::string & name,
	                                const std::string & area) {
		return drain_boolvec(surfit::pnts_filter_in_area(name.c_str(), area.c_str()));
	}, py::arg("name") = "*", py::arg("area") = "*");
	m.def("pnts_filter_out_area", [](const std::string & name,
	                                 const std::string & area) {
		return drain_boolvec(surfit::pnts_filter_out_area(name.c_str(), area.c_str()));
	}, py::arg("name") = "*", py::arg("area") = "*");
	m.def("pnts_info", []() { surfit::pnts_info(); });

	m.def("cntr_del", [](const std::string & name) {
		surfit::cntr_del(name.c_str());
	}, py::arg("name") = "*");
	m.def("cntr_mult_real", [](double value, const std::string & name) {
		return drain_boolvec(surfit::cntr_mult_real(value, name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");
	m.def("cntr_to_pnts", [](double step, const std::string & name) {
		return drain_boolvec(surfit::cntr_to_pnts(step, name.c_str()));
	}, py::arg("step") = 1, py::arg("name") = "*");
	m.def("cntrs_info", []() { surfit::cntrs_info(); });

	m.def("curv_to_cntr", [](double value, const std::string & name) {
		return drain_boolvec(surfit::curv_to_cntr(value, name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");
	m.def("curvs_info", []() { surfit::curvs_info(); });

	m.def("area_hist", [](const std::string & area, const std::string & hist,
	                      double penalty, int inside) {
		return drain_boolvec(surfit::area_hist(area.c_str(), hist.c_str(),
		                                       penalty, inside));
	}, py::arg("area") = "*", py::arg("hist") = "*",
	   py::arg("penalty_factor") = -1, py::arg("inside") = 1);
	m.def("areas_info", []() { surfit::areas_info(); });

	m.def("smooth_contour", [](const std::string & name, double penalty) {
		return drain_boolvec(surfit::smooth_contour(name.c_str(), penalty));
	}, py::arg("name") = "*", py::arg("penalty_factor") = 0);
	m.def("smooth_contour_add", [](double weight, const std::string & name) {
		return drain_boolvec(surfit::smooth_contour_add(weight, name.c_str()));
	}, py::arg("weight") = 50, py::arg("name") = "*");

	m.def("surf_del", [](const std::string & name) {
		surfit::surf_del(name.c_str());
	}, py::arg("name") = "*");
	m.def("surf_minus", [](const std::string & first, const std::string & second) {
		return drain_boolvec(surfit::surf_minus(first.c_str(), second.c_str()));
	}, py::arg("surface1_name"), py::arg("surface2_name"));
	m.def("surf_swapxy", [](const std::string & name) {
		return drain_boolvec(surfit::surf_swapxy(name.c_str()));
	}, py::arg("name") = "*");
	m.def("surf_filter_in_area", [](const std::string & name,
	                                const std::string & area) {
		return drain_boolvec(surfit::surf_filter_in_area(name.c_str(), area.c_str()));
	}, py::arg("name") = "*", py::arg("area") = "*");
	m.def("surf_info", [](const std::string & name) {
		surfit::surf_info(name.c_str());
	}, py::arg("name") = "*");
	m.def("surfs_info", []() { surfit::surfs_info(); });

	m.def("mask_info", [](const std::string & name) {
		surfit::mask_info(name.c_str());
	}, py::arg("name") = "*");
	m.def("hists_info", []() { surfit::hists_info(); });
	m.def("grid_info", []() { surfit::grid_info(); });
	m.def("grid_unload", []() { surfit::grid_unload(); });
	m.def("solvers_info", []() { surfit::solvers_info(); });
	m.def("mem_info", []() { surfit::mem_info(); });

	m.def("completer_add", [](double weight, double d1, double d2, double alpha,
	                          double w) {
		return surfit::completer_add(weight, d1, d2, alpha, w);
	}, py::arg("weight") = 1, py::arg("D1") = 1, py::arg("D2") = 2,
	   py::arg("alpha") = 0, py::arg("w") = 1);

	// Overloaded in C++ (the other one is the Triangle entry point), hence the
	// lambda rather than a plain function pointer.
	m.def("triangulate", []() { return surfit::triangulate(); });

	// ---- whole-task data files ---------------------------------------------

	m.def("file_load", [](const std::string & path) {
		surfit::file_load(path.c_str());
	}, py::arg("path"), py::call_guard<py::gil_scoped_release>());
	m.def("file_save", [](const std::string & path) {
		return surfit::file_save(path.c_str());
	}, py::arg("path"), py::call_guard<py::gil_scoped_release>());
	m.def("file_info", [](const std::string & path) {
		char * text = surfit::file_info(path.c_str());
		std::string result = text != NULL ? std::string(text) : std::string();
		free(text);
		return result;
	}, py::arg("path"));

	// ---- surfit_io: file formats -------------------------------------------
	// These are the commands of the libsurfit_io plugin.  Defaults follow the
	// SWIG interface file, which is what the Tcl front end uses: loaders take
	// an optional name (NULL derives it from the file), savers default to "*".

#define SURFIT_IO_LOAD(command)                                                \
	m.def(#command, [](const std::string & path, py::object name) {            \
		std::string storage;                                                   \
		return drain_boolvec(                                                  \
			surfit::command(path.c_str(), opt_cstr(name, storage)));           \
	}, py::arg("path"), py::arg("name") = py::none())

#define SURFIT_IO_SAVE(command)                                                \
	m.def(#command, [](const std::string & path, const std::string & name) {   \
		return drain_boolvec(surfit::command(path.c_str(), name.c_str()));     \
	}, py::arg("path"), py::arg("name") = "*")

	SURFIT_IO_LOAD(curv_load_bln);
	SURFIT_IO_LOAD(curv_load_shp);
	SURFIT_IO_LOAD(area_load_bln);
	SURFIT_IO_LOAD(area_load_shp);
	SURFIT_IO_LOAD(cntr_load_bln);
	SURFIT_IO_LOAD(surf_load_grd);
	SURFIT_IO_LOAD(surf_load_gmt);
	SURFIT_IO_LOAD(surf_load_grass);
	SURFIT_IO_LOAD(surf_load_arcgis);

	SURFIT_IO_SAVE(curv_save_bln);
	SURFIT_IO_SAVE(curv_save_shp);
	SURFIT_IO_SAVE(area_save_bln);
	SURFIT_IO_SAVE(area_save_shp);
	SURFIT_IO_SAVE(cntr_save_bln);
	SURFIT_IO_SAVE(cntr_save_shp);
	SURFIT_IO_SAVE(surf_save_gmt);
	SURFIT_IO_SAVE(surf_save_grass);
	SURFIT_IO_SAVE(surf_save_arcgis);
	SURFIT_IO_SAVE(surf_save_xyz);
	SURFIT_IO_SAVE(surf_save_bmp);
	SURFIT_IO_SAVE(mask_save_grd);
	SURFIT_IO_SAVE(mask_save_xyz);

#undef SURFIT_IO_LOAD
#undef SURFIT_IO_SAVE

	m.def("pnts_load_shp", [](const std::string & path, py::object name,
	                          const std::string & param) {
		std::string storage;
		return drain_boolvec(surfit::pnts_load_shp(path.c_str(),
		                                           opt_cstr(name, storage),
		                                           param.c_str()));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("param") = "VALUE");
	m.def("pnts_save_shp", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surfit::pnts_save_shp(path.c_str(), name.c_str()));
	}, py::arg("path"), py::arg("name") = "*");

	m.def("cntr_load_shp", [](const std::string & path, py::object name,
	                          py::object zfield) {
		std::string name_storage;
		std::string zfield_storage;
		return drain_boolvec(surfit::cntr_load_shp(path.c_str(),
		                                           opt_cstr(name, name_storage),
		                                           opt_cstr(zfield, zfield_storage)));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("zfield") = py::none());

	m.def("surf_load_xyz", [](const std::string & path, py::object name,
	                          bool force) {
		std::string storage;
		return drain_boolvec(surfit::surf_load_xyz(path.c_str(),
		                                           opt_cstr(name, storage),
		                                           force));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("force") = false);
	m.def("surf_save_grd", [](const std::string & path, const std::string & name,
	                          int format) {
		return drain_boolvec(surfit::surf_save_grd(path.c_str(), name.c_str(),
		                                           format));
	}, py::arg("path"), py::arg("name") = "*", py::arg("format") = 0);
	m.def("surf_save_jpg", [](const std::string & path, const std::string & name,
	                          int quality) {
		return drain_boolvec(surfit::surf_save_jpg(path.c_str(), name.c_str(),
		                                           quality));
	}, py::arg("path"), py::arg("name") = "*", py::arg("quality") = 255);

	// Both image loaders share the same extra arguments: a z-range plus an
	// explicit grid to interpret the pixels on.
	m.def("surf_load_jpg", [](const std::string & path, py::object name,
	                          double minz, double maxz, double start_x,
	                          double start_y, double step_x, double step_y) {
		std::string storage;
		return drain_boolvec(surfit::surf_load_jpg(path.c_str(),
		                                           opt_cstr(name, storage),
		                                           minz, maxz, start_x, start_y,
		                                           step_x, step_y));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("minz") = 0, py::arg("maxz") = 0, py::arg("start_x") = 0,
	   py::arg("start_y") = 0, py::arg("step_x") = 1, py::arg("step_y") = 1);
	m.def("surf_load_bmp", [](const std::string & path, py::object name,
	                          double minz, double maxz, double start_x,
	                          double start_y, double step_x, double step_y) {
		std::string storage;
		return drain_boolvec(surfit::surf_load_bmp(path.c_str(),
		                                           opt_cstr(name, storage),
		                                           minz, maxz, start_x, start_y,
		                                           step_x, step_y));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("minz") = 0, py::arg("maxz") = 0, py::arg("start_x") = 0,
	   py::arg("start_y") = 0, py::arg("step_x") = 1, py::arg("step_y") = 1);
}
