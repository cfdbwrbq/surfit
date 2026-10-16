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
#include "grid_tcl.h"
#include "area_tcl.h"
#include "curvs_tcl.h"
#include "surf_tcl.h"
#include "cmofs.h"
#include "variables_tcl.h"
#include "surf.h"

namespace py = pybind11;

using surfit::area;
using surfit::area_add;
using surfit::area_read;
using surfit::boolvec;
using surfit::clear_data;
using surfit::completer;
using surfit::d_surf;
using surfit::grid_get;
using surfit::map_name;
using surfit::surf_save;
using surfit::surfit_surfs;
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

}  // namespace

PYBIND11_MODULE(_surfit, m) {
	m.doc() = "surfit gridding engine -- C++ core bindings (stage L1)";

	// Without a Tcl interpreter the core suppresses console output; log_open()
	// still writes the log file.  A real logging bridge is the next L1 step.
	// NB: the log levels are macros, so LOG_MESSAGE cannot be namespace-qualified.
	m.def("log_open", [](int level, const std::string & path) {
		return surfit::log_open(level, path.empty() ? NULL : path.c_str());
	}, py::arg("level") = 1 /* LOG_MESSAGE */, py::arg("path") = std::string());

	m.def("clear_data", &clear_data, "drop all loaded data and gridding rules");
	m.def("set_map_name", &set_map_name, "name given to the resulting surface");
	m.def("map_name", &get_map_name);

	// Global solver settings.  In the Tcl front end these are traced variables
	// (that is why scripts do `set tol 1e-5`).
	m.def("set_tol", [](float value) { surfit::tol = value; },
	      "tolerance for the iterative solver");
	m.def("get_tol", []() { return surfit::tol; });

	m.def("area_read", [](const std::string & path, const std::string & name) {
		return drain_boolvec(area_read(path.c_str(), name.c_str()));
	}, py::arg("path"), py::arg("name"));

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

	m.def("area", [](const std::string & value, const std::string & name) {
		return drain_boolvec(area(value.c_str(), name.c_str()));
	}, py::arg("value"), py::arg("name") = "*");

	m.def("area_add", [](double value, double weight, const std::string & name) {
		return drain_boolvec(area_add(value, weight, name.c_str()));
	}, py::arg("value"), py::arg("weight"), py::arg("name") = "*");

	m.def("completer", &completer,
	      py::arg("D1") = 1, py::arg("D2") = 2,
	      py::arg("alpha") = 0, py::arg("w") = 1);

	m.def("surfit", []() { surfit::surfit(); }, "run the gridding algorithm");

	m.def("surf_save", [](const std::string & path, const std::string & name) {
		return drain_boolvec(surf_save(path.c_str(), name.c_str()));
	}, py::arg("path"), py::arg("name") = "*");

	m.def("surf_count", &surf_count, "number of surfaces in memory");
	m.def("surf_name_at", &surf_name_at, py::arg("pos"));
	m.def("surf_values", &surf_values, py::arg("pos"),
	      "surface values as a (count_y, count_x) float64 array");
}
