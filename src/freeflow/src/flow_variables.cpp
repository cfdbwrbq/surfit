
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

#include "flow_ie.h"

#include <string.h>

#include "fileio.h"

#include "flow_variables.h"
#include "flow_data_manager.h"
#include "data_manager.h"
#include "variables.h"


namespace surfit {

/*! Whether the process already has the freeflow data manager.
 *
 *	The manager is a stateless dispatcher over the engine's globals: the flow
 *	rules themselves are ordinary functionals in the active task's list, so
 *	the plugin has no per-task data of its own and needs no per-task context.
 *	Its registration is process-wide, and the process-wide data_manager owns
 *	and frees the manager, just as it owns the core's own manager.  The old
 *	flow_manager pointer was a second owner that could release it twice.
 */
static bool freeflow_manager_registered() {
	if (surfit_data_manager == NULL)
		return false;

	size_t i;
	for (i = 0; i < surfit_data_manager->get_managers_count(); i++) {
		const manager * man = surfit_data_manager->get_manager(i);
		if (man != NULL && strcmp(man->getName(), "freeflow") == 0)
			return true;
	}
	return false;
}

void freeflow_init_variables() {

	// Idempotent: the Tcl plugin, the Python module and an embedding may each
	// call it, and only one freeflow manager may exist.
	if (freeflow_manager_registered())
		return;

	add_manager(new freeflow_manager);

#ifdef XXL
	log_printf("loading module freeflow v%s (XXL build)\n", FREEFLOW_VERSION);
#else
	log_printf("loading module freeflow v%s\n", FREEFLOW_VERSION);
#endif

};


}; // namespace surfit;
