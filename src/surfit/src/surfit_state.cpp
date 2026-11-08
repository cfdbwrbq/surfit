
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

#include "surfit_ie.h"
#include "surfit_state.h"

#include "area.h"
#include "cntr.h"
#include "curv.h"
#include "hist.h"
#include "mask.h"
#include "points.h"
#include "surf.h"
#include "grid.h"
#include "grid_user.h"
#include "cmofs.h"
#include "vec.h"
#include "bitvec.h"
#include "functional.h"
#include "free_elements.h"

#include "variables.h"
#include "variables_tcl.h"
#include "variables_internal.h"

#include "data_manager.h"
#include "sstuff_state.h"

#include <float.h>
#include <stdlib.h>
#include <string.h>

#include <mutex>
#include <thread>
#include <vector>

namespace surfit {

/*! Every global a task owns, in one list.
 *
 *	The three functions below walk this list, so a field cannot be forgotten in
 *	one of them and remembered in another.
 */
#define SURFIT_STATE_FIELDS(X)                                          \
	X(areas_container *, areas, surfit_areas)                           \
	X(cntrs_container *, cntrs, surfit_cntrs)                           \
	X(curvs_container *, curvs, surfit_curvs)                           \
	X(hists_container *, hists, surfit_hists)                           \
	X(masks_container *, masks, surfit_masks)                           \
	X(pnts_container *, pnts, surfit_pnts)                              \
	X(surfs_container *, surfs, surfit_surfs)                           \
	X(std::vector<functional *> *, functionals, functionals)            \
	X(data_manager *, data, surfit_data_manager)                       \
	X(d_grid *, grid, surfit_grid)                                      \
	X(float, tol, tol)                                                  \
	X(REAL, undef_value, undef_value)                                   \
	X(REAL, sor_omega, sor_omega)                                       \
	X(REAL, ssor_omega, ssor_omega)                                     \
	X(bool, write_mat, write_mat)                                       \
	X(char *, map_name, map_name)                                       \
	X(char *, solver_name, solver_name)                                 \
	X(int, reproject_faults, reproject_faults)                          \
	X(int, reproject_undef_areas, reproject_undef_areas)                \
	X(int, process_isolated_areas, process_isolated_areas)              \
	X(size_t, penalty_max_iter, penalty_max_iter)                       \
	X(REAL, penalty_weight, penalty_weight)                             \
	X(REAL, penalty_weight_mult, penalty_weight_mult)                   \
	X(bool, stop_execution, stop_execution)                             \
	X(d_grid *, method_grid, method_grid)                               \
	X(d_grid *, method_prev_grid, method_prev_grid)                     \
	X(extvec *, method_X, method_X)                                     \
	X(bitvec *, method_mask_solved, method_mask_solved)                 \
	X(bitvec *, method_mask_undefined, method_mask_undefined)           \
	X(size_t, method_basis_cntX, method_basis_cntX)                     \
	X(size_t, method_basis_cntY, method_basis_cntY)                     \
	X(size_t, method_phase_counter, method_phase_counter)               \
	X(size_t, basis_cnt, basis_cnt)                                     \
	X(size_t, penalty_iter_counter, penalty_iter_counter)

/*! The state installed in this thread's globals.
 *
 *	Every thread owns one.  The engine's globals are thread_local as well, so
 *	two threads can each have a different task installed at the same time; this
 *	pointer says which task *this* thread's globals currently hold.
 */
static thread_local surfit_state * active_state = NULL;

static void globals_to_state(surfit_state * state) {
#define SURFIT_STATE_OUT(type, field, global) state->field = global;
	SURFIT_STATE_FIELDS(SURFIT_STATE_OUT)
#undef SURFIT_STATE_OUT
}

static void state_to_globals(const surfit_state * state) {
#define SURFIT_STATE_IN(type, field, global) global = state->field;
	SURFIT_STATE_FIELDS(SURFIT_STATE_IN)
#undef SURFIT_STATE_IN
}

namespace {

/*
 * Releasing a state has to clear it out of every thread that may still have it
 * installed.  A thread's active_state is a thread_local pointer, so the only
 * way to reach it from another thread is to remember its address: each thread
 * registers the address of its slot once and unregisters it on exit.  The
 * process-wide tables are deliberately leaked (allocated with new, never
 * destroyed): a worker thread may exit during static destruction, and its
 * unregister step must not touch an already-destroyed container.
 */
std::mutex & active_slot_mutex() {
	static std::mutex * mutex = new std::mutex;
	return *mutex;
}

std::vector<surfit_state **> & active_slots() {
	static std::vector<surfit_state **> * slots =
		new std::vector<surfit_state **>;
	return *slots;
}

//! removes this thread's slot when the thread exits
struct active_slot_guard {
	~active_slot_guard() {
		std::lock_guard<std::mutex> lock(active_slot_mutex());
		std::vector<surfit_state **> & slots = active_slots();
		for (size_t i = 0; i < slots.size(); i++) {
			if (slots[i] == &active_state) {
				slots.erase(slots.begin() + i);
				break;
			}
		}
	}
};

thread_local bool active_slot_registered = false;

void ensure_active_slot_registered() {
	if (active_slot_registered)
		return;
	// Constructing the guard registers the thread exit cleanup; the slot is
	// visible to state_release() from that point on.
	static thread_local active_slot_guard guard;
	(void)guard;
	std::lock_guard<std::mutex> lock(active_slot_mutex());
	active_slots().push_back(&active_state);
	active_slot_registered = true;
}

//! clears the released state out of every thread's active slot
void clear_active_slots(surfit_state * state) {
	std::lock_guard<std::mutex> lock(active_slot_mutex());
	std::vector<surfit_state **> & slots = active_slots();
	for (size_t i = 0; i < slots.size(); i++) {
		if (*slots[i] == state)
			*slots[i] = NULL;
	}
}

/*
 * Every thread needs a library state (the state module-level calls run on).  A
 * thread that never has a task installed derives one from this process-wide,
 * immutable template: the defaults captured after library initialisation, in
 * the thread that owns the globals the library was initialised in.  The
 * capture thread itself keeps using its live globals as the library state, so
 * module-level data and settings still survive a switch to another task.
 */
std::mutex & defaults_mutex() {
	static std::mutex * mutex = new std::mutex;
	return *mutex;
}

surfit_state * library_defaults = NULL;
std::thread::id defaults_thread;

//! fills library_defaults from the globals; the caller holds defaults_mutex()
void capture_library_defaults() {
	if (library_defaults != NULL)
		return;
	library_defaults = new surfit_state();
	globals_to_state(library_defaults);
	library_defaults->owns_data = false;
	library_defaults->sstuff = sstuff_state_origin();
	defaults_thread = std::this_thread::get_id();
}

/*! \brief a private library state for a thread that has none yet
 *
 *	The default's containers are copied as new empty ones: module-level data
 *	loaded in one thread is not silently visible in another.  The managers are
 *	borrowed, exactly like a task's manager list, because they are stateless
 *	dispatchers.  The names are copied because they are owned strings.
 */
surfit_state * clone_library_state(const surfit_state * source) {
	surfit_state * state = new surfit_state();
	*state = *source;

	state->areas = new areas_container();
	state->cntrs = new cntrs_container();
	state->curvs = new curvs_container();
	state->hists = new hists_container();
	state->masks = new masks_container();
	state->pnts = new pnts_container();
	state->surfs = new surfs_container();
	state->functionals = new std::vector<functional *>;

	state->data = new data_manager(false);
	state->owns_data = false;
	if (source->data) {
		for (size_t i = 0; i < source->data->get_managers_count(); i++)
			state->data->add_manager(
				const_cast<manager *>(source->data->get_manager(i)));
	}

	state->sstuff = sstuff_state_create();
	if (source->sstuff)
		sstuff_state_copy_settings(state->sstuff, source->sstuff);

	state->grid = NULL;
	state->method_grid = NULL;
	state->method_prev_grid = NULL;
	state->method_X = NULL;
	state->method_mask_solved = NULL;
	state->method_mask_undefined = NULL;

	state->map_name = source->map_name ? strdup(source->map_name) : NULL;
	state->solver_name = source->solver_name ? strdup(source->solver_name)
	                                         : NULL;

	return state;
}

} // anonymous namespace

void state_init_defaults() {
	std::lock_guard<std::mutex> lock(defaults_mutex());
	capture_library_defaults();
}

surfit_state * state_origin() {
	static thread_local surfit_state * origin = NULL;
	if (origin != NULL)
		return origin;

	std::lock_guard<std::mutex> lock(defaults_mutex());
	capture_library_defaults();

	ensure_active_slot_registered();
	if (std::this_thread::get_id() == defaults_thread) {
		// The capture thread's globals already hold the library state; taking
		// them keeps module-level data and settings alive across a switch.
		origin = new surfit_state();
		globals_to_state(origin);
		origin->owns_data = false;
		origin->sstuff = sstuff_state_origin();
	} else {
		origin = clone_library_state(library_defaults);
	}
	return origin;
}

surfit_state * state_active() {
	if (active_state == NULL)
		state_install(state_origin());
	return active_state;
}

surfit_state * state_create() {
	surfit_state * origin = state_origin();

	// The origin holds the library's defaults, but while it is the active state
	// the globals are where the settings actually live.  Sync it so a new task
	// starts from the settings in force, not from the values the origin was
	// created with.
	if (active_state == origin)
		globals_to_state(origin);

	surfit_state * state = new surfit_state();

	// Settings are inherited from the library's own state rather than repeated
	// here: a default typed twice is a default that can disagree with itself.
	*state = *origin;

	// The two names are the exception.  set_map_name() and set_solver() free the
	// old pointer before storing the new one, so a borrowed pointer would be
	// freed by the next task that sets a name and then freed again by the task
	// it was borrowed from.  Copy them here, and release the copies in
	// state_release().
	state->map_name = origin->map_name ? strdup(origin->map_name) : NULL;
	state->solver_name = origin->solver_name ? strdup(origin->solver_name) : NULL;

	// What a task owns is new and empty.
	state->areas = new areas_container();
	state->cntrs = new cntrs_container();
	state->curvs = new curvs_container();
	state->hists = new hists_container();
	state->masks = new masks_container();
	state->pnts = new pnts_container();
	state->surfs = new surfs_container();

	state->functionals = new std::vector<functional *>;

	// Managers are stateless dispatchers over the task globals; the state gets
	// its own manager list but borrows the manager objects.
	state->data = new data_manager(false);
	state->owns_data = true;
	state->sstuff = sstuff_state_create();
	if (origin->sstuff)
		sstuff_state_copy_settings(state->sstuff, origin->sstuff);
	if (origin->data) {
		for (size_t i = 0; i < origin->data->get_managers_count(); i++)
			state->data->add_manager(const_cast<manager *>(origin->data->get_manager(i)));
	}

	state->grid = NULL;

	state->method_grid = NULL;
	state->method_prev_grid = NULL;
	state->method_X = NULL;
	state->method_mask_solved = NULL;
	state->method_mask_undefined = NULL;
	state->method_basis_cntX = GRID_START_SIZE;
	state->method_basis_cntY = GRID_START_SIZE;
	state->method_phase_counter = 0;
	state->basis_cnt = GRID_START_SIZE;
	state->penalty_iter_counter = 0;
	state->stop_execution = false;

	return state;
}

void state_install(surfit_state * state) {
	if (state == NULL)
		return;

	surfit_state * origin = state_origin();
	ensure_active_slot_registered();

	// First call in this thread, or the state this thread had installed was
	// released by another thread: start from this thread's library state.  The
	// thread's globals may point at a released task, so they are overwritten,
	// never read.
	if (active_state == NULL) {
		state_to_globals(origin);
		// Bind the sstuff mirrors only: installing the library state here would
		// start a worker pool that a thread solving a task never uses.
		sstuff_state_apply_settings(origin->sstuff);
		active_state = origin;
	}

	// The globals are the live values, so whichever state they hold is written
	// back first -- even when that is the state being installed.  Without this,
	// a task built in one thread would be installed in another with the stale
	// snapshot its fields had when the build started (tol, grid, scratch).
	globals_to_state(active_state);

	if (active_state == state) {
		if (state != origin)
			sstuff_state_install(active_state->sstuff);
		return;
	}

	state_to_globals(state);
	sstuff_state_install(state->sstuff);
	active_state = state;
}

void state_store() {
	if (active_state == NULL)
		return;
	globals_to_state(active_state);
	// The sstuff mirrors are globals too; write them into the installed context
	// (a no-op when the installed context is a different object).
	sstuff_state_store(active_state->sstuff);
}

void state_release(surfit_state * state) {
	if (state == NULL)
		return;

	// The origin belongs to the library and is freed with it.
	if (state == state_origin())
		return;

	// Clear the state out of every thread before it is freed: another thread
	// may still have it installed, and its next install will bind the library
	// state instead of reading the freed task.
	bool was_active_here = (active_state == state);
	clear_active_slots(state);
	if (was_active_here)
		state_install(state_origin());

	if (state->areas) {
		release_elements(state->areas->begin(), state->areas->end());
		delete state->areas;
	}
	if (state->cntrs) {
		release_elements(state->cntrs->begin(), state->cntrs->end());
		delete state->cntrs;
	}
	if (state->curvs) {
		release_elements(state->curvs->begin(), state->curvs->end());
		delete state->curvs;
	}
	if (state->hists) {
		release_elements(state->hists->begin(), state->hists->end());
		delete state->hists;
	}
	if (state->masks) {
		release_elements(state->masks->begin(), state->masks->end());
		delete state->masks;
	}
	if (state->pnts) {
		release_elements(state->pnts->begin(), state->pnts->end());
		delete state->pnts;
	}
	if (state->surfs) {
		release_elements(state->surfs->begin(), state->surfs->end());
		delete state->surfs;
	}

	if (state->data && state->owns_data)
		delete state->data;
	state->data = NULL;

	if (state->sstuff) {
		sstuff_state_release(state->sstuff);
		state->sstuff = NULL;
	}

	if (state->functionals) {
		size_t i;
		for (i = 0; i < state->functionals->size(); i++) {
			functional * f = (*state->functionals)[i];
			if (f)
				f->release();
		}
		delete state->functionals;
	}

	// The scratch vectors can alias the grid slots, so each is checked against
	// the one it might share before being released.
	if (state->grid)
		state->grid->release();
	if (state->method_grid && state->method_grid != state->grid)
		state->method_grid->release();
	if (state->method_prev_grid && state->method_prev_grid != state->grid)
		state->method_prev_grid->release();
	if (state->method_X)
		state->method_X->release();
	if (state->method_mask_solved)
		state->method_mask_solved->release();
	if (state->method_mask_undefined)
		state->method_mask_undefined->release();

	// The names are this state's own copies (see state_create); the switch to
	// the origin above has already moved the globals off them.
	if (state->map_name) {
		free(state->map_name);
		state->map_name = NULL;
	}
	if (state->solver_name) {
		free(state->solver_name);
		state->solver_name = NULL;
	}

	delete state;
}

}; // namespace surfit
