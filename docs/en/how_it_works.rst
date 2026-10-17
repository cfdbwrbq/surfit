How it works
============

surfit does not interpolate point by point. It asks for the grid values that
minimize a sequence of functionals, one functional per gridding rule, and it
solves that sequence on a ladder of grids. This page describes the three pieces:
the CMOFS method, the penalty loop used for constraints, and the linear solvers.

The unknown
-----------

The result is one value in every cell of an equidistant grid. Inside a cell the
surface is constant, so the surface is a sum of step functions:

.. math::

   u(x,y) = \sum_{i,j} u_{ij} \, \phi_{ij}(x,y),

where :math:`\phi_{ij}` is 1 inside its cell and 0 outside, and the unknowns are
the cell values :math:`u_{ij}`.

Each gridding rule adds one functional :math:`\Phi_k(u)`. A rule that says "the
surface equals 10 inside area1" is a least-squares term over the cells inside
that area; a points rule is a sum over the measured points; a fault changes how
neighbouring cells are coupled. The order in which the rules are added is the
order of the functionals, and that order is the priority.

Why these energies
------------------

The two smoothness terms are the discrete bending energy of a thin plate: D1
penalises the slope and D2 the curvature, so without data the surface relaxes
to a constant or a plane. It is the same idea as minimum-curvature gridding in
geophysics, where the grid is a thin elastic sheet that passes through the data
and is allowed to bend [Wessel & Bercovici 1998]. A data-misfit term added to the
same energy is the classical thin-plate smoothing spline [Hutchinson 1995];
geostatistics looks at the same field as a realisation of a random process and
calls the interpolation kriging [Chilès & Delfiner 2012]. The rules mix both
views: hard conditions (points, areas, curves) act as data, soft ones as
misfit, and the completer is the bending energy itself.

* P. Wessel, D. Bercovici (1998). Interpolation with splines in tension: a
  Green's function approach. *Mathematical Geology* 30, 77–93.
  `doi:10.1023/A:1021713421882 <https://doi.org/10.1023/A:1021713421882>`_
* M. F. Hutchinson (1995). Interpolating mean rainfall using thin plate
  smoothing splines. *International Journal of Geographical Information
  Systems* 9, 385–403.
  `doi:10.1080/02693799508902045 <https://doi.org/10.1080/02693799508902045>`_
* J.-P. Chilès, P. Delfiner (2012). *Geostatistics: Modeling Spatial
  Uncertainty*. Wiley.
  `doi:10.1002/9781118136188 <https://doi.org/10.1002/9781118136188>`_

CMOFS
-----

The method is called CMOFS, *consecutive minimization of a functionals sequence*:

.. math::

   \Phi_1(u), \; \Phi_2(u), \; \ldots, \; \Phi_K(u).

The functionals are minimized in order. A functional that fixes a set of cells
marks them as solved, and the later functionals do not touch them again:

.. math::

   \frac{\partial \Phi_k(u)}{\partial u_j} = 0,
   \qquad j \text{ over the cells not solved yet}.

If that system has a unique solution, the unsolved cells are taken from it and
the method moves to the next functional. If it has no unique solution -- the
rule alone does not say enough -- the rule is not solved on its own. It is
attached as a condition to the next functional, and the two are minimized
together. That is why the first rule has the highest priority: the result
satisfies it as exactly as the data allows, and later rules fill in the rest.

Constraints -- inequalities, averages, histograms -- cannot be handled by one
unconstrained minimization. They go through the penalty loop below.

The solver does not start at the final grid
-------------------------------------------

Solving the whole system at the final resolution at once would be slow and would
let a coarse mistake propagate. The task is solved on a ladder of grids: the
first phase is :math:`8 \times 8` by default (``set_basis_cnt``), every phase
doubles the grid, and the solution is projected onto the finer one. The last
phase works on the grid the task asked for.

The log shows the ladder:

