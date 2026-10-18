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

#include <cstdint>

#include <cfloat>
#include <cstdlib>
#include <cstring>
#include <string>

// The export/visibility macros live in these two headers and must come first,
// exactly as in every core translation unit.
#include "sstuff_ie.h"
#include "surfit_ie.h"

#include "bind_common.h"

#include "real.h"
#include "vec.h"
#include "boolvec.h"
#include "intvec.h"
#include "strvec.h"
#include "fileio.h"
#include "interp.h"
#include "surfit_state.h"
#include "free_elements.h"
#include "grid_user.h"
#include "data_manager.h"
#include "license.h"

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

// The DEM and freeflow commands live in translation units of their own; each
// one binds its commands and registers its data manager on this module.
void bind_globe(pybind11::module_ & m);
void bind_freeflow(pybind11::module_ & m);

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
using surfit::intvec;
using surfit::strvec;
// NB: `surfit` itself is not imported by a using-declaration -- the function
// surfit::surfit() would clash with the namespace name in the global scope.

namespace {

// The result-draining helpers live in bind_common.h, because the globe and
// freeflow bindings are a translation unit of their own and use the same ones.
using surfit_py::cstr_or_empty;
using surfit_py::drain_boolvec;
using surfit_py::drain_intvec;
using surfit_py::drain_strvec;
using surfit_py::drain_vec;
using surfit_py::opt_cstr;

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

	// The DEM and freeflow modules, which the Tcl front end loads as the
	// plugins libglobe.so and libfreeflow.so.  Their init functions announce
	// themselves in the log the way the plugins do; a Python import stays
	// quiet, so the announcement is filtered, exactly like the licence
	// banner surfit_init_variables() would print.
	surfit::loglevel = LOG_SILENT;
	bind_globe(m);
	bind_freeflow(m);

	// The Tcl front end runs surfit_init_variables() when the module loads,
	// which calls log_open() and so raises the level to LOG_WARNING.  Python
	// does not run it, and the core's own default (LOG_MESSAGE) would hide
	// warnings and errors - and, because writelog() returns early when a
	// message is filtered, it would also suppress the exception that
	// stop_on_error raises for an error.  Start where the Tcl side starts.
	surfit::loglevel = LOG_WARNING;

	// The default level is the one the SWIG interface declares for Tcl
	// (src/tclsurfit/src/fileio.i: `int level = 3`).
	// NB: the log levels are macros, so LOG_WARNING cannot be namespace-qualified.
	m.def("log_open", [](int level, const std::string & path) {
		return surfit::log_open(level, path.empty() ? NULL : path.c_str());
	}, py::arg("level") = LOG_WARNING, py::arg("path") = std::string());

	m.def("clear_data", &clear_data, "drop all loaded data and gridding rules");

	// Object selection by name is the one thing the engine used to borrow from
	// Tcl; the matcher is local now, and this exposes it so it can be checked
	// against Tcl itself.
	m.def("string_match", [](const std::string & pattern, const std::string & string) {
		return ::StringMatch(pattern.c_str(), string.c_str());
	}, py::arg("pattern"), py::arg("string"),
	   "Tcl-style name matching: *, ?, [sets], backslash escapes");

	// One task's state, kept as an opaque handle: the Python side owns the
	// lifetime and never touches the structure.
	m.def("state_create", []() {
		return reinterpret_cast<std::uintptr_t>(surfit::state_create());
	}, "a new empty task state, as a handle");
	m.def("state_install", [](std::uintptr_t handle) {
		surfit::state_install(
			reinterpret_cast<surfit::surfit_state *>(handle));
	}, py::arg("handle"), "makes that state the active one");
	m.def("state_release", [](std::uintptr_t handle) {
		surfit::state_release(
			reinterpret_cast<surfit::surfit_state *>(handle));
	}, py::arg("handle"), "frees a state and everything it holds");

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

	// The rest of the settings the Tcl front end exposes as traced variables.
	// Python takes them as accessor pairs: a module-level variable would be
	// silently out of step with the engine's own copy.
	m.def("set_sor_omega", [](double value) { surfit::sor_omega = REAL(value); },
	      "over-relaxation factor for the SOR solver");
	m.def("get_sor_omega", []() { return double(surfit::sor_omega); });
	m.def("set_ssor_omega", [](double value) { surfit::ssor_omega = REAL(value); },
	      "over-relaxation factor for the symmetric SOR solver");
	m.def("get_ssor_omega", []() { return double(surfit::ssor_omega); });
	m.def("set_undef_value", [](double value) { surfit::undef_value = REAL(value); },
	      "what an undefined node holds");
	m.def("get_undef_value", []() { return double(surfit::undef_value); });
	m.def("set_stop_execution", [](bool value) { surfit::stop_execution = value; },
	      "stop the running solve at the next check");
	m.def("get_stop_execution", []() { return surfit::stop_execution; });
	m.def("set_reproject_faults", [](int value) { surfit::reproject_faults = value; });
	m.def("get_reproject_faults", []() { return surfit::reproject_faults; });
	m.def("set_reproject_undef_areas", [](int value) { surfit::reproject_undef_areas = value; });
	m.def("get_reproject_undef_areas", []() { return surfit::reproject_undef_areas; });
	m.def("set_process_isolated_areas", [](int value) { surfit::process_isolated_areas = value; });
	m.def("get_process_isolated_areas", []() { return surfit::process_isolated_areas; });
	m.def("set_penalty_max_iter", [](size_t value) { surfit::penalty_max_iter = value; });
	m.def("get_penalty_max_iter", []() { return surfit::penalty_max_iter; });
	m.def("set_penalty_weight", [](double value) { surfit::penalty_weight = REAL(value); });
	m.def("get_penalty_weight", []() { return double(surfit::penalty_weight); });
	m.def("set_penalty_weight_mult", [](double value) { surfit::penalty_weight_mult = REAL(value); });
	m.def("get_penalty_weight_mult", []() { return double(surfit::penalty_weight_mult); });
	m.def("set_basis_cnt", [](size_t value) { surfit::basis_cnt = value; },
	      "size of the solver's own grid in the first phase");
	m.def("get_basis_cnt", []() { return surfit::basis_cnt; });

