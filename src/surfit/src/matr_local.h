#ifndef __surfit_matr_local_included__
#define __surfit_matr_local_included__
#include "matr.h"
#include "vec.h"
#include <algorithm>
#include <vector>
namespace surfit {
class matr_local : public matr {
public:
	explicit matr_local(size_t size) : n(size), row_cols(size), row_vals(size) {};
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
}; // namespace surfit
#endif
