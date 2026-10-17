
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

#ifndef __surfit_state_included__
#define __surfit_state_included__

#include "surfit_ie.h"
#include "vec.h"

#include <cstddef>
#include <vector>

namespace surfit {

class areas_container;
class cntrs_container;
class curvs_container;
class hists_container;
class masks_container;
class pnts_container;
class surfs_container;
class d_grid;
class bitvec;
class functional;

/*! \file
    \brief one task's state

    The engine has always kept its working data in globals: the seven object
    containers, the gridding rules, the target grid, and the settings around
    them.  That is fine for a program that does one thing, and wrong for a
    process that wants two tasks -- creating a second task used to wipe the
    first without a word.

    A surfit_state holds one complete set of those globals.  The globals stay
    the place the engine reads and writes; installing a state copies it into
    them, and the state that was installed before is copied back out first, so
    nothing is lost while a task is not active.

    Only one state is active at a time, which is what makes the swap cheap.  Two
    tasks can therefore be interleaved in one thread -- one per notebook cell,
    say -- but not run concurrently from two threads.
*/
struct SURFIT_EXPORT surfit_state {
	//! loaded and produced objects
	areas_container * areas;
	cntrs_container * cntrs;
	curvs_container * curvs;
	hists_container * hists;
	masks_container * masks;
	pnts_container * pnts;
	surfs_container * surfs;

	//! gridding rules, in the order they were added
	std::vector<functional *> * functionals;

	//! the target grid
	d_grid * grid;

	//! settings
	float tol;
	REAL undef_value;
	REAL sor_omega;
	REAL ssor_omega;
	bool write_mat;
	char * map_name;
	char * solver_name;
	int reproject_faults;
	int reproject_undef_areas;
	int process_isolated_areas;
	size_t penalty_max_iter;
	REAL penalty_weight;
	REAL penalty_weight_mult;
	bool stop_execution;

	//! scratch space of the solver
	d_grid * method_grid;
	d_grid * method_prev_grid;
	extvec * method_X;
	bitvec * method_mask_solved;
	bitvec * method_mask_undefined;
	size_t method_basis_cntX;
	size_t method_basis_cntY;
	size_t method_phase_counter;
	size_t basis_cnt;
	size_t penalty_iter_counter;
};

//! the state the library was initialised with, captured on first use
SURFIT_EXPORT surfit_state * state_origin();

//! the state currently installed in the globals
SURFIT_EXPORT surfit_state * state_active();

//! a new empty state, with the default settings
SURFIT_EXPORT surfit_state * state_create();

//! makes \a state the active one, saving whatever was active before
SURFIT_EXPORT void state_install(surfit_state * state);

//! frees a state and everything it holds; the origin state is left alone
SURFIT_EXPORT void state_release(surfit_state * state);

};// namespace surfit

#endif
