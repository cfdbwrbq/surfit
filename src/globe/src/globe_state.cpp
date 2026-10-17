/*------------------------------------------------------------------------------
 *	DEM containers that belong to a task.
 *
 *	The DEM commands work on whatever container globe_dems points at, so a
 *	host that keeps several tasks alive can give each one its own: the
 *	container is created by the task, installed before its calls and released
 *	with it.  The library keeps one container of its own for the commands that
 *	run outside any task, which is what the Tcl front end and the module-level
 *	Python functions use.
 *
 *	Licensed under the GNU General Public License, version 2, like the rest of
 *	surfit.
 *----------------------------------------------------------------------------*/

#include "globe_ie.h"

#include "dem.h"
#include "free_elements.h"

namespace surfit {

/*! The library's own container, captured before anything is installed.
 *
 *	It is captured lazily, but every path that replaces globe_dems calls this
 *	first, so the pointer is never mistaken for a task's container.
 */
static dems_container * library_dems = NULL;

static dems_container * library_container() {
	if (library_dems == NULL) {
		if (globe_dems == NULL)
			globe_dems = new dems_container();
		library_dems = globe_dems;
	}
	return library_dems;
}

dems_container * globe_dems_create() {
	library_container();
	return new dems_container();
}

void globe_dems_install(dems_container * container) {
	if (container == NULL)
		return;
	library_container();
	globe_dems = container;
}

dems_container * globe_dems_origin() {
	return library_container();
}

void globe_dems_release(dems_container * container) {
	if (container == NULL)
		return;

	// The library's own container is freed with the library, not here.
	if (container == library_container())
		return;

	if (globe_dems == container)
		globe_dems = library_container();

	release_elements(container->begin(), container->end());
	delete container;
}

}; // namespace surfit