	// Library utilities that the Tcl front end also offers.
	m.def("clear_rules", &surfit::clear_rules, "drop the gridding rules only");
	m.def("types_info", []() {
		char * info = surfit::types_info();
		std::string text = info ? std::string(info) : std::string();
		if (info)
			surfit::surfit_free_char(info);
		return text;
	}, "the object types file_load can read");
	m.def("putlog", [](const std::string & text) { surfit::putlog(text.c_str()); },
	      py::arg("text"), "writes a line to the log file");
	m.def("log_clear", &surfit::log_clear, "truncate the log file");

	// How file_save treats an existing file: "new" truncates it, "append" adds
	// to it.  The Tcl front end exposes the same three commands.
	m.def("datafile_mode", []() {
		return cstr_or_empty(surfit::datafile_mode());
	}, "the mode file_save writes in: datafile_new or datafile_append");
	m.def("datafile_new", []() {
		return cstr_or_empty(surfit::datafile_new());
	}, "make file_save truncate an existing file");
	m.def("datafile_append", []() {
		return cstr_or_empty(surfit::datafile_append());
	}, "make file_save append to an existing file");
	m.def("show_c", &surfit::show_c, "print the copying conditions");
	m.def("show_w", &surfit::show_w, "print the warranty notice");
	m.def("init_threads", &surfit::init_threads, py::arg("count"),
	      "size of the thread pool");
	m.def("get_threads", &surfit::get_threads, "size of the thread pool");
	// `get_solver_short_name(pos)` and `get_solver_long_name(pos)` list the
	// available solvers; these report the one a solve would use.
	m.def("get_current_solver_short_name", []() {
		const char * name = surfit::get_current_solver_short_name();
		return name ? std::string(name) : std::string();
	}, "short name of the solver a solve would use");
	m.def("get_current_solver_long_name", []() {
		const char * name = surfit::get_current_solver_long_name();
		return name ? std::string(name) : std::string();
	}, "description of the solver a solve would use");

	// --- object collections -------------------------------------------
	// Counts and deletion per type.  `*` means every object of that type,
	// which is what the Tcl front end does with an omitted name.
	m.def("area_size", &surfit::area_size, "number of areas in memory");
	m.def("cntr_size", &surfit::cntr_size, "number of contours in memory");
	m.def("curv_size", &surfit::curv_size, "number of curves in memory");
	m.def("hist_size", &surfit::hist_size, "number of histograms in memory");
	m.def("mask_size", &surfit::mask_size, "number of masks in memory");
	m.def("pnts_size", &surfit::pnts_size, "number of point sets in memory");
	m.def("surf_size", &surfit::surf_size, "number of surfaces in memory");

	m.def("area_del", [](const std::string & n) { surfit::area_del(n.c_str()); },
	      py::arg("name") = "*", "unload areas");
	m.def("cntr_del", [](const std::string & n) { surfit::cntr_del(n.c_str()); },
	      py::arg("name") = "*", "unload contours");
	m.def("curv_del", [](const std::string & n) { surfit::curv_del(n.c_str()); },
	      py::arg("name") = "*", "unload curves");
	m.def("hist_del", [](const std::string & n) { surfit::hist_del(n.c_str()); },
	      py::arg("name") = "*", "unload histograms");
	m.def("mask_del", [](const std::string & n) { surfit::mask_del(n.c_str()); },
	      py::arg("name") = "*", "unload masks");
	m.def("pnts_del", [](const std::string & n) { surfit::pnts_del(n.c_str()); },
	      py::arg("name") = "*", "unload point sets");
	m.def("surf_del", [](const std::string & n) { surfit::surf_del(n.c_str()); },
	      py::arg("name") = "*", "unload surfaces");

	m.def("area_save", [](const std::string & p, const std::string & n) {
		return drain_boolvec(surfit::area_save(p.c_str(), n.c_str()));
	}, py::arg("path"), py::arg("name") = "*", "write areas to a .dat file");
	m.def("cntr_save", [](const std::string & p, const std::string & n) {
		return drain_boolvec(surfit::cntr_save(p.c_str(), n.c_str()));
	}, py::arg("path"), py::arg("name") = "*", "write contours to a .dat file");
	m.def("curv_save", [](const std::string & p, const std::string & n) {
		return drain_boolvec(surfit::curv_save(p.c_str(), n.c_str()));
	}, py::arg("path"), py::arg("name") = "*", "write curves to a .dat file");
	m.def("mask_save", [](const std::string & p, const std::string & n) {
		return drain_boolvec(surfit::mask_save(p.c_str(), n.c_str()));
	}, py::arg("path"), py::arg("name") = "*", "write masks to a .dat file");
	m.def("pnts_save", [](const std::string & p, const std::string & n) {
		return drain_boolvec(surfit::pnts_save(p.c_str(), n.c_str()));
	}, py::arg("path"), py::arg("name") = "*", "write point sets to a .dat file");
	m.def("surf_save", [](const std::string & p, const std::string & n) {
		return drain_boolvec(surfit::surf_save(p.c_str(), n.c_str()));
	}, py::arg("path"), py::arg("name") = "*", "write surfaces to a .dat file");

