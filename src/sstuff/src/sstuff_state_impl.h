
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

#ifndef __sstuff_state_impl_included__
#define __sstuff_state_impl_included__

/*! \file
    \brief definition of sstuff_state, private to libsstuff

    The state structure is hidden from the rest of the build (the public
    header only forward-declares it), so the resources below can change without
    an ABI change outside libsstuff.
*/

#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <vector>

#include "sstuff_state.h"
#include "fileio.h"

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
#include <io.h>
#else
#include <dirent.h>
#endif

// The thread API in threads.h lives in the global namespace (it predates the
// surfit namespace convention), so these forward declarations do too.
struct job;
class slavethread;

namespace surfit {

//! a fresh seed for a per-task RNG stream
unsigned long long sstuff_random_seed();

//! makes the pool of \a state match its cpu count; cheap when already matching
void sstuff_pool_ensure(sstuff_state * state);

//! joins and deletes the worker threads of \a state
void sstuff_pool_release(sstuff_state * state);

/*! \brief resources that belong to one task

    The five public settings -- cpu, loglevel, stop_on_error, fileio_append and
    datafile_modE -- are mirrored by process globals, because other libraries
    read and write them directly.  install/release copy them in and out; the
    list is in sstuff_state.cpp.  Everything else is used only through the state
    accessor, so it needs no global.
*/
struct sstuff_state {
	//! number of worker slots, including the calling thread
	size_t cpu;

	//! idle workers: cpu-1 of them once the pool is running
	std::vector<slavethread *> slaves;

	//! one job slot per worker, consumed by do_jobs()
	std::vector<job *> jobs;

	//! log verbosity, mirrored by the loglevel global
	int loglevel;

	//! whether a LOG_ERROR is fatal, mirrored by the stop_on_error global
	int stop_on_error;

	//! text writers append or rewrite, mirrored by the fileio_append global
	bool fileio_append;

	//! task log file, NULL when log_open() was not called
	FILE * logfile;

	//! name of the log file, owned (strdup'ed by log_open())
	char * logfilename;

	//! observer installed by set_log_hook()
	log_hook_type log_hook;

	//! file-search cursor: pattern being iterated, owned
	char * find_pattern;

	//! how many leading bytes of find_pattern are the directory prefix
	int path_pos;

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
	//! buffer for the path returned by find_first()/find_next()
	char find_res[_MAX_PATH];
	//! windows find handle and data
	long file_handle;
	_finddata_t ff;
#else
	//! buffer for the path returned by find_first()/find_next()
	char find_res[512];
	//! dirent cursor, NULL between find_close() calls
	DIR * dp;
	struct dirent * entry;
#endif

	//! file-save mode: 1 - create new file, 0 - append
	int datafile_modE;

	//! xorshift64* state of the task's random stream
	unsigned long long rng_state;

	//! all fields initialized to the library defaults
	sstuff_state();

	//! joins the pool and closes the log; safe on a partially used state
	~sstuff_state();
};

}; // namespace surfit

#endif
