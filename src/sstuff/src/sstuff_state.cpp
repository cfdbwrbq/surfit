
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

#include "sstuff_ie.h"
#include "sstuff_state_impl.h"

#include "fileio.h"
#include "datafile.h"
#include "threads.h"

#include <string.h>

namespace surfit {

/*! Public settings, in one list.
 *
 *	These five are the variables other libraries read and write directly, so
 *	they stay globals and remain the live values the engine uses.  A state
 *	stores a snapshot of them; install/release copy between the two.  The list
 *	is shared by both directions so a field cannot be forgotten in one and
 *	remembered in the other.
 */
#ifdef HAVE_THREADS
#define SSTUFF_STATE_CPU(X) X(size_t, cpu, cpu)
#else
#define SSTUFF_STATE_CPU(X)
#endif

#define SSTUFF_STATE_FIELDS(X)                                          \
	SSTUFF_STATE_CPU(X)                                                 \
	X(int, loglevel, loglevel)                                          \
	X(int, stop_on_error, stop_on_error)                                \
	X(bool, fileio_append, fileio_append)                               \
	X(int, datafile_modE, datafile_modE)

//! state whose settings are in the globals right now
static sstuff_state * active_state = NULL;

//! the library's own state, created on first use
static sstuff_state * origin_state = NULL;

static void globals_to_state(sstuff_state * state) {
#define SSTUFF_STATE_OUT(type, field, global) state->field = global;
	SSTUFF_STATE_FIELDS(SSTUFF_STATE_OUT)
#undef SSTUFF_STATE_OUT
}

static void state_to_globals(const sstuff_state * state) {
#define SSTUFF_STATE_IN(type, field, global) global = state->field;
	SSTUFF_STATE_FIELDS(SSTUFF_STATE_IN)
#undef SSTUFF_STATE_IN
}

//! closes and frees everything a state owns, except the state itself
static void state_free_resources(sstuff_state * state) {
	sstuff_pool_release(state);

	if (state->logfile) {
		fclose(state->logfile);
		state->logfile = NULL;
	}
	if (state->logfilename) {
		free(state->logfilename);
		state->logfilename = NULL;
	}
	if (state->find_pattern) {
		free(state->find_pattern);
		state->find_pattern = NULL;
	}

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
	if (state->file_handle != -1) {
		_findclose(state->file_handle);
		state->file_handle = -1;
	}
#else
	if (state->dp) {
		closedir(state->dp);
		state->dp = NULL;
	}
	state->entry = NULL;
#endif
}

sstuff_state::sstuff_state() {
	cpu = 1;
	loglevel = LOG_MESSAGE;
	stop_on_error = 1;
	fileio_append = false;
	datafile_modE = 1;

	logfile = NULL;
	logfilename = NULL;
	log_hook = NULL;

	find_pattern = NULL;
	path_pos = 0;
	find_res[0] = '\0';

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
	file_handle = -1;
	memset(&ff, 0, sizeof(ff));
#else
	dp = NULL;
	entry = NULL;
#endif

	rng_state = sstuff_random_seed();
}

sstuff_state::~sstuff_state() {
	state_free_resources(this);
}

sstuff_state * sstuff_state_origin() {
	if (origin_state == NULL) {
		origin_state = new sstuff_state();
		globals_to_state(origin_state);
		if (active_state == NULL)
			active_state = origin_state;
	}
	return origin_state;
}

sstuff_state * sstuff_state_active() {
	if (active_state == NULL)
		sstuff_state_origin();
	return active_state;
}

sstuff_state * sstuff_state_create() {
	sstuff_state * origin = sstuff_state_origin();

	// The origin holds the library defaults, but while it is active the globals
	// are where the settings actually live.  Sync it so a new task starts from
	// the settings in force, not from the values the origin was created with.
	if (active_state == origin)
		globals_to_state(origin);

	sstuff_state * state = new sstuff_state();

	// Settings are inherited; resources are not.  A task opens its own log and
	// starts its own worker pool, so two tasks cannot share either one.
	state->cpu = origin->cpu;
	state->loglevel = origin->loglevel;
	state->stop_on_error = origin->stop_on_error;
	state->fileio_append = origin->fileio_append;
	state->datafile_modE = origin->datafile_modE;
	state->log_hook = origin->log_hook;

	return state;
}

void sstuff_state_install(sstuff_state * state) {
	if (state == NULL)
		state = sstuff_state_origin();

	if (active_state == NULL)
		sstuff_state_origin();

	if (active_state == state) {
		sstuff_pool_ensure(state);
		return;
	}

	// The free functions write straight into the globals, so the outgoing state
	// has to be read back out before it is replaced.
	globals_to_state(active_state);
	state_to_globals(state);

	// The pool follows the installed cpu count; this is cheap when it already
	// matches, and starts the threads of a state that was never installed.
	sstuff_pool_ensure(state);

	active_state = state;
}

void sstuff_state_release(sstuff_state * state) {
	if (state == NULL)
		return;

	// The origin belongs to the library and is cleaned up with it.
	if (origin_state != NULL && state == origin_state)
		return;

	if (active_state == state)
		sstuff_state_install(sstuff_state_origin());

	delete state;
}

namespace {

/*! \brief closes the library state's resources at exit

    Static destruction releases the origin's log file, file-search cursor and
    worker threads, which is what the old fileio/threads garbage objects did.
    The sstuff_state object itself is left allocated: the core's origin state
    may still point at it, and the order of static destructors across the two
    libraries is not ours to rely on.
*/
struct sstuff_origin_garbage {
	~sstuff_origin_garbage() {
		if (origin_state == NULL)
			return;
		if (active_state == origin_state)
			active_state = NULL;
		state_free_resources(origin_state);
	}
};

sstuff_origin_garbage garb_origin;

}; // anonymous namespace

}; // namespace surfit
