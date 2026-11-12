#include "surfit_ie.h"

#include "f_gradient.h"
#include "points.h"
#include "matr.h"
#include "vec.h"
#include "bitvec.h"
#include "grid_user.h"
#include "variables_tcl.h"

#include <algorithm>
#include <vector>

namespace surfit {

class matr_gradient : public matr {
public:
	explicit matr_gradient(size_t size) : n(size), row_cols(size), row_vals(size) {};
	~matr_gradient() {};

	REAL element_at(size_t i, size_t j, size_t * next_j = NULL) const {
		for (size_t k = 0; k < row_cols[i].size(); k++) {
			if (row_cols[i][k] == j) {
				if (next_j) *next_j = j + 1;
				return row_vals[i][k];
			}
			if (next_j) *next_j = row_cols[i][k];
		}
		if (next_j) *next_j = n;
		return 0;
	};

	REAL at(size_t i, size_t j, size_t * next_j = NULL) const {
		return element_at(i, j, next_j);
	};

	size_t cols_count() const { return n; };
	size_t rows() const { return n; };
	size_t cols() const { return n; };

	REAL mult_line(size_t J, extvec::const_iterator b_begin,
	               extvec::const_iterator b_end) {
		REAL sum = 0;
		for (size_t k = 0; k < row_cols[J].size(); k++)
			sum += row_vals[J][k] * (*(b_begin + row_cols[J][k]));
		return sum;
	};

	REAL norm() const {
		REAL result = 0;
		for (size_t i = 0; i < n; i++) {
			REAL row = 0;
			for (size_t k = 0; k < row_vals[i].size(); k++)
				row += fabs(row_vals[i][k]);
			result = std::max(result, row);
		}
		return result;
	};

	void add(size_t row, size_t col, REAL value) {
		for (size_t k = 0; k < row_cols[row].size(); k++) {
			if (row_cols[row][k] == col) {
				row_vals[row][k] += value;
				return;
			}
		}
		row_cols[row].push_back(col);
		row_vals[row].push_back(value);
	};

private:
	size_t n;
	std::vector<std::vector<size_t> > row_cols;
	std::vector<std::vector<REAL> > row_vals;
};

f_gradient::f_gradient(const d_points * ipnts, REAL iweight) :
functional("f_gradient", F_CONDITION)
{
	pnts = ipnts;
	weight = iweight;
};

f_gradient::~f_gradient() {};

int f_gradient::this_get_data_count() const { return 1; };

const data * f_gradient::this_get_data(int pos) const {
	return pos == 0 ? pnts : NULL;
};

bool f_gradient::minimize() { return false; };

static void add_equation(matr_gradient * matrix, extvec * v,
                         std::vector<size_t> & index,
                         std::vector<REAL> & coeff,
                         REAL target, REAL weight) {
	for (size_t a = 0; a < index.size(); a++) {
		(*v)(index[a]) += weight * coeff[a] * target;
		for (size_t b = 0; b < index.size(); b++)
			matrix->add(index[a], index[b],
			            weight * coeff[a] * coeff[b]);
	}
};

bool f_gradient::make_matrix_and_vector(matr *& matrix, extvec *& v,
                                        bitvec * mask_solved,
                                        bitvec * mask_undefined) {
	size_t n = method_basis_cntX * method_basis_cntY;
	matr_gradient * result = new matr_gradient(n);
	v = create_extvec(n);
	if (pnts == NULL || pnts->GX == NULL || pnts->GY == NULL) {
		delete result;
		v->release();
		matrix = NULL;
		v = NULL;
		return false;
	}
	size_t nx = method_grid->getCountX();
	REAL dx = method_grid->stepX;
	REAL dy = method_grid->stepY;
	for (size_t p = 0; p < pnts->size(); p++) {
		size_t i = method_grid->get_i((*pnts->X)(p));
		size_t j = method_grid->get_j((*pnts->Y)(p));
		if (i >= nx || j >= method_grid->getCountY())
			continue;
		size_t center = i + j * nx;
		if (mask_solved->get(center) || mask_undefined->get(center))
			continue;
		REAL local_weight = weight;
		if (pnts->W && p < pnts->W->size())
			local_weight *= (*pnts->W)(p);
		std::vector<size_t> index;
		std::vector<REAL> coeff;
		if (i == 0) {
			index.push_back(center); coeff.push_back(-1.0 / dx);
			index.push_back(center + 1); coeff.push_back(1.0 / dx);
		} else if (i + 1 >= nx) {
			index.push_back(center - 1); coeff.push_back(-1.0 / dx);
			index.push_back(center); coeff.push_back(1.0 / dx);
		} else {
			index.push_back(center - 1); coeff.push_back(-0.5 / dx);
			index.push_back(center + 1); coeff.push_back(0.5 / dx);
		}
		add_equation(result, v, index, coeff, (*pnts->GX)(p), local_weight);
		index.clear();
		coeff.clear();
		if (j == 0) {
			index.push_back(center); coeff.push_back(-1.0 / dy);
			index.push_back(center + nx); coeff.push_back(1.0 / dy);
		} else if (j + 1 >= method_grid->getCountY()) {
			index.push_back(center - nx); coeff.push_back(-1.0 / dy);
			index.push_back(center); coeff.push_back(1.0 / dy);
		} else {
			index.push_back(center - nx); coeff.push_back(-0.5 / dy);
			index.push_back(center + nx); coeff.push_back(0.5 / dy);
		}
		add_equation(result, v, index, coeff, (*pnts->GY)(p), local_weight);
	}
	matrix = result;
	wrap_sums(matrix, v, mask_solved, mask_undefined);
	return true;
};

void f_gradient::mark_solved_and_undefined(bitvec * mask_solved,
                                           bitvec * mask_undefined,
                                           bool i_am_cond) {
};

bool f_gradient::solvable_without_cond(const bitvec * mask_solved,
                                       const bitvec * mask_undefined,
                                       const extvec * X) {
	return true;
};

}; // namespace surfit
