
/*------------------------------------------------------------------------------
 *	$Id$
 *
 *	Copyright (c) 2002-2006 by M. V. Dmitrievsky and V. N. Kutrunov
 *	See COPYING file for copying and redistribution conditions.
 *
 *	  program is free software; you can redistribute it and/or modify
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
#include "threads.h"
#include "sstuff_state_impl.h"

#include <vector>

#ifdef HAVE_THREADS

void job::release() { 
	delete this; 
};

//! live pool size; the installed state carries the matching snapshot
thread_local size_t cpu = 1;

namespace surfit {

/*! \brief resizes the worker pool of \a state to \a cnt slots

    One slot belongs to the calling thread (slot 0); the other cnt-1 are idle
    slaves.  The arithmetic of the historical sstuff_init_threads() is kept,
    including leaving a couple of idle slaves behind when shrinking, because
    that is what the engine has always done and the slots are harmless.
*/
static void pool_resize(sstuff_state * state, size_t cnt) {
	size_t ssize = state->slaves.size();
	if (ssize == cnt) {
		state->jobs.resize(cnt);
		return;
	}
	size_t i;
	if (ssize > cnt) {
		for (i = 0; i < ssize - cnt - 1; i++) {
			slavethread * slave = *(state->slaves.end()-1);
			slave->postquit();
			slave->waitfor();
			state->slaves.erase(state->slaves.end()-1);
			delete slave;
		}
	} else {
		for (i = 0; i < cnt - ssize - 1; i++) {
			slavethread * slave = new slavethread();
			state->slaves.push_back(slave);
			slave->start();
		}
	}
	state->jobs.resize(cnt);
	for (i = 0; i < cnt; i++)
		state->jobs[i] = NULL;
}

void sstuff_pool_ensure(sstuff_state * state) {
	if (state == NULL)
		return;
	pool_resize(state, state->cpu);
}

void sstuff_pool_release(sstuff_state * state) {
	if (state == NULL)
		return;

	// Slaves are constructed as thread(false), so the pool owns them: a ptypes
	// thread must be joined and deleted by its owner.  Autofree (thread(true))
	// cannot be used here -- a self-deleting thread trips ~thread()'s "Attempt
	// to free a working thread" fatal, because nothing has cleared its handle
	// yet, and joining it afterwards is a use-after-free.
	size_t i;
	for (i = 0; i < state->slaves.size(); i++) {
		slavethread * s = state->slaves[i];
		state->slaves[i] = NULL;
		if (s != NULL) {
			s->postquit();
			s->waitfor();
		}
		delete s;
	}
	state->slaves.clear();

	// The job objects belong to their callers (most are static arrays); the
	// slots only ever hold a pointer until do_jobs() consumes it.
	state->jobs.clear();
}

}; // namespace surfit

#endif // HAVE_THREADS

void sstuff_init_threads(size_t cnt) {
#ifdef HAVE_THREADS

	surfit::sstuff_state * state = surfit::sstuff_state_active();

	size_t value = MIN(cnt, MAX_CPU);

#ifdef XXL
	value = 1;
#endif

	// The global is the live value the engine reads through sstuff_get_threads();
	// the state keeps the snapshot that install/release move in and out.
	cpu = value;
	state->cpu = value;
	surfit::sstuff_pool_ensure(state);
#endif //threads
};

size_t sstuff_get_threads() {
#ifdef HAVE_THREADS
	return cpu;
#else
	return 1;
#endif
};

#ifdef HAVE_THREADS
void set_job(job * j, size_t pos) {

	surfit::sstuff_state * state = surfit::sstuff_state_active();
	if (state == NULL || pos >= state->jobs.size())
		return;
	state->jobs[pos] = j;
};

void do_jobs() {

	surfit::sstuff_state * state = surfit::sstuff_state_active();
	if (state == NULL || state->jobs.empty())
		return;

	std::vector<job *> & jobs = state->jobs;

	size_t i;
	unsigned added_slaves = 0;
	for (i = 1; i < jobs.size(); i++) {
		job * j = jobs[i];
		if (j == NULL)
			break;

		slavethread * slave = state->slaves[i-1];
		slave->j = j;
		jobs[i] = NULL;
		slave->post_do_job();
		added_slaves++;
	}

	job * j = jobs[0];
	jobs[0] = NULL;
	if (j)
		j->do_job();

	for (i = 0; i < added_slaves; i++) {
		slavethread * slave = state->slaves[i];
		slave->sem.wait();
	}

};

void slavethread::execute()
{
	msgqueue::run();
}

void slavethread::cleanup()
{
}

void slavethread::msghandler(message& msg)
{
	switch (msg.id)
	{
	case MSG_JOB:
		{
			if (j) {
				j->do_job();
				j = NULL;
			}
			sem.post();
		}
		break;
	default:
		defhandler(msg);
	}
}

void slavethread::postquit()
{ 
	msgqueue::post(MSG_QUIT); 
}

inline void slavethread::post_do_job()
{  
	msgqueue::post(new jobmessage());
}
#endif // HAVE_THREADS
