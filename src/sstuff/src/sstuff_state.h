
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

#ifndef __sstuff_state_included__
#define __sstuff_state_included__

/*! \file
    \brief per-task sstuff context: worker pool, log, file search, RNG

    libsstuff used to keep its working state in file-scope globals: one worker
    pool, one log file, one find_first()/find_next() iteration, one file-save
    mode and the process-wide C RNG.  A second task therefore shared (and could
    corrupt) the first task's pool, log and file search.

    An sstuff_state owns one complete set of those resources.  The project has
    to keep the historical free functions (writelog(), find_first(),
    sstuff_get_threads(), ...) and their globals, because the engine and the
    plugin libraries call them directly; installing a state copies its public
    settings into the globals, and the state that was installed before is copied
    back out first, so nothing is lost while a task is not active.  Resources
    that are not part of the public ABI -- the pool, the log FILE, the file
    search cursor, the RNG -- live only in the state.

    The install/release pair is the same pattern as surfit_state: the core owns
    one sstuff_state per surfit_state and installs it in state_install().  The
    installed state, the library state and the mirrored globals are all
    thread_local, so two tasks in two threads keep their pools, logs, file
    searches, save modes and random streams apart.  Releasing a state clears it
    out of every thread that still has it installed.
*/

#ifndef SSTUFF_EXPORT
// The sstuff sources include "sstuff_ie.h" before this header; a consumer that
// includes it on its own still gets a usable declaration.
#define SSTUFF_EXPORT
#endif

namespace surfit {

//! opaque per-task context (defined in sstuff_state_impl.h, inside libsstuff)
struct sstuff_state;

//! the calling thread's library state, captured on first use; owned by libsstuff
SSTUFF_EXPORT
sstuff_state * sstuff_state_origin();

//! the state installed in the calling thread's globals; never NULL
SSTUFF_EXPORT
sstuff_state * sstuff_state_active();

/*! \brief copies the five public settings and the log hook from \a source

    The settings are inherited by a new context; the resources (pool, log,
    file cursor, RNG) stay with the context that owns them.  Used when a task
    is created from another thread's library state.
*/
SSTUFF_EXPORT
void sstuff_state_copy_settings(sstuff_state * destination,
                                const sstuff_state * source);

/*! \brief copies \a source's mirrored settings into this thread's globals

    Used to bind a thread to the library state without installing it: the worker
    pool count is deliberately not copied, because the pool of the library state
    is the thread's own and a thread that only runs tasks must not start one.
*/
SSTUFF_EXPORT
void sstuff_state_apply_settings(const sstuff_state * source);

/*! \brief writes this thread's mirrored settings into \a state

    A no-op unless \a state is exactly the context installed in this thread, so
    storing one task's snapshot cannot write another task's globals into it.
*/
SSTUFF_EXPORT
void sstuff_state_store(sstuff_state * state);

/*! \brief a new context with a copy of the current settings

    The worker pool is not started until the state is installed, so creating a
    task that is never used costs no threads.  A state starts with no log file
    and an empty file-search cursor; each task opens its own log if it wants one.
*/
SSTUFF_EXPORT
sstuff_state * sstuff_state_create();

/*! \brief makes \a state active, saving the outgoing state's public settings

    Installing NULL installs the library state, so a caller can always
    "return to the defaults" with sstuff_state_install(NULL).
*/
SSTUFF_EXPORT
void sstuff_state_install(sstuff_state * state);

/*! \brief frees a state, its worker pool, log file and file-search cursor

    The origin state belongs to the library and is left alone.  Releasing the
    active state installs the origin first, exactly like state_release().
*/
SSTUFF_EXPORT
void sstuff_state_release(sstuff_state * state);

}; // namespace surfit

#endif