.. code-block:: text

   * Phase 1, grid size = 8 x 8 (map_area)
   ...
   * Phase 6, grid size = 121 x 121 (map_area)
   ...
   cg: (14641) iter : 113, error : 4.99215E-06, 0 sec

The live line also prints one dot per progress tick between the cell count and
``iter``; they are left out here. :doc:`python` shows how ``surfit.progress()``
turns the same events into a tqdm bar.

The tolerance ``tol`` applies to each linear solve on the way. The number of
phases follows from the requested grid size, not from the data.

The penalty loop
----------------

A constraint has to be enforced while the data term is minimized, so it is added
to the functional with a weight that grows until the solution stops moving:

.. math::

   \min_u \; T(u) + \rho \, P(u), \qquad \rho_{k+1} = m \, \rho_k,

where :math:`T` is the functional being minimized, :math:`P` the constraint and
:math:`m` the multiplier. The loop starts at ``penalty_weight`` (1), multiplies
the weight by ``penalty_weight_mult`` (10) each iteration, and stops when the
change of the solution between iterations falls below ``tol``, or after
``penalty_max_iter`` (99) iterations.

The per-rule argument ``penalty_factor`` is the base-10 logarithm of the weight
that rule starts with: 0 means 1, -2 means 0.01, 2 means 100. It is the initial
weight, not the growth rate; the growth is global. Rules that are constraints
have their own defaults: an inequality starts at 0, ``mean`` and ``wmean`` at
-2, so an average is a softer condition than a bound. The original manual
recommended -3 to 3, and that is still a reasonable range.

The settings are module functions, and they belong to the task state, so two
Sessions keep their own values:

.. code-block:: python

   surfit.set_penalty_max_iter(99)      # give up after this many iterations
   surfit.set_penalty_weight(1.0)       # first weight of the constraint
   surfit.set_penalty_weight_mult(10.0) # how fast it grows

Solvers
-------

Every phase produces a sparse linear system, solved by an iterative method.
``surfit.solvers_info()`` prints the list; all five are available:

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Name
     - Method
   * - ``cg``
     - Conjugate Gradients (the default)
   * - ``jcg``
     - Jacobi Conjugate Gradients, CG with Jacobi preconditioning
   * - ``rf``
     - Richardson's method with a fixed, optimally extrapolated parameter
   * - ``jacobi``
     - Jacobi
   * - ``ssor``
     - Symmetric Successive Overrelaxation

Select one with ``set_solver`` and set the tolerance in the Session (or with
``set_tol``):

.. code-block:: python

   task = surfit.Session(map_name="map", tol=1e-5)
   task.set_solver("cg")

``cg`` is the default and the usual choice. The solver reports the iteration
count and the achieved step (``max|alpha·p|``) in the log, and
``surfit.progress()`` turns those lines into a progress bar; :doc:`python` shows
both.

The tolerance is not an error bound
-----------------------------------

``tol`` limits the step of the solver, not the distance to the solution, and the
penalty loop stops when the norm of the solution stops changing. Both criteria
can be much more optimistic than the result. On an 81x81 task ``tol=1e-6`` left
the surface 0.7% of its value range away from the exact solution; on the
``mean``/``wmean`` examples the penalty loop stopped after two iterations,
14-21% away, and only at ``1e-10`` did the same runs agree with the exact
penalty solution. Expect the actual error to be orders of magnitude larger than
``tol``: use a value well below the accuracy you need, and check a result that
matters against a direct solve of the same task.

How the pieces fit
------------------

For each phase CMOFS walks the rule sequence. A rule that solves uniquely marks
its cells and moves on; a rule that does not is carried into the next;
constraints go through the penalty loop; the linear system of each step is
handed to the chosen solver. Then the grid is refined, the solution is
projected, and the sequence runs again. The surface that comes out is the
solution of the last phase on the requested grid.

A rule that matched nothing contributes nothing, and the flags each rule
returns are the quickest way to notice a typo in a name.
