
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

#ifndef __sstuff_interp_included__
#define __sstuff_interp_included__

/*! \file
    \brief string matching used to select objects by name

    The engine used to call Tcl_StringMatch() here, which was the last thing
    tying the core to Tcl.  The matching rules are Tcl's, implemented locally;
    see StringMatch() for the details.
*/

//! Compares two strings, where the first is a string mask
SSTUFF_EXPORT
bool StringMatch(const char * match, const char * str);

#endif

