
/*------------------------------------------------------------------------------
 *	One task's state of the globe plugin.
 *
 *	The DEM commands read the container in \ref globe_dems and the display flag
 *	in \ref draw_dem; both are process globals, so they can hold one task's
 *	values at a time.  A host that keeps several tasks alive gives each one a
 *	globe_state: create one with the task, install it before the task's calls,
 *	and release it with the task.  The library keeps its own origin state for
 *	the calls that run outside a task, which is what the Tcl front end and the
 *	module-level Python functions use.
 *
 *	Licensed under the GNU General Public License, version 2, like the rest of
 *	surfit.
 *----------------------------------------------------------------------------*/

#ifndef __globe__globe_state__
#define __globe__globe_state__

#include "globe_ie.h"

namespace surfit {

class dems_container;

/*! \struct globe_state
    \brief opaque per-task state: the DEM container and the display flag

	Only one state is installed at a time; the globals \ref globe_dems and
	\ref draw_dem hold the installed state's values, exactly as the engine's
	surfit_state holds the task's globals.  Installing copies the state in and
	saving the outgoing state's values first, so an interleaved task loses
	nothing.

	The state owns its DEM container, including the DEMs in it.  The host must
	release the state after the gridding rules that point at those DEMs: a DEM
	rule borrows the raster, so freeing the rasters first would leave the rule
	with a dangling pointer.  \ref globe_state_origin() owns the library's
	container instead and is never freed by \ref globe_state_release().

	The container pointer and the display flag are thread_local, together with
	the installed state, so each thread installs the task it is working on and
	two tasks can be used from two threads at the same time.  Releasing a state
	clears it out of every thread that still had it installed, so the next call
	in that thread starts from the library's own container again.
*/
struct globe_state;

//! the library's own state, captured on first use and never freed by release()
GLOBE_EXPORT globe_state * globe_state_origin();

//! the state currently installed in the globals
GLOBE_EXPORT globe_state * globe_state_active();

//! a new state with an empty DEM container and the current display setting
GLOBE_EXPORT globe_state * globe_state_create();

//! makes \a state the installed one, saving the outgoing state's values first
GLOBE_EXPORT void globe_state_install(globe_state * state);

/*! frees a state made by globe_state_create() and the DEMs it holds
 *
 *	Releasing the installed state restores the origin first, so the globals
 *	never point at a freed container.  Releasing the origin is a no-op.
 */
GLOBE_EXPORT void globe_state_release(globe_state * state);

//! the DEM container of \a state, or NULL
GLOBE_EXPORT dems_container * globe_state_dems(globe_state * state);

//! whether _dem_show() draws the solid DEM for \a state
GLOBE_EXPORT int globe_state_get_draw_dem(globe_state * state);

//! sets the display flag of \a state; the installed globals follow it
GLOBE_EXPORT void globe_state_set_draw_dem(globe_state * state, int draw_dem);

}; // namespace surfit

#endif
