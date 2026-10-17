
/*------------------------------------------------------------------------------
 *	$Id$
 *
 *	Copyright (c) 2002-2006 by M. V. Dmitrievsky
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

#include "surfit_io_ie.h"

#include "cntr.h"
#include "cntr_io.h"
#include "boolvec.h"
#include "findfile.h"

#include "interp.h"
#include <algorithm>
#include <vector>
#include <errno.h>

namespace surfit {

boolvec * cntr_load_bln(const char * filename, const char * cntrname) 
{
	if (cntrname != NULL) {

		const char * fname = find_first(filename);
		boolvec * res = create_boolvec();

		while (fname) {
			FILE * file = fopen(fname, "r");
			if (!file) {
				writelog(LOG_WARNING, "The file %s was not opened: %s",filename,strerror( errno ));
				res->push_back(false);
				fname = find_next();
				continue;
			}
			if (ferror(file) != 0) {
				writelog(LOG_WARNING, "loading from BLN: file error.");
				fclose(file);
				res->push_back(false);
				fname = find_next();
				continue;
			}
			
			int orient = 1;
			d_cntr * crv = _cntr_load_bln(file, orient);
			while (crv != NULL) {

				if ( StringMatch(cntrname, crv->getName()) == false ) {
					crv->release();
					crv = _cntr_load_bln(file, orient);
					continue;
				}

				writelog(LOG_MESSAGE,"loading contour \"%s\" from Surfer BLN file %s", crv->getName(), filename);

				surfit_cntrs->push_back(crv);
				crv = _cntr_load_bln(file, orient);
				continue;
			}

			fclose(file);
			res->push_back(true);
			fname = find_next();
		}

		find_close();
		return res;
	}

	boolvec * res = create_boolvec();
	const char * fname = find_first(filename);

	while (fname) {

		writelog(LOG_MESSAGE,"loading contours from BLN file %s", fname);

		FILE * file = fopen(fname, "r");
		if (!file) {
			writelog(LOG_WARNING, "The file %s was not opened: %s",filename,strerror( errno ));
			res->push_back(false);
			fname = find_next();
			continue;
		}
		if (ferror(file) != 0) {
			writelog(LOG_WARNING, "loading from BLN: file error.");
			fclose(file);
			res->push_back(false);
			fname = find_next();
			continue;
		}

		int orient = 1;
		d_cntr * crv = _cntr_load_bln(file, orient);
		while (crv != NULL) {
			surfit_cntrs->push_back(crv);
			crv = _cntr_load_bln(file, orient);
		}

		fclose(file);
		res->push_back(true);
		fname = find_next();

	}

	find_close();
	return res;
};

boolvec * cntr_load_shp(const char * filename, const char * cntrname, const char * zfield) 
{
	boolvec * res = create_boolvec();
	const char * fname = find_first(filename);
	while (fname)
	{
		res->push_back( _cntr_load_shp(fname, cntrname, zfield) );
		fname = find_next();
	}
	
	find_close();
	return res;
};

boolvec * cntr_save_shp(const char * filename, const char * cntr_pos) {
	// The shape type belongs to the file, not to one contour: a flat contour
	// must not create an ARC file that the next, varying-Z contour cannot join.
	// Decide the type over the whole match first, then write every contour
	// with that type.  Without this, a set that mixes a flat contour with a 3D
	// one fails halfway and leaves a partial file.
	std::vector<d_cntr *> matched;
	bool use_arcz = false;
	size_t i;
	for (i = 0; i < surfit_cntrs->size(); i++) {
		d_cntr * cntr = (*surfit_cntrs)[i];
		if (!cntr || !cntr->getName())
			continue;
		if (StringMatch(cntr_pos, cntr->getName()) == false)
			continue;
		matched.push_back(cntr);
		REAL minz, maxz;
		cntr->getMinMaxZ(minz, maxz);
		if (maxz != minz)
			use_arcz = true;
	}

	if (matched.empty())
		return NULL;

	boolvec * res = create_boolvec();
	for (i = 0; i < matched.size(); i++)
		res->push_back(_cntr_save_shp_as(matched[i], filename, use_arcz));
	return res;
};

struct match_cntr_save_bln
{
	match_cntr_save_bln(const char * ifilename, const char * icntr_pos, FILE * ifile)
	{
		filename = ifilename;
		cntr_pos = icntr_pos;
		res = NULL;
		file = ifile;
	}

	void operator()(d_cntr * crv)
	{
		if (res == NULL)
			res = create_boolvec();

		if ( StringMatch(cntr_pos, crv->getName()) )
		{
			writelog(LOG_MESSAGE,"saving contour \"%s\" to Surfer BLN file %s",
				 crv->getName(), filename);
			res->push_back( _cntr_save_bln(crv, file, 1) );
		}
	};

	const char * filename;
	const char * cntr_pos;
	boolvec * res;
	FILE * file;
};

boolvec * cntr_save_bln(const char * filename, const char * cntr_pos) 
{
	FILE * file = fopen(filename, "a");
	if (!file) {
		writelog(LOG_ERROR, "The file %s was not opened: %s",filename,strerror( errno ));
		return NULL;
	}
	if (ferror(file) != 0) {
		writelog(LOG_ERROR, "saving BLN: file error.");
		fclose(file);
		return NULL;
	}

	match_cntr_save_bln saver(filename, cntr_pos, file);
	saver = std::for_each(surfit_cntrs->begin(), surfit_cntrs->end(), saver);

	fclose(file);

	return saver.res;
};

}; // namespace surfit;


