#ifndef __surfit_f_slope_included__
#define __surfit_f_slope_included__
#include "functional.h"
namespace surfit {
class d_area;
class d_mask;
class matr;
class extvec;
class bitvec;
/*! Local slope/curvature bound applied as a final projection. */
class SURFIT_EXPORT f_slope : public functional {
public:
	f_slope(REAL ilimit, const d_area * iarea, const d_mask * imask,
	        bool iinside, int imode, REAL imult);
	~f_slope();
	const char * getManagerName() const { return "surfit"; };
	bool minimize();
	bool make_matrix_and_vector(matr *& matrix, extvec *& v,
	                            bitvec * mask_solved, bitvec * mask_undefined);
	void mark_solved_and_undefined(bitvec * mask_solved,
	                               bitvec * mask_undefined, bool i_am_cond);
	bool solvable_without_cond(const bitvec * mask_solved,
	                           const bitvec * mask_undefined, const extvec * X);
	bool base_first() const { return true; };
protected:
	int this_get_data_count() const;
	const data * this_get_data(int pos) const;
private:
	bool build_projection(matr *& matrix, extvec *& v);
	REAL limit;
	const d_area * area;
	const d_mask * mask;
	bool inside;
	int mode;
	REAL mult;
};
}; // namespace surfit
#endif
