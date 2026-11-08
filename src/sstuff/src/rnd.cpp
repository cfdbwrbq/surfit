
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
#include "rnd.h"
#include "sstuff_state_impl.h"

#include <math.h>
#include <time.h>
#include <atomic>

namespace surfit {

#define MAGIC_NUMBER 30
#define STD 0.0526971

/*! \brief a fresh seed for one task's random stream

    The engine used to call srand(time(NULL)) once and take numbers from the
    process-wide C RNG, so two interleaved tasks drew from one stream and the
    noise on a surface depended on what another task did.  Each sstuff_state now
    owns the stream.  A task's stream is seeded from the clock and a process
    counter, which keeps the "random" behavior of randomize() while making two
    tasks independent from each other (and reproducible for a single task until
    randomize() is called again).
*/
unsigned long long sstuff_random_seed() {
	static std::atomic<unsigned long long> counter(0);
	unsigned long long step = counter.fetch_add(1) + 1;
	unsigned long long seed = (unsigned long long)time(NULL);
	seed ^= step * 0x9E3779B97F4A7C15ULL;
	seed ^= (unsigned long long)(size_t)&counter;

	// splitmix64 finalizer: one clock tick still gives well-spread states
	seed = (seed ^ (seed >> 30)) * 0xBF58476D1CE4E5B9ULL;
	seed = (seed ^ (seed >> 27)) * 0x94D049BB133111EBULL;
	seed ^= seed >> 31;

	// xorshift64* is stuck at zero, so a zero seed is never used
	if (seed == 0)
		seed = 0x9E3779B97F4A7C15ULL;
	return seed;
};

//! one xorshift64* step; returns 64 random bits
static unsigned long long rng_next(sstuff_state * state) {
	unsigned long long x = state->rng_state;
	x ^= x >> 12;
	x ^= x << 25;
	x ^= x >> 27;
	state->rng_state = x;
	return x * 0x2545F4914F6CDD1DULL;
};

void randomize() {
	sstuff_state_active()->rng_state = sstuff_random_seed();
};

REAL norm_rand(REAL std) {
	sstuff_state * state = sstuff_state_active();
	REAL res = REAL(0);
	int i;
	for (i = 0; i < MAGIC_NUMBER; i++) {
		// >> 33 keeps the value in [0, RAND_MAX], the range rand() returned
		res += REAL(rng_next(state) >> 33) / REAL(RAND_MAX);
	}
	return REAL((std/STD)*(res/REAL(MAGIC_NUMBER)-REAL(0.5)));
};

}; // namespace surfit
