
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

#ifndef __surfit_f_cntr_included__
#define __surfit_f_cntr_included__

#include "functional.h"
#include "f_points.h"

#include <set>

namespace surfit {

struct cell_record
{
	cell_record() : sum_value(0), cnt(0) {};
	REAL sum_value;
	size_t cnt;
};

class d_points;
class f_points;
class d_cntr;
class bitvec;
class vec;
class sizetvec;

/*! \class f_cntr
    \brief functional for approximating contour
*/
class SURFIT_EXPORT f_cntr : public f_points_user {
public:
	//! constructor
	f_cntr(const d_cntr * icontour);
	//! destructor
	~f_cntr();

	d_points * get_points();
	
protected:

	int this_get_data_count() const;
	const data * this_get_data(int pos) const;

	//! contour for approximation
	const d_cntr * contour;
};

struct sect
{
	//! distance to neighbour cell
	REAL d; 
	
	//! desired value
	REAL z; 
	
	//! lower cell number
	size_t pos1;

	//! higher cell number
	size_t pos2;

};

class SURFIT_EXPORT f_cntr2 : public functional {
public:
	//! constructor
	f_cntr2(bool iflag, REAL imult = 1);
	//! destructor
	~f_cntr2();

	const char * getManagerName() const { return "surfit"; };

	bool minimize();
	bool make_matrix_and_vector(matr *& matrix, extvec *& v, bitvec * mask_solved, bitvec * mask_undefined);
	void mark_solved_and_undefined(bitvec * mask_solved, 
				       bitvec * mask_undefined,
				       bool i_am_cond);
	
	bool solvable_without_cond(const bitvec * mask_solved, 
				   const bitvec * mask_undefined,
				   const extvec * X);

	virtual void cleanup();

	void add_contour(const d_cntr * cntr);
	bool get_flag() const;
	
protected:

	int this_get_data_count() const;
	const data * this_get_data(int pos) const;

	//! contour for approximation
	std::vector<const d_cntr *> * contours;

private:
	void calc_sects(bitvec * mask_solved, bitvec * mask_undefined);
	d_grid * sects_grid;
	std::vector<sect> * sects;
	REAL mult;
	bool flag;

	std::set<size_t, cell_record> recs;

};

}; // namespace surfit

#endif

