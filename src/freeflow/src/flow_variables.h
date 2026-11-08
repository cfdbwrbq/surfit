
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

#ifndef __surfit_flow_variables_included__
#define __surfit_flow_variables_included__

#include <vector>

namespace surfit {

#define FREEFLOW_VERSION "3.0"

/*! registers libfreeflow with the process-wide data manager, once
 *
 *	Freeflow has no per-task plugin state: the flow rules are ordinary
 *	functionals in the active task's list (surfit_state::functionals), and the
 *	manager registered here is a stateless dispatcher over that list.  The
 *	process-wide data_manager owns and frees the manager, so there is no
 *	global pointer to a plugin singleton.
 */
FLOW_EXPORT
void freeflow_init_variables();

}; // namespace surfit;

#endif

