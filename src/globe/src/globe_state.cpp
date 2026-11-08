/*------------------------------------------------------------------------------
 *	One task's state of the globe plugin.
 *
 *	The DEM commands work on whatever container \ref globe_dems points at and
 *	read the display flag \ref draw_dem, so a host that keeps several tasks
 *	alive can give each one its own globe_state: the state is created by the
 *	task, installed before its calls and released with it.  The library keeps
 *	one state of its own for the commands that run outside any task, which is
 *	what the Tcl front end and the module-level Python functions use.
 *
 *	The old container-level API (globe_dems_create() and friends) is kept for
 *	the front ends that use it today; a container made by it belongs to the
 *	caller, while a container inside a globe_state belongs to that state.
 *
 *	Licensed under the GNU General Public License, version 2, like the rest of
 *	surfit.
 *----------------------------------------------------------------------------*/

#include "globe_ie.h"

#include "globe_state.h"

#include "dem.h"
#include "dem_show.h"
#include "free_elements.h"

namespace surfit {

/*! The state a task owns: the DEM container and the display flag.
 *
 *	The struct is opaque to the host, so the members can change without
 *	touching a front end.
 */
struct globe_state {
	//! the container the DEM commands work on
	dems_container * dems;
	//! whether _dem_show() draws the solid DEM
	int draw_dem;
};

/*! Display flag read by dem_show.cpp.
 *
 *	It is the installed state's value, like \ref globe_dems is the installed
 *	state's container: globe_state_install() copies it in and install() of the
 *	next state copies the current value back out first.
 */
int draw_dem = 1;

//! the installed state; NULL until the first state is asked for
static globe_state * active_state = NULL;

//! the library's own state, captured before anything is installed
static globe_state * library_state = NULL;

globe_state * globe_state_origin() {
	if (library_state == NULL) {
		library_state = new globe_state;
		// dem_garbage in dem.cpp makes the library container at startup.  Keep
		// the same fallback here for an embedding that uses the library
		// without running that static construction.
		if (globe_dems == NULL)
			globe_dems = new dems_container();
		library_state->dems = globe_dems;
		library_state->draw_dem = draw_dem;
		if (active_state == NULL)
			active_state = library_state;
	}
	return library_state;
}

globe_state * globe_state_active() {
	globe_state_origin();
	return active_state;
}

globe_state * globe_state_create() {
	globe_state_origin();
	globe_state * state = new globe_state;
	state->dems = globe_dems_create();
	state->draw_dem = draw_dem;
	return state;
}

void globe_state_install(globe_state * state) {
	if (state == NULL)
		return;

	globe_state_origin();

	if (active_state == state)
		return;

	// The globals may have been changed directly (the container-level API and
	// dem_show.h keep both writable), so the outgoing state is read back out
	// before the new one is copied in.  The container is not read back: it is
	// owned by the state that made it, and a caller-owned container installed
	// through globe_dems_install() must be released by that caller, not by the
	// state that happened to be installed when it appeared.
	active_state->draw_dem = draw_dem;

	globe_dems = state->dems;
	draw_dem = state->draw_dem;
	active_state = state;
}

void globe_state_release(globe_state * state) {
	if (state == NULL)
		return;

	// The origin belongs to the library and is freed with it.
	if (state == globe_state_origin())
		return;

	// Restore the origin first, so the globals never point at the container
	// this function is about to free.
	if (active_state == state)
		globe_state_install(globe_state_origin());

	globe_dems_release(state->dems);
	delete state;
}

dems_container * globe_state_dems(globe_state * state) {
	if (state == NULL)
		return NULL;
	return state->dems;
}

int globe_state_get_draw_dem(globe_state * state) {
	if (state == NULL)
		return draw_dem;
	return state->draw_dem;
}

void globe_state_set_draw_dem(globe_state * state, int draw) {
	if (state == NULL)
		return;
	state->draw_dem = draw;
	if (active_state == state)
		draw_dem = draw;
}

//
// The container-level API kept for the front ends that use it today.
//
// A container made by globe_dems_create() belongs to the caller; the library's
// own container is the one inside globe_state_origin() and is not freed here.
// The state API is the one a host should use: it also carries the display
// flag, and its release restores the origin before freeing.
//

dems_container * globe_dems_create() {
	globe_state_origin();
	return new dems_container();
}

void globe_dems_install(dems_container * container) {
	if (container == NULL)
		return;
	globe_state_origin();
	globe_dems = container;
}

dems_container * globe_dems_origin() {
	return globe_state_origin()->dems;
}

void globe_dems_release(dems_container * container) {
	if (container == NULL)
		return;

	// The library's own container is freed with the library, not here.
	if (container == globe_state_origin()->dems)
		return;

	if (globe_dems == container)
		globe_dems = globe_state_origin()->dems;

	release_elements(container->begin(), container->end());
	delete container;
}

}; // namespace surfit
