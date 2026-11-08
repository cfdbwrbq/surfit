
/*------------------------------------------------------------------------------
 *	$Id$
 *
 *	Copyright (c) 2002-2006 by M. V. Dmitrievsky and V. N. Kutrunov
 *	See COPYING file for copying and redistribution conditions.
 *
 *	This program is free software; you can redistribute it and/or modify
 *	it under the terms of the GNU General Public License as published by
 *	the Free Software Foundation; version 2 of the License.
 *
 *	This program is distributed in the hope that it will be useful,
 *	but WITHOUT ANY WARRANTY; without even the implied warranty of
 *	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *	GNU General Public License for more details.
 *
 *	Contact info: surfit.sourceforge.net
 *----------------------------------------------------------------------------*/

#include "globe_ie.h"

#include <string.h>

#include "fileio.h"

#include "globe_state.h"
#include "globe_variables.h"
#include "globe_data_manager.h"
#include "data_manager.h"
#include "variables.h"


namespace surfit {

/*! Whether the process already has the globe data manager.
 *
 *	The manager is a stateless dispatcher over the installed globe_state: it
 *	lets file_load, file_save, clear_data and mem_info carry DEMs.  What a task
 *	owns is the state, not the dispatcher, so the manager is registered once
 *	for the process and the process-wide data_manager owns and frees it, just
 *	as it owns the core's own manager.  Keeping a global pointer to it here
 *	only created a second owner that could release it twice.
 */
static bool globe_manager_registered() {
	if (surfit_data_manager == NULL)
		return false;

	size_t i;
	for (i = 0; i < surfit_data_manager->get_managers_count(); i++) {
		const manager * man = surfit_data_manager->get_manager(i);
		if (man != NULL && strcmp(man->getName(), "globe") == 0)
			return true;
	}
	return false;
}

void globe_init_variables() {

	// Idempotent: the Tcl plugin, the Python module and an embedding may each
	// call it, and only one globe manager may exist.
	if (globe_manager_registered())
		return;

	// The library's own state has to exist before the first command reads
	// globe_dems, and it is what the module-level calls work on.
	globe_state_origin();
	add_manager(new globe_manager);

#ifdef XXL
	log_printf("loading module globe v%s (XXL build)\n", GLOBE_VERSION);
#else
	log_printf("loading module globe v%s\n", GLOBE_VERSION);
#endif

};


}; // namespace surfit;
