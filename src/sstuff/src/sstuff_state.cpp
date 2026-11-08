
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

#include <mutex>
#include <vector>

namespace surfit {

/*! Public settings, in one list.
 *
 *	These five are the variables other libraries read and write directly, so
 *	they stay globals and remain the live values the engine uses.  A state
 *	stores a snapshot of them; install/release copy between the two.  The list
 *	is shared by both directions so a field cannot be forgotten in one and
 *	remembered in the other.  The globals are thread_local, together with the
 *	installed state: each thread swaps its own copy.
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

//! state whose settings are in this thread's globals right now
static thread_local sstuff_state * active_state = NULL;

//! this thread's library state, created on first use
static thread_local sstuff_state * origin_state = NULL;

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

namespace {

/*
 * Releasing a context must clear it out of the other threads that installed it.
 * The active pointer is thread_local, so each thread registers the address of
 * its slot; the tables are leaked on purpose, because a worker thread can exit
 * during static destruction.
 */
std::mutex & active_slot_mutex() {
	static std::mutex * mutex = new std::mutex;
	return *mutex;
}

std::vector<sstuff_state **> & active_slots() {
	static std::vector<sstuff_state **> * slots =
		new std::vector<sstuff_state **>;
	return *slots;
}

struct active_slot_guard {
	~active_slot_guard() {
		std::lock_guard<std::mutex> lock(active_slot_mutex());
		std::vector<sstuff_state **> & slots = active_slots();
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
	static thread_local active_slot_guard guard;
	(void)guard;
	std::lock_guard<std::mutex> lock(active_slot_mutex());
	active_slots().push_back(&active_state);
	active_slot_registered = true;
}

void clear_active_slots(sstuff_state * state) {
	std::lock_guard<std::mutex> lock(active_slot_mutex());
	std::vector<sstuff_state **> & slots = active_slots();
	for (size_t i = 0; i < slots.size(); i++) {
		if (*slots[i] == state)
			*slots[i] = NULL;
	}
}

} // anonymous namespace

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
		ensure_active_slot_registered();
		if (active_state == NULL)
			active_state = origin_state;
	}
	return origin_state;
}

sstuff_state * sstuff_state_active() {
	if (active_state == NULL) {
		// First use in this thread, or the installed state was released by
		// another thread.  Bind the library state without reading the stale
		// globals that may still point at the released task.
		sstuff_state * origin = sstuff_state_origin();
		state_to_globals(origin);
		active_state = origin;
	}
	return active_state;
}

void sstuff_state_copy_settings(sstuff_state * destination,
                                const sstuff_state * source) {
	if (destination == NULL || source == NULL)
		return;
	destination->cpu = source->cpu;
	destination->loglevel = source->loglevel;
	destination->stop_on_error = source->stop_on_error;
	destination->fileio_append = source->fileio_append;
	destination->datafile_modE = source->datafile_modE;
	destination->log_hook = source->log_hook;
}

void sstuff_state_apply_settings(const sstuff_state * source) {
	if (source == NULL)
		return;
	loglevel = source->loglevel;
	stop_on_error = source->stop_on_error;
	fileio_append = source->fileio_append;
	datafile_modE = source->datafile_modE;
}

void sstuff_state_store(sstuff_state * state) {
	if (state == NULL || state != active_state)
		return;
	globals_to_state(state);
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
	sstuff_state_copy_settings(state, origin);

	return state;
}

void sstuff_state_install(sstuff_state * state) {
	if (state == NULL)
		state = sstuff_state_origin();

	ensure_active_slot_registered();
	if (active_state == NULL) {
		// First use in this thread, or the installed state was released by
		// another thread.  Bind the library state; the globals may point at the
		// released task, so they are overwritten, never read back.
		sstuff_state * origin = sstuff_state_origin();
		state_to_globals(origin);
		active_state = origin;
	}

	// The globals are the live values, so keep the installed state's snapshot
	// current even when it is already installed; a context built in one thread
	// is then installed in another with the settings the build left behind.
	globals_to_state(active_state);

	if (active_state == state) {
		sstuff_pool_ensure(state);
		return;
	}

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

	bool was_active_here = (active_state == state);
	clear_active_slots(state);
	if (was_active_here)
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
