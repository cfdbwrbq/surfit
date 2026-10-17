/*------------------------------------------------------------------------------
 *	Helpers shared by the binding translation units.
 *
 *	The core API hands its results over as raw pointers with a release() call
 *	that the caller owes: every command returns a vec, a boolvec, an intvec or
 *	a strvec, and nothing else.  These four functions copy one into Python and
 *	release it, and opt_cstr() turns None into the NULL the C++ API expects for
 *	an absent name.
 *
 *	Licensed under the GNU General Public License, version 2, like the rest of
 *	surfit.
 *----------------------------------------------------------------------------*/

#ifndef SURFIT_PYSURFIT_BIND_COMMON_H
#define SURFIT_PYSURFIT_BIND_COMMON_H

#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>

#include <string>

#include "real.h"
#include "vec.h"
#include "boolvec.h"
#include "intvec.h"
#include "strvec.h"

namespace surfit_py {

/*! Drains a boolvec of per-object success flags and releases it. */
inline pybind11::list drain_boolvec(surfit::boolvec * flags) {
	pybind11::list result;
	if (flags == NULL)
		return result;
	for (size_t i = 0; i < flags->size(); i++)
		result.append(pybind11::bool_((*flags)(i)));
	flags->release();
	return result;
}

/*! A REAL vector result: copied into an array, then released.

	These come back from the statistics commands, which return one value per
	object they matched rather than a flag each.
*/
inline pybind11::array_t<double> drain_vec(surfit::vec * values) {
	if (values == NULL)
		return pybind11::array_t<double>(0);
	const size_t size = values->size();
	pybind11::array_t<double> result(size);
	double * out = result.mutable_data();
	for (size_t i = 0; i < size; i++)
		out[i] = double((*values)(i));
	values->release();
	return result;
}

/*! The integer counterpart, for cell counts and decomposition levels. */
inline pybind11::array_t<int> drain_intvec(surfit::intvec * values) {
	if (values == NULL)
		return pybind11::array_t<int>(0);
	const size_t size = values->size();
	pybind11::array_t<int> result(size);
	int * out = result.mutable_data();
	for (size_t i = 0; i < size; i++)
		out[i] = (*values)(i);
	values->release();
	return result;
}

/*! A strvec of object names, as a Python list of str. */
inline pybind11::list drain_strvec(surfit::strvec * values) {
	pybind11::list result;
	if (values == NULL)
		return result;
	for (size_t i = 0; i < values->size(); i++) {
		const char * name = (*values)(i);
		result.append(pybind11::str(name != NULL ? name : ""));
	}
	values->release();
	return result;
}

/*! The accessors answer NULL for a position that does not exist, which Python
	spells as an empty string rather than a missing value. */
inline std::string cstr_or_empty(const char * text) {
	return text != NULL ? std::string(text) : std::string();
}

/*! Optional-string helper: Python None becomes a NULL C string, matching the
	C++ API, where NULL means "derive the name" or "no name". */
inline const char * opt_cstr(const pybind11::object & value, std::string & storage) {
	if (value.is_none())
		return NULL;
	storage = std::string(pybind11::str(value));
	return storage.c_str();
}

}  // namespace surfit_py

#endif
