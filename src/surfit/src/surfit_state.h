
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
class data_manager;
struct sstuff_state;

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

    The globals and the installed-state pointer are thread_local.  Each thread
    therefore has its own view of the engine, and two tasks can run in two
    threads at the same time.  A state can be created in one thread and used in
    another: installing it copies its snapshot into the calling thread's
    globals.  Releasing a state clears it out of every thread that still has it
    installed, so the next install in that thread starts from the library state.
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

	//! per-task manager list; borrowed managers are shared
	data_manager * data;
	bool owns_data;

	//! per-task sstuff context: worker pool, log, file search, RNG
	sstuff_state * sstuff;

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

//! the library state of the calling thread, captured on first use
SURFIT_EXPORT surfit_state * state_origin();

//! the state currently installed in the calling thread's globals
SURFIT_EXPORT surfit_state * state_active();

//! a new empty state, with the default settings
SURFIT_EXPORT surfit_state * state_create();

/*! \brief captures the library defaults used by threads that have no state yet

    A front end that may use the library from more than one thread calls this
    from its initialisation, in the thread the globals were initialised in, so
    the defaults are complete (managers registered, settings final).  Calling it
    again is harmless; the first call wins.
*/
SURFIT_EXPORT void state_init_defaults();

/*! \brief makes \a state the calling thread's active one

    The outgoing state is written back to its snapshot first, even when it is
    already the active one, so a task built in one thread can be installed in
    another without losing the values the build left in the globals.
*/
SURFIT_EXPORT void state_install(surfit_state * state);

/*! \brief writes the calling thread's globals back into the installed state

    A command runs straight on the globals, so a task finished in one thread and
    used in another would otherwise be installed with the snapshot its fields
    had before the last command.  The Session wrapper calls this after every
    command.
*/
SURFIT_EXPORT void state_store();

/*! \brief frees a state and everything it holds; the origin state is left alone

    Every thread that still has the state installed is switched back to its
    library state first, so no thread keeps a pointer to the freed task.
*/
SURFIT_EXPORT void state_release(surfit_state * state);

};// namespace surfit

#endif
