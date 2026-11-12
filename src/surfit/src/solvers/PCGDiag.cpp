#include "../surfit_ie.h"
#include <algorithm>
#include "threads.h"
#include "../solvers.h"
#include "vec.h"
#include "vec_alg.h"
#include "../matr.h"
#include "../variables_tcl.h"

namespace surfit {

extvec * PCGDiag(matr * A, const extvec * b, int max_it, REAL tol,
                 extvec *& X, size_t & iters, REAL undef_value) {
	writelog2(LOG_MESSAGE, "pcg: (%d) ", b->size());
	iters = 0;
	int N = b->size();
	extvec * x = NULL;
	if (!X)
		x = create_extvec(*b);
	else {
		x = X;
		X = NULL;
	}
	extvec * r = create_extvec(N, 0, 0);
	extvec * z = create_extvec(N, 0, 0);
	extvec * p = create_extvec(N, 0, 0);
	extvec * q = create_extvec(N, 0, 0);
	A->mult(x, r);
	for (int i = 0; i < N; i++)
		(*r)(i) = (*b)(i) - (*r)(i);
	REAL bnrm2 = norm2(b);
	if (bnrm2 == 0)
		bnrm2 = 1;
	REAL error_norm = norm2(x, undef_value);
	REAL rho = 0;
	for (int iter = 1; iter <= max_it; iter++) {
		for (int i = 0; i < N; i++) {
			REAL diagonal = A->at(i, i);
			(*z)(i) = (diagonal == 0) ? (*r)(i) : (*r)(i) / diagonal;
		}
		REAL rho_new = times(r, z);
		if (iter == 1) {
			rho = rho_new;
			*p = *z;
		} else {
			REAL beta = (rho == 0) ? 0 : rho_new / rho;
			for (int i = 0; i < N; i++)
				(*p)(i) = (*z)(i) + beta * (*p)(i);
			rho = rho_new;
		}
		A->mult(p, q);
		REAL pq = times(p, q);
		REAL alpha = (fabs(pq) > 1e-30) ? rho / pq : 0;
		REAL error = 0;
		for (int i = 0; i < N; i++) {
			(*x)(i) += alpha * (*p)(i);
			error = MAX(error, fabs(alpha * (*p)(i)));
		}
		error = (error_norm == 0) ? 0 : error / error_norm;
		iters = iter;
		if (error <= tol || stop_execution)
			break;
		for (int i = 0; i < N; i++)
			(*r)(i) -= alpha * (*q)(i);
	}
	r->release();
	z->release();
	p->release();
	q->release();
	return x;
}

}; // namespace surfit