	m.def("area_write", [](const std::string & p, const std::string & n,
	                       const std::string & d) {
		return drain_boolvec(surfit::area_write(p.c_str(), n.c_str(), d.c_str()));
	}, py::arg("path"), py::arg("name") = "*", py::arg("delimiter") = "\t",
	   "write areas as text");
	m.def("cntr_write", [](const std::string & p, const std::string & n,
	                       const std::string & d) {
		return drain_boolvec(surfit::cntr_write(p.c_str(), n.c_str(), d.c_str()));
	}, py::arg("path"), py::arg("name") = "*", py::arg("delimiter") = "\t",
	   "write contours as text");
	m.def("curv_write", [](const std::string & p, const std::string & n,
	                       const std::string & d) {
		return drain_boolvec(surfit::curv_write(p.c_str(), n.c_str(), d.c_str()));
	}, py::arg("path"), py::arg("name") = "*", py::arg("delimiter") = "\t",
	   "write curves as text");
	m.def("pnts_write", [](const std::string & p, const std::string & n,
	                       const std::string & d) {
		return drain_boolvec(surfit::pnts_write(p.c_str(), n.c_str(), d.c_str()));
	}, py::arg("path"), py::arg("name") = "*", py::arg("delimiter") = "\t",
	   "write point sets as text");
	m.def("hist_write", [](const std::string & p, const std::string & n,
	                       bool three_columns) {
		return drain_boolvec(surfit::hist_write(p.c_str(), n.c_str(), three_columns));
	}, py::arg("path"), py::arg("name") = "*", py::arg("three_columns") = true,
	   "write histograms as text");

	m.def("area_invert", [](const std::string & n) {
		return drain_boolvec(surfit::area_invert(n.c_str()));
	}, py::arg("name") = "*", "swap inside and outside of areas");

