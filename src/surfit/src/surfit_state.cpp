
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

#include <float.h>

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

static surfit_state * active_state = NULL;

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

surfit_state * state_origin() {
	static surfit_state * origin = NULL;
	if (origin == NULL) {
		origin = new surfit_state();
		globals_to_state(origin);
		if (active_state == NULL)
			active_state = origin;
	}
	return origin;
}

surfit_state * state_active() {
	if (active_state == NULL)
		state_origin();
	return active_state;
}

surfit_state * state_create() {
	surfit_state * state = new surfit_state();

	state->areas = new areas_container();
	state->cntrs = new cntrs_container();
	state->curvs = new curvs_container();
	state->hists = new hists_container();
	state->masks = new masks_container();
	state->pnts = new pnts_container();
	state->surfs = new surfs_container();

	state->functionals = new std::vector<functional *>;
	state->grid = NULL;

	// The same defaults surfit_init_all() installs.
	state->tol = float(1e-5);
	state->undef_value = FLT_MAX;
	state->sor_omega = REAL(1.6);
	state->ssor_omega = REAL(1.6);
	state->write_mat = false;
	state->map_name = NULL;
	state->solver_name = NULL;
	state->reproject_faults = 1;
	state->reproject_undef_areas = 0;
	state->process_isolated_areas = 1;
	state->penalty_max_iter = 99;
	state->penalty_weight = REAL(1);
	state->penalty_weight_mult = REAL(10);
	state->stop_execution = false;

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

	return state;
}

void state_install(surfit_state * state) {
	if (state == NULL)
		return;

	if (active_state == NULL)
		state_origin();

	if (active_state == state)
		return;

	// The engine writes straight into the globals, so the outgoing state has to
	// be read back out before it is replaced.
	globals_to_state(active_state);
	state_to_globals(state);

	active_state = state;
}

void state_release(surfit_state * state) {
	if (state == NULL)
		return;

	// The origin belongs to the library and is freed with it.
	if (state == state_origin())
		return;

	if (active_state == state)
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

	delete state;
}

};// namespace surfit
