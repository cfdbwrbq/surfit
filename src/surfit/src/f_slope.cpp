#include "surfit_ie.h"
#include "f_slope.h"
#include "area.h"
#include "mask.h"
#include "grid_user.h"
#include "matr_local.h"
#include "solvers.h"
#include "vec.h"
#include "bitvec.h"
#include <cmath>
namespace surfit {
f_slope::f_slope(REAL ilimit, const d_area * iarea, const d_mask * imask,
                 bool iinside, int imode, REAL imult) :
functional("f_slope", F_USUAL)
{
	limit = ilimit; area = iarea; mask = imask;
	inside = iinside; mode = imode; mult = imult;
};
f_slope::~f_slope() {};
int f_slope::this_get_data_count() const {
	return (area ? 1 : 0) + (mask ? 1 : 0);
};
const data * f_slope::this_get_data(int pos) const {
	if (area && pos == 0) return area;
	if (mask && pos == (area ? 1 : 0)) return mask;
	return NULL;
};
bool f_slope::minimize() { return true; };
static void add_equation(matr_local * matrix, extvec * v,
                         const std::vector<size_t> & index,
                         const std::vector<REAL> & coeff,
                         REAL target, REAL weight) {
	for (size_t a = 0; a < index.size(); a++) {
		(*v)(index[a]) += weight * coeff[a] * target;
		for (size_t b = 0; b < index.size(); b++)
			matrix->add(index[a], index[b], weight * coeff[a] * coeff[b]);
	}
};
bool f_slope::build_projection(matr *& matrix, extvec *& v) {
	size_t nx = method_grid->getCountX();
	size_t ny = method_grid->getCountY();
	size_t n = nx * ny;
	matr_local * result = new matr_local(n);
	v = create_extvec(n);
	size_t violations = 0;
	REAL dx = method_grid->stepX, dy = method_grid->stepY;
	for (size_t j = 0; j < ny; j++) {
		for (size_t i = 0; i < nx; i++) {
			size_t center = i + j * nx;
			if (method_mask_undefined && method_mask_undefined->get(center))
				continue;
			REAL x, y;
			method_grid->getCoordNode(i, j, x, y);
			bool in_region = true;
			if (area) {
				in_region = area->in_region(x, y);
				if (inside == false) in_region = !in_region;
			}
			if (mask && mask->getValue(x, y) == false) in_region = false;
			if (in_region == false) continue;
			if (mode == 0) {
				if (i + 1 < nx &&
				    !(method_mask_undefined &&
				      method_mask_undefined->get(center + 1))) {
					REAL diff = (*method_X)(center + 1) - (*method_X)(center);
					if (fabs(diff) > limit * dx) {
						REAL target = (diff > 0 ? 1 : -1) * limit * dx;
						add_equation(result, v, {center, center + 1},
						             {-1.0 / dx, 1.0 / dx}, target, mult);
						violations++;
					}
				}
				if (j + 1 < ny &&
				    !(method_mask_undefined &&
				      method_mask_undefined->get(center + nx))) {
					REAL diff = (*method_X)(center + nx) - (*method_X)(center);
					if (fabs(diff) > limit * dy) {
						REAL target = (diff > 0 ? 1 : -1) * limit * dy;
						add_equation(result, v, {center, center + nx},
						             {-1.0 / dy, 1.0 / dy}, target, mult);
						violations++;
					}
				}
			} else {
				if (i > 0 && i + 1 < nx &&
				    !(method_mask_undefined &&
				      (method_mask_undefined->get(center - 1) ||
				       method_mask_undefined->get(center + 1)))) {
					REAL second = (*method_X)(center + 1) -
					              2.0 * (*method_X)(center) + (*method_X)(center - 1);
					REAL bound = limit * dx * dx;
					if (fabs(second) > bound) {
						REAL target = (second > 0 ? 1 : -1) * bound;
						add_equation(result, v, {center - 1, center, center + 1},
						             {1.0 / (dx * dx), -2.0 / (dx * dx), 1.0 / (dx * dx)}, target, mult);
						violations++;
					}
				}
				if (j > 0 && j + 1 < ny &&
				    !(method_mask_undefined &&
				      (method_mask_undefined->get(center - nx) ||
				       method_mask_undefined->get(center + nx)))) {
					REAL second = (*method_X)(center + nx) -
					              2.0 * (*method_X)(center) + (*method_X)(center - nx);
					REAL bound = limit * dy * dy;
					if (fabs(second) > bound) {
						REAL target = (second > 0 ? 1 : -1) * bound;
						add_equation(result, v, {center - nx, center, center + nx},
						             {1.0 / (dy * dy), -2.0 / (dy * dy), 1.0 / (dy * dy)}, target, mult);
						violations++;
					}
				}
			}
		}
	}
	if (violations == 0) {
		delete result; v->release(); v = NULL; matrix = NULL;
		return false;
	}
	matrix = result;
	return true;
};
bool f_slope::make_matrix_and_vector(matr *& matrix, extvec *& v,
                                     bitvec * mask_solved, bitvec * mask_undefined) {
	return build_projection(matrix, v);
};
void f_slope::post_process(extvec * X) {
	for (int iteration = 0; iteration < 20; iteration++) {
		matr * matrix = NULL;
		extvec * v = NULL;
		if (!build_projection(matrix, v)) break;
		solve(matrix, v, X);
		delete matrix;
		if (v) v->release();
	}
};
void f_slope::mark_solved_and_undefined(bitvec * mask_solved, bitvec * mask_undefined, bool i_am_cond) {};
bool f_slope::solvable_without_cond(const bitvec * mask_solved, const bitvec * mask_undefined, const extvec * X) { return true; };
}; // namespace surfit