	// --- object accessors ---------------------------------------------
	// The Tcl front end has this family for every collection: the names that
	// match, one name by position, the object ids and renaming.  Without it a
	// front end can only reach an object it already knows the name of.
	m.def("area_getName", [](const std::string & name) {
		return drain_strvec(surfit::area_getName(name.c_str()));
	}, py::arg("area_name") = "*", "names of the matching areas");
	m.def("area_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::area_getNameAt(pos));
	}, py::arg("pos"), "name of the area at that position; empty if there is none");
	m.def("area_getId", [](const std::string & name) {
		return drain_intvec(surfit::area_getId(name.c_str()));
	}, py::arg("area_name") = "*", "ids of the matching areas");
	m.def("area_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::area_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("area_name") = "*");

	m.def("cntr_getName", [](const std::string & name) {
		return drain_strvec(surfit::cntr_getName(name.c_str()));
	}, py::arg("cntr_name") = "*", "names of the matching contours");
	m.def("cntr_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::cntr_getNameAt(pos));
	}, py::arg("pos"), "name of the contour at that position; empty if there is none");
	m.def("cntr_getId", [](const std::string & name) {
		return drain_intvec(surfit::cntr_getId(name.c_str()));
	}, py::arg("cntr_name") = "*", "ids of the matching contours");
	m.def("cntr_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::cntr_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("cntr_name") = "*");

	m.def("curv_getName", [](const std::string & name) {
		return drain_strvec(surfit::curv_getName(name.c_str()));
	}, py::arg("curv_name") = "*", "names of the matching curves");
	m.def("curv_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::curv_getNameAt(pos));
	}, py::arg("pos"), "name of the curve at that position; empty if there is none");
	m.def("curv_getId", [](const std::string & name) {
		return drain_intvec(surfit::curv_getId(name.c_str()));
	}, py::arg("curv_name") = "*", "ids of the matching curves");
	m.def("curv_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::curv_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("curv_name") = "*");

	m.def("grid_getCountX", &surfit::grid_getCountX,
	      "node count of the target grid in X, 0 when no grid is defined");
	m.def("grid_setCountX", &surfit::grid_setCountX, py::arg("countX"));
	m.def("grid_getCountY", &surfit::grid_getCountY,
	      "node count of the target grid in Y, 0 when no grid is defined");
	m.def("grid_setCountY", &surfit::grid_setCountY, py::arg("countY"));
	m.def("grid_getCoordNodeX", [](int i) {
		return double(surfit::grid_getCoordNodeX(i));
	}, py::arg("i"));
	m.def("grid_getCoordNodeY", [](int j) {
		return double(surfit::grid_getCoordNodeY(j));
	}, py::arg("j"));
	m.def("grid_getStepX", []() { return double(surfit::grid_getStepX()); });
	m.def("grid_getStepY", []() { return double(surfit::grid_getStepY()); });

	m.def("hist_getName", [](const std::string & name) {
		return drain_strvec(surfit::hist_getName(name.c_str()));
	}, py::arg("name") = "*", "names of the matching histograms");
	m.def("hist_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::hist_getNameAt(pos));
	}, py::arg("pos"), "name of the histogram at that position; empty if there is none");
	m.def("hist_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::hist_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("name") = "*");

	m.def("mask_getValue", [](double x, double y, const std::string & name) {
		return drain_boolvec(surfit::mask_getValue(REAL(x), REAL(y), name.c_str()));
	}, py::arg("x"), py::arg("y"), py::arg("mask_name") = "*");
	m.def("mask_getName", [](const std::string & name) {
		return drain_strvec(surfit::mask_getName(name.c_str()));
	}, py::arg("mask_name") = "*", "names of the matching masks");
	m.def("mask_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::mask_getNameAt(pos));
	}, py::arg("pos"), "name of the mask at that position; empty if there is none");
	m.def("mask_getId", [](const std::string & name) {
		return drain_intvec(surfit::mask_getId(name.c_str()));
	}, py::arg("mask_name") = "*", "ids of the matching masks");
	m.def("mask_setName", [](const std::string & new_name, const std::string & name) {
		surfit::mask_setName(new_name.c_str(), name.c_str());
	}, py::arg("new_name"), py::arg("mask_name") = "*");

	m.def("pnts_getCount", [](const std::string & name) {
		return drain_intvec(surfit::pnts_getCount(name.c_str()));
	}, py::arg("points_name") = "*", "point count of each matching set");
	m.def("pnts_getName", [](const std::string & name) {
		return drain_strvec(surfit::pnts_getName(name.c_str()));
	}, py::arg("points_name") = "*", "names of the matching point sets");
	m.def("pnts_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::pnts_getNameAt(pos));
	}, py::arg("pos"), "name of the point set at that position; empty if there is none");
	m.def("pnts_getId", [](const std::string & name) {
		return drain_intvec(surfit::pnts_getId(name.c_str()));
	}, py::arg("points_name") = "*", "ids of the matching point sets");
	m.def("pnts_setName", [](const std::string & new_name, const std::string & name) {
		return drain_boolvec(surfit::pnts_setName(new_name.c_str(), name.c_str()));
	}, py::arg("new_name"), py::arg("points_name") = "*");

	m.def("surf_getValue", [](double x, double y, const std::string & name) {
		return drain_vec(surfit::surf_getValue(REAL(x), REAL(y), name.c_str()));
	}, py::arg("x"), py::arg("y"), py::arg("surface_name") = "*");
	m.def("surf_getValueIJ", [](int i, int j, const std::string & name) {
		return drain_vec(surfit::surf_getValueIJ(i, j, name.c_str()));
	}, py::arg("i"), py::arg("j"), py::arg("surface_name") = "*");
	m.def("surf_D1", [](const std::string & name) {
		return drain_vec(surfit::surf_D1(name.c_str()));
	}, py::arg("surface_name") = "*", "approximation term of the surface");
	m.def("surf_D2", [](const std::string & name) {
		return drain_vec(surfit::surf_D2(name.c_str()));
	}, py::arg("surface_name") = "*", "roughness term of the surface");
	m.def("surf_getCountX", [](const std::string & name) {
		return drain_intvec(surfit::surf_getCountX(name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_getCountY", [](const std::string & name) {
		return drain_intvec(surfit::surf_getCountY(name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_getStepX", [](const std::string & name) {
		return drain_vec(surfit::surf_getStepX(name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_getStepY", [](const std::string & name) {
		return drain_vec(surfit::surf_getStepY(name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_getName", [](const std::string & name) {
		return drain_strvec(surfit::surf_getName(name.c_str()));
	}, py::arg("surface_name") = "*", "names of the matching surfaces");
	m.def("surf_getNameAt", [](int pos) {
		return cstr_or_empty(surfit::surf_getNameAt(pos));
	}, py::arg("pos"), "name of the surface at that position; empty if there is none");
	m.def("surf_getId", [](const std::string & name) {
		return drain_intvec(surfit::surf_getId(name.c_str()));
	}, py::arg("surface_name") = "*", "ids of the matching surfaces");

	m.def("area_completer_add",
	      [](double weight, const std::string & name, double d1, double d2,
	         double alpha, double w, int inside) {
		return drain_boolvec(surfit::area_completer_add(REAL(weight), name.c_str(),
		                                        REAL(d1), REAL(d2), REAL(alpha),
		                                        REAL(w), inside));
	}, py::arg("weight") = 1, py::arg("name") = "*", py::arg("d1") = 1,
	   py::arg("d2") = 2, py::arg("alpha") = 0, py::arg("w") = 1,
	   py::arg("inside") = 1, "rule: complete inside or outside an area");
	m.def("mask_completer_add",
	      [](double weight, const std::string & name, double d1, double d2,
	         double alpha, double w) {
		return drain_boolvec(surfit::mask_completer_add(REAL(weight), name.c_str(),
		                                        REAL(d1), REAL(d2), REAL(alpha),
		                                        REAL(w)));
	}, py::arg("weight") = 1, py::arg("name") = "*", py::arg("d1") = 1,
	   py::arg("d2") = 2, py::arg("alpha") = 0, py::arg("w") = 1,
	   "rule: complete inside a mask");

	// --- arithmetic and statistics over surfaces ----------------------
	// The commands that combine a surface with another one, with a value, or
	// with an area, plus the statistics that report one number per object.
	m.def("surf_add_noise", [](double std, const std::string & surface_name) {
		surfit::surf_add_noise(REAL(std), surface_name.c_str());
	}, py::arg("std"), py::arg("surface_name") = "*");
	m.def("surf_adj_hist", [](const std::string & surface_name, const py::object & histogram_name) {
		std::string histogram_name_storage;
		return drain_boolvec(surfit::surf_adj_hist(surface_name.c_str(), opt_cstr(histogram_name, histogram_name_storage)));
	}, py::arg("surface_name") = "*", py::arg("histogram_name") = py::none());
	m.def("surf_area_maxz", [](const std::string & area_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_area_maxz(area_name.c_str(), surface_name.c_str()));
	}, py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_area_mean", [](const std::string & area_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_area_mean(area_name.c_str(), surface_name.c_str()));
	}, py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_area_minz", [](const std::string & area_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_area_minz(area_name.c_str(), surface_name.c_str()));
	}, py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_area_wmean", [](const std::string & area_name, const std::string & wsurface_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_area_wmean(area_name.c_str(), wsurface_name.c_str(), surface_name.c_str()));
	}, py::arg("area_name") = "*", py::arg("wsurface_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_auto_decomp", [](double eps, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_auto_decomp(REAL(eps), surface_name.c_str()));
	}, py::arg("eps"), py::arg("surface_name") = "*");
	m.def("surf_cells_in_area", [](const std::string & area_name, const std::string & surface_name) {
		return drain_intvec(surfit::surf_cells_in_area(area_name.c_str(), surface_name.c_str()));
	}, py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_decomp", [](const std::string & surface_name) {
		return drain_boolvec(surfit::surf_decomp(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_div", [](const std::string & surface1_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_div(surface1_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("surface2_name"));
	m.def("surf_div_area", [](const std::string & surface1_name, const std::string & area_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_div_area(surface1_name.c_str(), area_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("area_name"), py::arg("surface2_name"));
	m.def("surf_div_value", [](double val, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_div_value(REAL(val), surface_name.c_str()));
	}, py::arg("val"), py::arg("surface_name") = "*");
	m.def("surf_div_value_area", [](double val, const std::string & area_name, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_div_value_area(REAL(val), area_name.c_str(), surface_name.c_str()));
	}, py::arg("val"), py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_filter_by_mask", [](const std::string & surface_name, const std::string & mask_name) {
		return drain_boolvec(surfit::surf_filter_by_mask(surface_name.c_str(), mask_name.c_str()));
	}, py::arg("surface_name") = "*", py::arg("mask_name") = "*");
	m.def("surf_filter_by_surf", [](double eps, const std::string & surface1_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_filter_by_surf(REAL(eps), surface1_name.c_str(), surface2_name.c_str()));
	}, py::arg("eps"), py::arg("surface1_name") = "*", py::arg("surface2_name") = "*");
	m.def("surf_filter_out_area", [](const std::string & surface_name, const std::string & area_name) {
		return drain_boolvec(surfit::surf_filter_out_area(surface_name.c_str(), area_name.c_str()));
	}, py::arg("surface_name") = "*", py::arg("area_name") = "*");
	m.def("surf_full_recons", [](const std::string & surface_name) {
		return drain_boolvec(surfit::surf_full_recons(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_get_details_level", [](const std::string & surface_name) {
		return drain_intvec(surfit::surf_get_details_level(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_gradient", [](const std::string & surface_name, const py::object & newname) {
		std::string newname_storage;
		return drain_boolvec(surfit::surf_gradient(surface_name.c_str(), opt_cstr(newname, newname_storage)));
	}, py::arg("surface_name") = "*", py::arg("newname") = py::none());
	m.def("surf_mask_mean", [](const std::string & mask_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_mask_mean(mask_name.c_str(), surface_name.c_str()));
	}, py::arg("mask_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_mask_wmean", [](const std::string & mask_name, const std::string & wsurface_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_mask_wmean(mask_name.c_str(), wsurface_name.c_str(), surface_name.c_str()));
	}, py::arg("mask_name") = "*", py::arg("wsurface_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_maxz", [](const std::string & surface_name) {
		return drain_vec(surfit::surf_maxz(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_mean", [](const std::string & surface_name) {
		return drain_vec(surfit::surf_mean(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_minus_area", [](const std::string & surface1_name, const std::string & area_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_minus_area(surface1_name.c_str(), area_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("area_name"), py::arg("surface2_name"));
	m.def("surf_minus_value", [](double val, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_minus_value(REAL(val), surface_name.c_str()));
	}, py::arg("val"), py::arg("surface_name") = "*");
	m.def("surf_minus_value_area", [](double val, const std::string & area_name, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_minus_value_area(REAL(val), area_name.c_str(), surface_name.c_str()));
	}, py::arg("val"), py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_minz", [](const std::string & surface_name) {
		return drain_vec(surfit::surf_minz(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_mult", [](const std::string & surface1_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_mult(surface1_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("surface2_name"));
	m.def("surf_mult_area", [](const std::string & surface1_name, const std::string & area_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_mult_area(surface1_name.c_str(), area_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("area_name"), py::arg("surface2_name"));
	m.def("surf_mult_value", [](double val, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_mult_value(REAL(val), surface_name.c_str()));
	}, py::arg("val"), py::arg("surface_name") = "*");
	m.def("surf_mult_value_area", [](double val, const std::string & area_name, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_mult_value_area(REAL(val), area_name.c_str(), surface_name.c_str()));
	}, py::arg("val"), py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_plus", [](const std::string & surface1_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_plus(surface1_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("surface2_name"));
	m.def("surf_plus_area", [](const std::string & surface1_name, const std::string & area_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_plus_area(surface1_name.c_str(), area_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("area_name"), py::arg("surface2_name"));
	m.def("surf_plus_value_area", [](double val, const std::string & surface_name, const std::string & area_name) {
		return drain_boolvec(surfit::surf_plus_value_area(REAL(val), surface_name.c_str(), area_name.c_str()));
	}, py::arg("val"), py::arg("surface_name") = "*", py::arg("area_name") = "*");
	m.def("surf_project", [](const std::string & surface_name, const py::object & newname) {
		std::string newname_storage;
		return drain_boolvec(surfit::surf_project(surface_name.c_str(), opt_cstr(newname, newname_storage)));
	}, py::arg("surface_name") = "*", py::arg("newname") = py::none());
	m.def("surf_recons", [](const std::string & surface_name) {
		return drain_boolvec(surfit::surf_recons(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_resid", [](const std::string & filename, const std::string & surface_name, const std::string & points_name) {
		return drain_boolvec(surfit::surf_resid(filename.c_str(), surface_name.c_str(), points_name.c_str()));
	}, py::arg("filename"), py::arg("surface_name") = "*", py::arg("points_name") = "*");
	m.def("surf_set_area", [](const std::string & surface1_name, const std::string & area_name, const std::string & surface2_name) {
		return drain_boolvec(surfit::surf_set_area(surface1_name.c_str(), area_name.c_str(), surface2_name.c_str()));
	}, py::arg("surface1_name"), py::arg("area_name"), py::arg("surface2_name"));
	m.def("surf_set_value", [](double val, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_set_value(REAL(val), surface_name.c_str()));
	}, py::arg("val"), py::arg("surface_name") = "*");
	m.def("surf_set_value_area", [](const std::string & val, const std::string & area_name, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_set_value_area(val.c_str(), area_name.c_str(), surface_name.c_str()));
	}, py::arg("val"), py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_std", [](double mean, const std::string & surface_name) {
		return drain_vec(surfit::surf_std(REAL(mean), surface_name.c_str()));
	}, py::arg("mean"), py::arg("surface_name") = "*");
	m.def("surf_sum", [](const std::string & surface_name) {
		return drain_vec(surfit::surf_sum(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_sum_area", [](const std::string & area_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_sum_area(area_name.c_str(), surface_name.c_str()));
	}, py::arg("area_name") = "*", py::arg("surface_name") = "*");
	m.def("surf_to_mask", [](double true_from, double true_to, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_to_mask(REAL(true_from), REAL(true_to), surface_name.c_str()));
	}, py::arg("true_from"), py::arg("true_to"), py::arg("surface_name") = "*");
	m.def("surf_to_pnts", [](const std::string & surface_name) {
		return drain_boolvec(surfit::surf_to_pnts(surface_name.c_str()));
	}, py::arg("surface_name") = "*");
	m.def("surf_trace_cntr", [](const std::string & surface_name, double step, double from, double to) {
		return drain_boolvec(surfit::surf_trace_cntr(surface_name.c_str(), REAL(step), REAL(from), REAL(to)));
	}, py::arg("surface_name") = "*", py::arg("step") = 3.4028234663852886e38, py::arg("from") = 3.4028234663852886e38, py::arg("to") = 3.4028234663852886e38);
	m.def("surf_undef", [](double new_undef_value, const std::string & surface_name) {
		return drain_boolvec(surfit::surf_undef(REAL(new_undef_value), surface_name.c_str()));
	}, py::arg("new_undef_value"), py::arg("surface_name") = "*");
	m.def("surf_wmean", [](const std::string & wsurface_name, const std::string & surface_name) {
		return drain_vec(surfit::surf_wmean(wsurface_name.c_str(), surface_name.c_str()));
	}, py::arg("wsurface_name") = "*", py::arg("surface_name") = "*");

	// --- points, masks, grids, contours -------------------------------
	m.def("area_load", [](const std::string & filename, const py::object & area_name) {
		std::string area_name_storage;
		return drain_boolvec(surfit::area_load(filename.c_str(), opt_cstr(area_name, area_name_storage)));
	}, py::arg("filename"), py::arg("area_name") = py::none());
	m.def("cntr_div_real", [](double value, const std::string & cntr_name) {
		return drain_boolvec(surfit::cntr_div_real(REAL(value), cntr_name.c_str()));
	}, py::arg("value"), py::arg("cntr_name") = "*");
	m.def("cntr_minus_real", [](double value, const std::string & cntr_name) {
		return drain_boolvec(surfit::cntr_minus_real(REAL(value), cntr_name.c_str()));
	}, py::arg("value"), py::arg("cntr_name") = "*");
	m.def("cntr_plus_real", [](double value, const std::string & cntr_name) {
		return drain_boolvec(surfit::cntr_plus_real(REAL(value), cntr_name.c_str()));
	}, py::arg("value"), py::arg("cntr_name") = "*");
	m.def("cntr_smooth", [](const std::string & cntr_name, size_t cnt) {
		return drain_boolvec(surfit::cntr_smooth(cntr_name.c_str(), cnt));
	}, py::arg("cntr_name") = "*", py::arg("cnt") = 1);
	m.def("cntr_to_curv", [](const std::string & cntr_name) {
		return drain_boolvec(surfit::cntr_to_curv(cntr_name.c_str()));
	}, py::arg("cntr_name") = "*");
	m.def("grid2", [](double stepX, double stepY, double percent, const py::object & gridname) {
		std::string gridname_storage;
		return surfit::grid2(REAL(stepX), REAL(stepY), REAL(percent), opt_cstr(gridname, gridname_storage));
	}, py::arg("stepX") = 0, py::arg("stepY") = 0, py::arg("percent") = 2, py::arg("gridname") = py::none());
	m.def("grid_check", []() {
		return surfit::grid_check();
	}, "true when the target grid has been defined");
	m.def("grid_get2", [](double startX, double endX, double stepX, double startY, double endY, double stepY, const py::object & gridname) {
		std::string gridname_storage;
		return surfit::grid_get2(REAL(startX), REAL(endX), REAL(stepX), REAL(startY), REAL(endY), REAL(stepY), opt_cstr(gridname, gridname_storage));
	}, py::arg("startX"), py::arg("endX"), py::arg("stepX"), py::arg("startY"), py::arg("endY"), py::arg("stepY"), py::arg("gridname") = py::none());
	m.def("grid_get_for_pnts", [](int Xnodes, int Ynodes, const std::string & points_name, const py::object & gridname) {
		std::string gridname_storage;
		return surfit::grid_get_for_pnts(Xnodes, Ynodes, points_name.c_str(), opt_cstr(gridname, gridname_storage));
	}, py::arg("Xnodes"), py::arg("Ynodes"), py::arg("points_name") = "*", py::arg("gridname") = py::none());
	m.def("grid_get_for_pnts_step", [](double stepX, double stepY, const std::string & points_name, const py::object & gridname) {
		std::string gridname_storage;
		return surfit::grid_get_for_pnts_step(REAL(stepX), REAL(stepY), points_name.c_str(), opt_cstr(gridname, gridname_storage));
	}, py::arg("stepX"), py::arg("stepY"), py::arg("points_name") = "*", py::arg("gridname") = py::none());
	m.def("grid_get_from_surf", [](const std::string & surface_name, const py::object & gridname) {
		std::string gridname_storage;
		return surfit::grid_get_from_surf(surface_name.c_str(), opt_cstr(gridname, gridname_storage));
	}, py::arg("surface_name") = "*", py::arg("gridname") = py::none());
	m.def("grid_load", [](const std::string & filename, const py::object & gridname) {
		std::string gridname_storage;
		return surfit::grid_load(filename.c_str(), opt_cstr(gridname, gridname_storage));
	}, py::arg("filename"), py::arg("gridname") = py::none());
	m.def("grid_save", [](const std::string & filename) {
		return surfit::grid_save(filename.c_str());
	}, py::arg("filename"));
	m.def("mask_and", [](const std::string & mask1_name, const std::string & mask2_name) {
		surfit::mask_and(mask1_name.c_str(), mask2_name.c_str());
	}, py::arg("mask1_name") = "*", py::arg("mask2_name") = "*");
	m.def("mask_apply_to_surf", [](const std::string & mask_name, const std::string & surface_name) {
		return drain_boolvec(surfit::mask_apply_to_surf(mask_name.c_str(), surface_name.c_str()));
	}, py::arg("mask_name") = "*", py::arg("surface_name") = "*");
	m.def("mask_from_surf", [](const std::string & surface_name) {
		surfit::mask_from_surf(surface_name.c_str());
	}, py::arg("surface_name") = "*");
	m.def("mask_not", [](const std::string & mask1_name, const std::string & mask2_name) {
		surfit::mask_not(mask1_name.c_str(), mask2_name.c_str());
	}, py::arg("mask1_name") = "*", py::arg("mask2_name") = "*");
	m.def("mask_or", [](const std::string & mask1_name, const std::string & mask2_name) {
		surfit::mask_or(mask1_name.c_str(), mask2_name.c_str());
	}, py::arg("mask1_name") = "*", py::arg("mask2_name") = "*");
	m.def("mask_to_surf", [](const std::string & mask_name) {
		surfit::mask_to_surf(mask_name.c_str());
	}, py::arg("mask_name") = "*");
	m.def("mask_xor", [](const std::string & mask1_name, const std::string & mask2_name) {
		surfit::mask_xor(mask1_name.c_str(), mask2_name.c_str());
	}, py::arg("mask1_name") = "*", py::arg("mask2_name") = "*");
	m.def("pnts_abs", [](const std::string & points_name) {
		return drain_boolvec(surfit::pnts_abs(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_add_noise", [](double std, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_add_noise(REAL(std), points_name.c_str()));
	}, py::arg("std"), py::arg("points_name") = "*");
	m.def("pnts_concat", [](const std::string & points_name1, const std::string & points_name2) {
		return drain_boolvec(surfit::pnts_concat(points_name1.c_str(), points_name2.c_str()));
	}, py::arg("points_name1"), py::arg("points_name2"));
	m.def("pnts_div", [](const std::string & points_name1, const std::string & points_name2) {
		return drain_boolvec(surfit::pnts_div(points_name1.c_str(), points_name2.c_str()));
	}, py::arg("points_name1"), py::arg("points_name2"));
	m.def("pnts_div_real", [](double val, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_div_real(REAL(val), points_name.c_str()));
	}, py::arg("val"), py::arg("points_name") = "*");
	m.def("pnts_div_surf", [](const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_div_surf(points_name.c_str(), surf_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("surf_name") = "*");
	m.def("pnts_filter_by_mask", [](const std::string & points_name, const std::string & mask_name) {
		return drain_boolvec(surfit::pnts_filter_by_mask(points_name.c_str(), mask_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("mask_name") = "*");
	m.def("pnts_filter_by_surf", [](double eps, const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_filter_by_surf(REAL(eps), points_name.c_str(), surf_name.c_str()));
	}, py::arg("eps"), py::arg("points_name") = "*", py::arg("surf_name") = "*");
	m.def("pnts_inverse_transform", [](double shiftX, double scaleX, double shiftY, double scaleY, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_inverse_transform(REAL(shiftX), REAL(scaleX), REAL(shiftY), REAL(scaleY), points_name.c_str()));
	}, py::arg("shiftX"), py::arg("scaleX"), py::arg("shiftY"), py::arg("scaleY"), py::arg("points_name") = "*");
	m.def("pnts_maxx", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_maxx(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_maxy", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_maxy(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_maxz", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_maxz(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_mean", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_mean(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_minus", [](const std::string & points_name1, const std::string & points_name2) {
		return drain_boolvec(surfit::pnts_minus(points_name1.c_str(), points_name2.c_str()));
	}, py::arg("points_name1"), py::arg("points_name2"));
	m.def("pnts_minus_real", [](double val, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_minus_real(REAL(val), points_name.c_str()));
	}, py::arg("val"), py::arg("points_name") = "*");
	m.def("pnts_minus_surf", [](const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_minus_surf(points_name.c_str(), surf_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("surf_name") = "*");
	m.def("pnts_minx", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_minx(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_miny", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_miny(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_minz", [](const std::string & points_name) {
		return drain_vec(surfit::pnts_minz(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_mult", [](const std::string & points_name1, const std::string & points_name2) {
		return drain_boolvec(surfit::pnts_mult(points_name1.c_str(), points_name2.c_str()));
	}, py::arg("points_name1"), py::arg("points_name2"));
	m.def("pnts_mult_surf", [](const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_mult_surf(points_name.c_str(), surf_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("surf_name") = "*");
	m.def("pnts_plus", [](const std::string & points_name1, const std::string & points_name2) {
		return drain_boolvec(surfit::pnts_plus(points_name1.c_str(), points_name2.c_str()));
	}, py::arg("points_name1"), py::arg("points_name2"));
	m.def("pnts_plus_real", [](double val, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_plus_real(REAL(val), points_name.c_str()));
	}, py::arg("val"), py::arg("points_name") = "*");
	m.def("pnts_plus_surf", [](const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_plus_surf(points_name.c_str(), surf_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("surf_name") = "*");
	m.def("pnts_rotate", [](double centerX, double centerY, double angle, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_rotate(REAL(centerX), REAL(centerY), REAL(angle), points_name.c_str()));
	}, py::arg("centerX"), py::arg("centerY"), py::arg("angle"), py::arg("points_name") = "*");
	m.def("pnts_set_real", [](double val, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_set_real(REAL(val), points_name.c_str()));
	}, py::arg("val"), py::arg("points_name") = "*");
	m.def("pnts_set_surf", [](const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_set_surf(points_name.c_str(), surf_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("surf_name") = "*");
	m.def("pnts_std", [](double mean, const std::string & points_name) {
		return drain_vec(surfit::pnts_std(REAL(mean), points_name.c_str()));
	}, py::arg("mean"), py::arg("points_name") = "*");
	m.def("pnts_to_cntrs", [](const std::string & points_name) {
		return drain_boolvec(surfit::pnts_to_cntrs(points_name.c_str()));
	}, py::arg("points_name") = "*");
	m.def("pnts_transform", [](double shiftX, double scaleX, double shiftY, double scaleY, const std::string & points_name) {
		return drain_boolvec(surfit::pnts_transform(REAL(shiftX), REAL(scaleX), REAL(shiftY), REAL(scaleY), points_name.c_str()));
	}, py::arg("shiftX"), py::arg("scaleX"), py::arg("shiftY"), py::arg("scaleY"), py::arg("points_name") = "*");
	m.def("pnts_update_by_surf", [](const std::string & points_name, const std::string & surf_name) {
		return drain_boolvec(surfit::pnts_update_by_surf(points_name.c_str(), surf_name.c_str()));
	}, py::arg("points_name") = "*", py::arg("surf_name") = "*");

	// The columns and the delimiter are part of the command: `area_read` reads
	// a table, and an area file whose coordinates are not in columns 1 and 2
	// (press2's ZAM1.txt puts the name first) cannot be loaded without them.
	m.def("area_read", [](const std::string & path, py::object name,
	                      int col1, int col2, const std::string & delimiter,
	                      int skip_lines, int grow_by) {
		std::string storage;
		return drain_boolvec(area_read(path.c_str(), opt_cstr(name, storage),
		                               col1, col2, delimiter.c_str(),
		                               skip_lines, grow_by));
	}, py::arg("path"), py::arg("name") = py::none(),
	   py::arg("col1") = 1, py::arg("col2") = 2, py::arg("delimiter") = " \t",
	   py::arg("skip_lines") = 0, py::arg("grow_by") = 250,
	   "read areas from a text file, one row per node");

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
	m.def("get_solver_long_name", &surfit::get_solver_long_name, py::arg("pos"),
	      "description of the pos-th solver");

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

	// ---- dataset utilities -------------------------------------------------

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

	// Overloaded in C++ (the other one is the triangulation entry point), hence
	// the lambda rather than a plain function pointer.
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
