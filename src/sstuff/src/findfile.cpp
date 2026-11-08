
/*------------------------------------------------------------------------------
 *	$Id: fileio.cpp 934 2007-01-28 16:59:19Z mishadm $
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
#include "findfile.h"
#include "fileio.h"
#include "interp.h"
#include "sstuff_state_impl.h"

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)
#include <io.h>
#else
#include <dirent.h>
#endif

#include <string.h>
#include <stdlib.h>

namespace surfit {

/*! \brief the active task's file-search cursor

    find_first()/find_next()/find_close() used to keep the pattern, the result
    buffer, the platform directory handle and the current entry in process
    globals, so one task's file load could rewind another task's iteration.
    They live in the installed sstuff_state now; the returned path points into
    that state's buffer, exactly as it pointed into the old global one.
*/
static sstuff_state * find_state() {
	return sstuff_state_active();
};

const char * make_find_res(const char * str)
{
	sstuff_state * state = find_state();
	strncpy(state->find_res + state->path_pos, str, strlen(str));
	state->find_res[state->path_pos + strlen(str)] = '\0';
	return state->find_res;
};

#if defined(_WIN32) || defined(__WIN32__) || defined(WIN32)

const char * find_first(const char * pattern)
{
	sstuff_state * state = find_state();

	state->file_handle = _findfirst(pattern, &state->ff);
	if (state->file_handle == -1) {
		writelog(LOG_ERROR,"%s",strerror(errno));
		return NULL;
	}
	state->find_pattern = strdup(pattern);

	int path_pos1 = 0;
	if ( strrchr(state->find_pattern+path_pos1, '/') != NULL )
		path_pos1 = strrchr(state->find_pattern+path_pos1, '/') - state->find_pattern + 1;

	int path_pos2 = 0;
	if ( strrchr(state->find_pattern+path_pos2, '\\') != NULL )
		path_pos2 = strrchr(state->find_pattern+path_pos2, '\\') - state->find_pattern + 1;

	state->path_pos = MAX(path_pos1, path_pos2);
	strncpy(state->find_res, state->find_pattern, state->path_pos);

	if (state->ff.attrib &= _A_SUBDIR)
		return find_next();
	return make_find_res(state->ff.name);
};

const char * find_next()
{
	sstuff_state * state = find_state();
	if (state->file_handle == -1)
		return NULL;

	int res = _findnext(state->file_handle, &state->ff);
	if (res == 0) {
		if (state->ff.attrib &= _A_SUBDIR)
			return find_next();
		return make_find_res(state->ff.name);
	}
	return NULL;
};

void find_close()
{
	sstuff_state * state = find_state();
	free(state->find_pattern);
	state->find_pattern = NULL;
	if (state->file_handle != -1) {
		_findclose(state->file_handle);
		state->file_handle = -1;
	}
};

#else

bool wildcmp(const char *wild, const char *string) {
	return StringMatch( wild, string);
};

const char * find_first(const char * pattern)
{
	sstuff_state * state = find_state();

	state->find_pattern = strdup(pattern);

	int path_pos1 = 0;
	if ( strrchr(state->find_pattern+path_pos1, '/') != NULL )
		path_pos1 = strrchr(state->find_pattern+path_pos1, '/') - state->find_pattern + 1;

	int path_pos2 = 0;
	if ( strrchr(state->find_pattern+path_pos2, '\\') != NULL )
		path_pos2 = strrchr(state->find_pattern+path_pos2, '\\') - state->find_pattern + 1;

	state->path_pos = MAX(path_pos1, path_pos2);
	if (state->path_pos != 0) {
		strncpy(state->find_res, state->find_pattern, state->path_pos);
		state->find_res[state->path_pos] = '\0';
	} else {
		state->find_res[0]='.';
		state->find_res[1]='\0';
	}

	if ((state->dp = opendir(state->find_res)) == NULL)
	{
		free(state->find_pattern);
		state->find_pattern = NULL;
		return NULL;
	}

	return find_next();
};

const char * find_next()
{
	sstuff_state * state = find_state();
	if (state->dp == NULL)
		return NULL;

	state->entry = readdir(state->dp);
	if (state->entry == NULL)
		return NULL;
	else {
		const char * name = make_find_res(state->entry->d_name);
		if ( wildcmp(state->find_pattern, name) ) {
			return name;
		} else
			return find_next();
	}
};

void find_close()
{
	sstuff_state * state = find_state();
	if (state->dp) {
		closedir(state->dp);
		state->dp = NULL;
	}
	state->entry = NULL;
	free(state->find_pattern);
	state->find_pattern = NULL;
};

#endif

}; // namespace surfit
