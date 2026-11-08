
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

#ifndef __surfit_globe_variables_included__
#define __surfit_globe_variables_included__

#include <vector>

namespace surfit {

#define GLOBE_VERSION "3.0"

/*! registers libglobe with the process-wide data manager, once
 *
 *	The DEM data itself is per task: a host creates a globe_state per task
 *	(globe_state.h) and installs it before the task's calls.  The manager
 *	registered here is a stateless dispatcher over the installed state, so its
 *	registration is process-wide and the process-wide data_manager owns and
 *	frees it; there is no global pointer to a plugin singleton.
 */
GLOBE_EXPORT
void globe_init_variables();

}; // namespace surfit;

#endif

