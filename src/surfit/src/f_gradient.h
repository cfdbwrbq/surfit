#ifndef __surfit_f_gradient_included__
#define __surfit_f_gradient_included__

#include "functional.h"

namespace surfit {

class d_points;
class matr;
class extvec;
class bitvec;

/*! Local derivative constraint from points with dZ/dx and dZ/dy. */
class SURFIT_EXPORT f_gradient : public functional {
public:
	f_gradient(const d_points * ipnts, REAL iweight = 1.0);
	~f_gradient();

	const char * getManagerName() const { return "surfit"; };
	bool minimize();
	bool make_matrix_and_vector(matr *& matrix, extvec *& v,
	                            bitvec * mask_solved,
	                            bitvec * mask_undefined);
	void mark_solved_and_undefined(bitvec * mask_solved,
	                               bitvec * mask_undefined,
	                               bool i_am_cond);
	bool solvable_without_cond(const bitvec * mask_solved,
	                           const bitvec * mask_undefined,
	                           const extvec * X);

protected:
	int this_get_data_count() const;
	const data * this_get_data(int pos) const;

private:
	const d_points * pnts;
	REAL weight;
};

}; // namespace surfit

#endif
