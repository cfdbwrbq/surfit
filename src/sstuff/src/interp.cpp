
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
#include "interp.h"

#include <string.h>

namespace {

/*! Matches one '[...]' set, following Tcl's rules exactly.

	The rules were read off Tcl itself rather than guessed:

	* a ']' straight after the '[' closes the set, so ``[]]`` is an empty set
	  followed by a literal ']' and matches nothing;
	* a range ``x-y`` matches anything between the two characters in either
	  order, so ``[c-a]`` matches a, b and c;
	* an unterminated set runs to the end of the pattern, so ``[a-c`` matches
	  a, b and c;
	* '!' and '^' are ordinary members, not negations;
	* there is no escaping inside a set either: a backslash is a member like
	  any other, and in ``[a\-c]`` the backslash starts a range with 'c';

	\param candidate the character to test
	\param pattern   points just past the '['
	\param after     receives where the pattern continues: at the closing ']',
	                 or at the end of the pattern when it was never closed
	\return non-zero when the character belongs to the set
*/
int match_set(char candidate, const char * pattern, const char ** after)
{
	const char * cursor = pattern;
	int matched = 0;

	while (*cursor != '\0' && *cursor != ']') {
		char low = *cursor;
		cursor++;

		if (cursor[0] == '-' && cursor[1] != '\0') {
			char high = cursor[1];
			cursor += 2;

			char lo = (low < high) ? low : high;
			char hi = (low < high) ? high : low;
			if (candidate >= lo && candidate <= hi)
				matched = 1;
			continue;
		}

		if (candidate == low)
			matched = 1;
	}

	*after = cursor;
	return matched;
}

}  // namespace

bool StringMatch(const char * match, const char * str)
{
	if (str == NULL)
		str = "";
	if (match == NULL)
		match = "*";

	const char * string = str;
	const char * pattern = match;

	while (*pattern != '\0') {
		if (*pattern == '*') {
			/* A run of '*' matches anything, so try the rest of the
			   pattern at every remaining position. */
			while (*pattern == '*')
				pattern++;
			if (*pattern == '\0')
				return true;
			while (*string != '\0') {
				if (StringMatch(pattern, string))
					return true;
				string++;
			}
			return StringMatch(pattern, string);
		}

		if (*string == '\0')
			return false;

		if (*pattern == '?') {
			pattern++;
			string++;
			continue;
		}

		if (*pattern == '[') {
			const char * after = NULL;
			int matched = match_set(*string, pattern + 1, &after);
			if (!matched)
				return false;
			/* Step past the closing ']' when there is one. */
			pattern = (*after == ']') ? after + 1 : after;
			string++;
			continue;
		}

		if (*pattern == '\\' && pattern[1] != '\0')
			pattern++;

		if (*pattern != *string)
			return false;
		pattern++;
		string++;
	}

	return *string == '\0';
}
