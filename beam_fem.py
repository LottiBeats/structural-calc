"""
beam_fem.py
===========
A simple but complete Euler-Bernoulli beam finite element solver.

Degrees of freedom per node: [v (transverse displacement, positive upward),
                               theta (rotation, positive counterclockwise)]

The element DOF vector is ordered [v1, theta1, v2, theta2].  The cubic
Hermite shape functions are expressed in the isoparametric coordinate
xi in [-1, 1] where xi = 2*(x - x_left)/Le - 1.

Sign conventions
----------------
- Positive v        : upward displacement
- Positive P (load) : downward point load
- Positive M_applied: counterclockwise point moment
- Positive M_result : sagging (tension at bottom fibre)
- Positive V_result : upward shear on left face

Dependencies: numpy, matplotlib (standard scientific Python stack)
"""

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle, Polygon


# ---------------------------------------------------------------------------
# 5-point Gauss quadrature on [-1, 1]
# ---------------------------------------------------------------------------
_GP5, _GW5 = np.polynomial.legendre.leggauss(5)


# ---------------------------------------------------------------------------
# Cubic Hermite shape functions in isoparametric coords
# ---------------------------------------------------------------------------

def _hermite(xi, Le):
    """
    Cubic Hermite shape functions for one beam element mapped to xi in [-1,1].

    The physical DOF vector is d = [v1, theta1, v2, theta2].

    The mapping is  x = x_left + (xi+1)/2 * Le,  so dx/dxi = Le/2.

    Returns
    -------
    N   : ndarray (4,)  - shape functions  [N1, N2, N3, N4]
    B   : ndarray (4,)  - d^2N/dx^2  (curvature row, the B-matrix)
    B3  : ndarray (4,)  - d^3N/dx^3  (constant per element)
    """
    # ---- shape functions in xi ----
    # H1 = (2 - 3*xi + xi^3) / 4     -- displacement at node 1
    # H2 = Le/2 * (1 - xi - xi^2 + xi^3) / 4  -- rotation at node 1 (scaled)
    # H3 = (2 + 3*xi - xi^3) / 4     -- displacement at node 2
    # H4 = Le/2 * (-1 - xi + xi^2 + xi^3) / 4 -- rotation at node 2 (scaled)
    #
    # Here the rotation shape functions are pre-multiplied by Le/2 so that
    # the interpolation is simply N @ d_physical with d = [v1, th1, v2, th2].

    h = Le / 2.0
    N = np.array([
        (2.0 - 3.0*xi + xi**3) / 4.0,
        h * (1.0 - xi - xi**2 + xi**3) / 4.0,
        (2.0 + 3.0*xi - xi**3) / 4.0,
        h * (-1.0 - xi + xi**2 + xi**3) / 4.0,
    ])

    # ---- second derivative w.r.t. x ----
    # d/dx = (2/Le) * d/dxi
    # d^2N1/dxi^2 = 6*xi / 4 = 3*xi/2
    # d^2N2/dxi^2 = h * (-2 - 6*xi) / 4... wait let me do it cleanly:
    # N1(xi) = (2 - 3xi + xi^3)/4  => N1' = (-3 + 3xi^2)/4  => N1'' = 6xi/4
    # N2(xi) = h*(1 - xi - xi^2 + xi^3)/4 => N2'' = h*(-2 + 6xi)/4
    # N3(xi) = (2 + 3xi - xi^3)/4         => N3'' = -6xi/4
    # N4(xi) = h*(-1 - xi + xi^2 + xi^3)/4 => N4'' = h*(2 + 6xi)/4

    inv_dx = 2.0 / Le            # dxi/dx
    d2N_dxi2 = np.array([
        6.0 * xi / 4.0,
        h * (-2.0 + 6.0 * xi) / 4.0,
        -6.0 * xi / 4.0,
        h * (2.0 + 6.0 * xi) / 4.0,
    ])
    B = d2N_dxi2 * inv_dx**2     # d^2N/dx^2

    # ---- third derivative w.r.t. x (constant per element) ----
    # d^3N1/dxi^3 = 6/4
    # d^3N2/dxi^3 = h * 6/4
    # d^3N3/dxi^3 = -6/4
    # d^3N4/dxi^3 = h * 6/4
    d3N_dxi3 = np.array([6.0/4.0, h * 6.0/4.0, -6.0/4.0, h * 6.0/4.0])
    B3 = d3N_dxi3 * inv_dx**3    # d^3N/dx^3

    return N, B, B3


# ---------------------------------------------------------------------------
# Element stiffness matrix (exact closed-form)
# ---------------------------------------------------------------------------

def _element_stiffness(Le, EI):
    """
    4×4 Euler-Bernoulli beam element stiffness matrix.

    DOF order: [v1, theta1, v2, theta2].

    Parameters
    ----------
    Le : float  Element length [m].
    EI : float  Flexural rigidity [N·m²].
    """
    L = Le
    return EI / L**3 * np.array([
        [ 12.0,    6.0*L,  -12.0,   6.0*L],
        [  6.0*L,  4.0*L**2, -6.0*L,  2.0*L**2],
        [-12.0,   -6.0*L,   12.0,  -6.0*L],
        [  6.0*L,  2.0*L**2, -6.0*L,  4.0*L**2],
    ])


# ---------------------------------------------------------------------------
# BeamFEM class
# ---------------------------------------------------------------------------

class BeamFEM:
    """
    Euler-Bernoulli beam finite element solver.

    Assembles the global stiffness matrix from cubic Hermite elements, applies
    boundary conditions by DOF elimination, solves for nodal displacements and
    rotations, then evaluates displacement, bending moment and shear force on a
    fine grid (10× element density).

    Parameters
    ----------
    length : float
        Total beam span [m].
    E : float
        Young's modulus [Pa].
    I : float
        Second moment of area [m^4].
    n_elements : int
        Number of equal-length elements (default 200).
    """

    def __init__(self, length: float, E: float, I: float,
                 n_elements: int = 200):
        self.L = float(length)
        self.E = float(E)
        self.I = float(I)
        self.n_el = int(n_elements)
        self.EI = self.E * self.I

        self.n_nodes = self.n_el + 1
        self.n_dof = 2 * self.n_nodes     # 2 DOFs per node
        self.Le = self.L / self.n_el      # uniform element length

        self.x_nodes = np.linspace(0.0, self.L, self.n_nodes)

        # Global arrays
        self.K = np.zeros((self.n_dof, self.n_dof))
        self.F = np.zeros(self.n_dof)

        # Boundary condition list: [(dof_index, prescribed_value), ...]
        self._bc_dofs: list[tuple[int, float]] = []

        # Storage for visualisation
        self._supports: list[dict] = []
        self._point_loads: list[dict] = []
        self._point_moments: list[dict] = []
        self._distributed_loads: list[dict] = []

        # Populated by solve()
        self.u = None
        self.x_fine = None
        self.v_fine = None
        self.M_fine = None
        self.V_fine = None
        self.reactions: dict = {}

        self._assemble_K()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _node_at(self, x: float) -> int:
        """Index of the nearest mesh node to position *x*."""
        return int(round(float(x) / self.Le))

    def _dof_v(self, node: int) -> int:
        """Global DOF index for transverse displacement *v* at *node*."""
        return 2 * node

    def _dof_t(self, node: int) -> int:
        """Global DOF index for rotation *theta* at *node*."""
        return 2 * node + 1

    def _elem_dofs(self, e: int):
        """Return [dof_v_left, dof_t_left, dof_v_right, dof_t_right] for element *e*."""
        return [self._dof_v(e), self._dof_t(e),
                self._dof_v(e+1), self._dof_t(e+1)]

    def _assemble_K(self):
        """Assemble the global stiffness matrix from element matrices."""
        for e in range(self.n_el):
            ke = _element_stiffness(self.Le, self.EI)
            dofs = self._elem_dofs(e)
            for a in range(4):
                for b in range(4):
                    self.K[dofs[a], dofs[b]] += ke[a, b]

    def _x_to_xi(self, x: float):
        """
        Map a physical coordinate *x* to (element_index, xi).

        Returns
        -------
        e  : int    Element index (0-based, clamped to last element at x=L).
        xi : float  Isoparametric coordinate in [-1, 1].
        """
        x = float(np.clip(x, 0.0, self.L))
        e = min(int(x / self.Le), self.n_el - 1)
        xi = 2.0 * (x - e * self.Le) / self.Le - 1.0
        return e, xi

    # ------------------------------------------------------------------
    # Public API — define loads and supports
    # ------------------------------------------------------------------

    def add_support(self, x: float, support_type: str):
        """
        Add a support (boundary condition) at position *x*.

        Parameters
        ----------
        x : float
            Position along beam [m].
        support_type : str
            ``'pin'`` or ``'roller'`` → constrains *v = 0*;
            ``'fixed'`` → constrains *v = 0* and *theta = 0*.
        """
        node = self._node_at(x)
        x_actual = self.x_nodes[node]
        st = support_type.lower()

        if st in ('pin', 'roller'):
            self._bc_dofs.append((self._dof_v(node), 0.0))
        elif st == 'fixed':
            self._bc_dofs.append((self._dof_v(node), 0.0))
            self._bc_dofs.append((self._dof_t(node), 0.0))
        else:
            raise ValueError(
                f"Unknown support type '{support_type}'. "
                "Use 'pin', 'roller', or 'fixed'.")

        self._supports.append({'x': x_actual, 'type': st, 'node': node})

    def add_point_load(self, x: float, P: float):
        """
        Add a concentrated transverse load.

        Parameters
        ----------
        x : float
            Position along beam [m].
        P : float
            Load magnitude [N].  **Positive = downward.**
        """
        node = self._node_at(x)
        x_actual = self.x_nodes[node]
        # Downward load → force opposes positive v (upward) → subtract from F_v
        self.F[self._dof_v(node)] -= P
        self._point_loads.append({'x': x_actual, 'P': P})

    def add_point_moment(self, x: float, M: float):
        """
        Add a concentrated moment.

        Parameters
        ----------
        x : float
            Position along beam [m].
        M : float
            Moment magnitude [N·m].  **Positive = counterclockwise.**
        """
        node = self._node_at(x)
        x_actual = self.x_nodes[node]
        # Counterclockwise positive → add to F_theta
        self.F[self._dof_t(node)] += M
        self._point_moments.append({'x': x_actual, 'M': M})

    def add_udl(self, w: float, x1: float = 0.0, x2: float = None):
        """
        Add a uniformly distributed load over a span.

        Parameters
        ----------
        w : float
            Load intensity [N/m].  **Positive = downward.**
        x1 : float
            Start position [m] (default 0).
        x2 : float
            End position [m] (default = beam length).
        """
        if x2 is None:
            x2 = self.L
        self._add_distributed(w, w, float(x1), float(x2), label_as_udl=True)

    def add_trapezoidal_load(self, w1: float, w2: float,
                             x1: float, x2: float):
        """
        Add a linearly varying (trapezoidal) distributed load.

        Parameters
        ----------
        w1 : float
            Intensity at *x1* [N/m].  Positive = downward.
        w2 : float
            Intensity at *x2* [N/m].  Positive = downward.
        x1, x2 : float
            Start and end positions [m].
        """
        self._add_distributed(w1, w2, float(x1), float(x2),
                              label_as_udl=False)

    def _add_distributed(self, w1, w2, x1, x2, label_as_udl):
        """Internal: accumulate consistent nodal loads for a distributed load."""
        x1 = float(np.clip(x1, 0.0, self.L))
        x2 = float(np.clip(x2, 0.0, self.L))
        if x2 <= x1:
            raise ValueError("x2 must be greater than x1.")

        rec = {'type': 'udl' if label_as_udl else 'trapezoidal',
               'w1': w1, 'w2': w2, 'x1': x1, 'x2': x2}
        if label_as_udl:
            rec['w'] = w1
        self._distributed_loads.append(rec)

        for e in range(self.n_el):
            xe_l = e * self.Le
            xe_r = (e + 1) * self.Le

            ol = max(x1, xe_l)
            or_ = min(x2, xe_r)
            if or_ <= ol:
                continue

            # Evaluate consistent load vector over sub-interval [ol, or_]
            # using 5-point Gauss integration mapped to parent element xi.
            sub_Le = or_ - ol
            jac = sub_Le / 2.0
            fe = np.zeros(4)

            for xi_g, wg in zip(_GP5, _GW5):
                # Physical x at this Gauss point
                x_gp = ol + (xi_g + 1) / 2.0 * sub_Le
                # Linearly interpolated load
                t = (x_gp - x1) / (x2 - x1)
                w_gp = w1 * (1.0 - t) + w2 * t
                # Parent element xi
                xi_par = 2.0 * (x_gp - xe_l) / self.Le - 1.0
                N, _, _ = _hermite(xi_par, self.Le)
                fe += w_gp * N * jac * wg

            dofs = self._elem_dofs(e)
            for a in range(4):
                # Downward load → subtracts from F (opposes positive v)
                self.F[dofs[a]] -= fe[a]

    # ------------------------------------------------------------------
    # Solver
    # ------------------------------------------------------------------

    def solve(self):
        """
        Solve for nodal displacements and post-process results.

        Applies boundary conditions by DOF elimination (the constrained rows
        and columns are removed from the global system), solves the reduced
        linear system with ``numpy.linalg.solve``, then evaluates
        displacement, bending moment and shear force on a fine grid with
        10 points per element for smooth plots.

        Populates
        ---------
        self.u        : ndarray (n_dof,)   nodal displacement vector [m, rad]
        self.x_fine   : ndarray            x-coordinates of result grid [m]
        self.v_fine   : ndarray            transverse displacement [m]
        self.M_fine   : ndarray            bending moment [N·m]
        self.V_fine   : ndarray            shear force [N]
        self.reactions : dict              {x: {'V': force, 'M': moment}}
        """
        if not self._bc_dofs:
            raise RuntimeError(
                "No supports defined. Call add_support() first.")

        # ---- partition DOFs ----
        constrained = dict(self._bc_dofs)
        all_dofs = np.arange(self.n_dof)
        free_dofs = np.array([d for d in all_dofs if d not in constrained])
        fixed_dofs = np.array(list(constrained.keys()))
        fixed_vals = np.array([constrained[d] for d in fixed_dofs])

        K_ff = self.K[np.ix_(free_dofs, free_dofs)]
        K_fc = self.K[np.ix_(free_dofs, fixed_dofs)]
        F_f = self.F[free_dofs] - K_fc @ fixed_vals

        u_free = np.linalg.solve(K_ff, F_f)

        self.u = np.zeros(self.n_dof)
        self.u[free_dofs] = u_free
        self.u[fixed_dofs] = fixed_vals

        # ---- reaction forces ----
        R = self.K @ self.u - self.F
        self.reactions = {}
        for dof, _ in self._bc_dofs:
            node = dof // 2
            x_pos = self.x_nodes[node]
            self.reactions.setdefault(x_pos, {})
            if dof % 2 == 0:
                self.reactions[x_pos]['V'] = R[dof]
            else:
                self.reactions[x_pos]['M'] = R[dof]

        # ---- post-process on fine grid ----
        n_fine_per_el = 10
        n_fine = self.n_el * n_fine_per_el + 1
        self.x_fine = np.linspace(0.0, self.L, n_fine)
        self.v_fine = np.zeros(n_fine)
        self.M_fine = np.zeros(n_fine)
        self.V_fine = np.zeros(n_fine)

        for idx, xp in enumerate(self.x_fine):
            e, xi = self._x_to_xi(xp)
            dofs = self._elem_dofs(e)
            d_e = self.u[dofs]          # [v1, theta1, v2, theta2]

            N, B, B3 = _hermite(xi, self.Le)

            self.v_fine[idx] = N @ d_e
            self.M_fine[idx] = self.EI * (B @ d_e)
            self.V_fine[idx] = self.EI * (B3 @ d_e)

    # ------------------------------------------------------------------
    # Results summary
    # ------------------------------------------------------------------

    def results_summary(self):
        """
        Print key results to stdout (displacement, moment, shear, reactions).

        Must be called after :meth:`solve`.
        """
        if self.u is None:
            raise RuntimeError("Call solve() before results_summary().")

        v_mm = self.v_fine * 1e3
        M_kNm = -self.M_fine * 1e-3
        V_kN = self.V_fine * 1e-3
        x = self.x_fine

        print("\n" + "=" * 58)
        print("  Beam FEM Results Summary")
        print("=" * 58)
        print(f"  Length   : {self.L:.3f} m")
        print(f"  EI       : {self.EI:.4e} N·m²")
        print(f"  Elements : {self.n_el}")
        print("-" * 58)

        idx = np.argmax(np.abs(v_mm))
        print(f"  Max |v|  : {v_mm[idx]:+.4f} mm   "
              f"at x = {x[idx]:.3f} m")

        ip = np.argmax(M_kNm)
        im = np.argmin(M_kNm)
        print(f"  Max M (+): {M_kNm[ip]:+.4f} kN·m  "
              f"at x = {x[ip]:.3f} m")
        print(f"  Min M (-): {M_kNm[im]:+.4f} kN·m  "
              f"at x = {x[im]:.3f} m")

        vp = np.argmax(V_kN)
        vm = np.argmin(V_kN)
        print(f"  Max V (+): {V_kN[vp]:+.4f} kN    "
              f"at x = {x[vp]:.3f} m")
        print(f"  Min V (-): {V_kN[vm]:+.4f} kN    "
              f"at x = {x[vm]:.3f} m")

        print("-" * 58)
        print("  Reactions:")
        for x_pos, r in sorted(self.reactions.items()):
            if 'V' in r:
                print(f"    x = {x_pos:.3f} m  R_v = {r['V']*1e-3:+.4f} kN")
            if 'M' in r:
                print(f"    x = {x_pos:.3f} m  R_M = {r['M']*1e-3:+.4f} kN·m")
        print("=" * 58 + "\n")

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot(self, title: str = "Beam FEM Analysis",
             save_as: str = None) -> plt.Figure:
        """
        Generate a 4-panel figure: beam diagram, displacement, moment, shear.

        Parameters
        ----------
        title : str
            Figure title.
        save_as : str or None
            File path to save the figure (PNG/PDF/SVG).  If *None* the figure
            is only displayed.

        Returns
        -------
        fig : matplotlib.figure.Figure
        """
        if self.u is None:
            raise RuntimeError("Call solve() before plot().")

        v_mm = self.v_fine * 1e3
        M_kNm = self.M_fine * 1e-3
        V_kN = self.V_fine * 1e-3
        x = self.x_fine

        fig = plt.figure(figsize=(14, 11))
        fig.suptitle(title, fontsize=13, fontweight='bold', y=0.98)

        gs = gridspec.GridSpec(4, 1,
                               height_ratios=[1.5, 2, 2, 2],
                               hspace=0.50,
                               figure=fig)

        ax0 = fig.add_subplot(gs[0])
        ax1 = fig.add_subplot(gs[1])
        ax2 = fig.add_subplot(gs[2])
        ax3 = fig.add_subplot(gs[3])

        # -- Panel 1: beam diagram --
        self._draw_beam_diagram(ax0)
        ax0.set_title("Beam Layout", fontsize=9, pad=3)

        # -- Panel 2: displacement --
        ax1.plot(x, v_mm, color='steelblue', lw=1.5, zorder=3)
        ax1.fill_between(x, v_mm, alpha=0.20, color='steelblue')
        ax1.axhline(0.0, color='k', lw=0.6, ls='--')
        ax1.set_ylabel('v  [mm]', fontsize=8)
        ax1.set_xlabel('x  [m]', fontsize=8)
        ax1.tick_params(labelsize=7)
        _clean_ax(ax1)

        idx_v = np.argmax(np.abs(v_mm))
        v_range = np.ptp(v_mm) if np.ptp(v_mm) > 1e-14 else 1.0
        offset_v = -np.sign(v_mm[idx_v]) * v_range * 0.25
        ax1.annotate(f'{v_mm[idx_v]:.3f} mm',
                     xy=(x[idx_v], v_mm[idx_v]),
                     xytext=(x[idx_v], v_mm[idx_v] + offset_v),
                     arrowprops=dict(arrowstyle='->', color='steelblue', lw=1),
                     fontsize=7, color='steelblue', ha='center')

        # -- Panel 3: bending moment --
        ax2.plot(x, M_kNm, color='crimson', lw=1.5, zorder=3)
        ax2.fill_between(x, M_kNm, where=(M_kNm >= 0),
                         alpha=0.20, color='crimson')
        ax2.fill_between(x, M_kNm, where=(M_kNm < 0),
                         alpha=0.20, color='darkviolet')
        ax2.axhline(0.0, color='k', lw=0.6, ls='--')
        ax2.set_ylabel('M  [kN·m]', fontsize=8)
        ax2.set_xlabel('x  [m]', fontsize=8)
        ax2.tick_params(labelsize=7)
        _clean_ax(ax2)

        M_range = np.ptp(M_kNm) if np.ptp(M_kNm) > 1e-14 else 1.0
        ip = np.argmax(M_kNm)
        im = np.argmin(M_kNm)
        if M_kNm[ip] > 1e-6 * M_range:
            ax2.annotate(f'{M_kNm[ip]:.3f}',
                         xy=(x[ip], M_kNm[ip]),
                         xytext=(x[ip], M_kNm[ip] + M_range * 0.18),
                         arrowprops=dict(arrowstyle='->', color='crimson', lw=1),
                         fontsize=7, color='crimson', ha='center')
        if M_kNm[im] < -1e-6 * M_range:
            ax2.annotate(f'{M_kNm[im]:.3f}',
                         xy=(x[im], M_kNm[im]),
                         xytext=(x[im], M_kNm[im] - M_range * 0.18),
                         arrowprops=dict(arrowstyle='->', color='darkviolet', lw=1),
                         fontsize=7, color='darkviolet', ha='center')

        # -- Panel 4: shear force --
        ax3.plot(x, V_kN, color='seagreen', lw=1.5, zorder=3)
        ax3.fill_between(x, V_kN, where=(V_kN >= 0),
                         alpha=0.20, color='seagreen')
        ax3.fill_between(x, V_kN, where=(V_kN < 0),
                         alpha=0.20, color='darkorange')
        ax3.axhline(0.0, color='k', lw=0.6, ls='--')
        ax3.set_ylabel('V  [kN]', fontsize=8)
        ax3.set_xlabel('x  [m]', fontsize=8)
        ax3.tick_params(labelsize=7)
        _clean_ax(ax3)

        V_range = np.ptp(V_kN) if np.ptp(V_kN) > 1e-14 else 1.0
        idx_sv = np.argmax(np.abs(V_kN))
        offset_sv = np.sign(V_kN[idx_sv]) * V_range * 0.20
        ax3.annotate(f'{V_kN[idx_sv]:.3f} kN',
                     xy=(x[idx_sv], V_kN[idx_sv]),
                     xytext=(x[idx_sv], V_kN[idx_sv] + offset_sv),
                     arrowprops=dict(arrowstyle='->', color='seagreen', lw=1),
                     fontsize=7, color='seagreen', ha='center')

        if save_as:
            fig.savefig(save_as, dpi=150, bbox_inches='tight')
            print(f"  Figure saved: {save_as}")

        plt.show()
        return fig

    # ------------------------------------------------------------------
    # Beam diagram drawing
    # ------------------------------------------------------------------

    def _draw_beam_diagram(self, ax):
        """Draw beam diagram: beam rectangle, supports, loads."""
        y_beam = 0.50
        beam_h = 0.06

        ax.set_xlim(-0.06 * self.L, 1.06 * self.L)
        ax.set_ylim(-0.25, 1.0)

        # Beam
        beam_rect = Rectangle((0.0, y_beam - beam_h), self.L, 2.0 * beam_h,
                               facecolor='#2c2c2c', edgecolor='black',
                               lw=1.5, zorder=5)
        ax.add_patch(beam_rect)

        # Distributed loads
        for dl in self._distributed_loads:
            x1, x2 = dl['x1'], dl['x2']
            w_val = dl.get('w', dl.get('w1', 0.0))
            top_y = y_beam + beam_h + 0.22

            xs_fill = [x1, x2, x2, x1]
            ys_fill = [y_beam + beam_h, y_beam + beam_h, top_y, top_y]
            ax.fill(xs_fill, ys_fill, alpha=0.25, color='royalblue', zorder=2)
            ax.plot([x1, x2], [top_y, top_y],
                    color='royalblue', lw=1.2, zorder=3)

            n_arr = max(2, int((x2 - x1) / self.L * 14) + 1)
            for xa in np.linspace(x1, x2, n_arr):
                ax.annotate('',
                            xy=(xa, y_beam + beam_h + 0.01),
                            xytext=(xa, top_y - 0.02),
                            arrowprops=dict(arrowstyle='->',
                                            color='royalblue', lw=0.9),
                            zorder=4)

            ax.text((x1 + x2) / 2.0, top_y + 0.05,
                    f'w = {w_val/1e3:.1f} kN/m',
                    ha='center', va='bottom', fontsize=7, color='royalblue')

        # Supports
        for sup in self._supports:
            x_s = sup['x']
            stype = sup['type']
            y_base = y_beam - beam_h

            if stype in ('pin', 'roller'):
                tri_h = 0.12
                tri_w = 0.07
                tri = Polygon(
                    [[x_s,          y_base],
                     [x_s - tri_w,  y_base - tri_h],
                     [x_s + tri_w,  y_base - tri_h]],
                    closed=True,
                    facecolor='white', edgecolor='black', lw=1.2, zorder=6)
                ax.add_patch(tri)
                gy = y_base - tri_h
                ax.plot([x_s - tri_w * 1.4, x_s + tri_w * 1.4],
                        [gy, gy], 'k-', lw=1.5, zorder=6)
                for hx in np.linspace(x_s - tri_w * 1.2,
                                      x_s + tri_w * 1.2, 6):
                    ax.plot([hx, hx - 0.014], [gy, gy - 0.04],
                            'k-', lw=0.8, zorder=6)

            elif stype == 'fixed':
                bar_w = 0.025
                bar_h = 0.28
                bx = x_s - bar_w if x_s < self.L / 2.0 else x_s
                bar = Rectangle((bx, y_beam - bar_h / 2.0),
                                 bar_w, bar_h,
                                 facecolor='#555555', edgecolor='black',
                                 lw=1.5, zorder=6)
                ax.add_patch(bar)
                ys_h = np.linspace(y_beam - bar_h / 2.0 + 0.02,
                                   y_beam + bar_h / 2.0 - 0.02, 7)
                for yh in ys_h:
                    if x_s < self.L / 2.0:
                        ax.plot([bx - 0.03, bx], [yh - 0.02, yh + 0.02],
                                'k-', lw=0.8, zorder=7)
                    else:
                        ax.plot([bx + bar_w, bx + bar_w + 0.03],
                                [yh - 0.02, yh + 0.02], 'k-', lw=0.8, zorder=7)

        # Point loads
        for pl in self._point_loads:
            x_p, P = pl['x'], pl['P']
            y_tip = y_beam + beam_h + 0.01
            y_tail = y_tip + 0.22
            ax.annotate('',
                        xy=(x_p, y_tip), xytext=(x_p, y_tail),
                        arrowprops=dict(arrowstyle='->', color='red',
                                        lw=2.0, mutation_scale=12),
                        zorder=8)
            ax.text(x_p, y_tail + 0.04, f'{P/1e3:.1f} kN',
                    ha='center', va='bottom', fontsize=7,
                    color='red', fontweight='bold')

        # Point moments (arc + label)
        for pm in self._point_moments:
            x_m, M_val = pm['x'], pm['M']
            r = 0.07
            th_arc = np.linspace(0.15 * np.pi, 1.85 * np.pi, 60)
            ax.plot(x_m + r * np.cos(th_arc),
                    y_beam + r * np.sin(th_arc),
                    color='darkorange', lw=1.5, zorder=8)
            ax.text(x_m, y_beam + r + 0.06,
                    f'M = {M_val/1e3:.1f} kN·m',
                    ha='center', va='bottom', fontsize=7, color='darkorange')

        # Axes clean-up
        for sp in ['top', 'right', 'left']:
            ax.spines[sp].set_visible(False)
        ax.set_yticks([])
        ax.set_xlabel('x  [m]', fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(False)
        ax.set_xlim(-0.06 * self.L, 1.06 * self.L)


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _clean_ax(ax):
    """Remove top/right spines and add a light dotted grid."""
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, which='major', ls=':', lw=0.5, alpha=0.6)


# ---------------------------------------------------------------------------
# Workflow helpers — beam actions into report calculations
# ---------------------------------------------------------------------------

@dataclass
class BeamLoadCase:
    """Named beam load case used for overlay plots and result extraction."""

    name: str
    color: str
    apply: Callable[["BeamFEM"], None]


def closed_form_simply_supported_udl(w: float, L: float, E: float | None = None,
                                     I: float | None = None):
    """Closed-form actions for a simply supported beam under full-span UDL.

    Parameters
    ----------
    w : float
        Uniform load [N/m].
    L : float
        Span [m].
    E : float, optional
        Young's modulus [Pa]. Needed for deflection.
    I : float, optional
        Second moment of area [m^4]. Needed for deflection.
    """
    out = {
        'M_max_Nm': float(w * L**2 / 8.0),
        'V_max_N': float(w * L / 2.0),
    }
    if E is not None and I is not None:
        out['delta_max_m'] = float(5.0 * w * L**4 / (384.0 * E * I))
    return out


def summarise_beam_actions(beam: "BeamFEM", case_name: str = ""):
    """Return report-friendly beam actions from a solved beam."""
    if beam.u is None:
        raise RuntimeError('Call solve() before summarise_beam_actions().')

    x = np.asarray(beam.x_fine, dtype=float)
    v = np.asarray(beam.v_fine, dtype=float)
    M = np.asarray(beam.M_fine, dtype=float)
    V = np.asarray(beam.V_fine, dtype=float)

    i_v = int(np.argmax(np.abs(v)))
    i_M = int(np.argmax(np.abs(M)))
    i_V = int(np.argmax(np.abs(V)))

    return {
        'case_name': case_name,
        'source': 'beam_fem',
        'M_Ed_Nm': float(abs(M[i_M])),
        'M_Ed_signed_Nm': float(M[i_M]),
        'x_M_Ed_m': float(x[i_M]),
        'V_Ed_N': float(abs(V[i_V])),
        'V_Ed_signed_N': float(V[i_V]),
        'x_V_Ed_m': float(x[i_V]),
        'delta_max_m': float(abs(v[i_v])),
        'delta_signed_m': float(v[i_v]),
        'x_delta_max_m': float(x[i_v]),
        'beam': beam,
    }


def solve_load_case(length: float, E: float, I: float, case: BeamLoadCase,
                    n_elements: int = 200,
                    supports: Iterable[tuple[float, str]] | None = None):
    """Solve one named load case and return both beam + summary."""
    beam = BeamFEM(length=length, E=E, I=I, n_elements=n_elements)
    if supports is None:
        supports = [(0.0, 'pin'), (length, 'roller')]
    for x_s, st in supports:
        beam.add_support(x_s, st)
    case.apply(beam)
    beam.solve()
    return summarise_beam_actions(beam, case.name)


def analyse_load_combinations(length: float, E: float, I: float,
                              cases: Iterable[BeamLoadCase],
                              n_elements: int = 200,
                              supports: Iterable[tuple[float, str]] | None = None):
    """Solve multiple beam combinations and return a dict keyed by case name."""
    return {case.name: solve_load_case(length, E, I, case,
                                       n_elements=n_elements,
                                       supports=supports)
            for case in cases}


def plot_load_combination_overlays(length: float, E: float, I: float,
                                   cases: Iterable[BeamLoadCase],
                                   save_as: str | None = None,
                                   n_elements: int = 200,
                                   supports: Iterable[tuple[float, str]] | None = None,
                                   title: str = 'Load combinations - displacement, moment, shear'):
    """Plot multiple load combinations as coloured overlays.

    Returns
    -------
    fig : matplotlib.figure.Figure
    summaries : dict[str, dict]
        Each entry contains the solved beam plus max M/V/deflection values.
    """
    cases = list(cases)
    if not cases:
        raise ValueError('At least one BeamLoadCase is required.')

    summaries = analyse_load_combinations(length, E, I, cases,
                                          n_elements=n_elements,
                                          supports=supports)

    first_beam = next(iter(summaries.values()))['beam']

    fig = plt.figure(figsize=(12, 10))
    gs = gridspec.GridSpec(4, 1, height_ratios=[1.4, 2, 2, 2],
                           hspace=0.45, figure=fig)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])
    ax2 = fig.add_subplot(gs[2])
    ax3 = fig.add_subplot(gs[3])

    first_beam._draw_beam_diagram(ax0)
    ax0.set_title('Beam layout', fontsize=10)

    for case in cases:
        result = summaries[case.name]
        beam = result['beam']
        x = beam.x_fine
        v_mm = beam.v_fine * 1e3
        M_kNm = -beam.M_fine * 1e-3
        V_kN = beam.V_fine * 1e-3

        ax1.plot(x, v_mm, lw=1.8, label=case.name, color=case.color)
        ax2.plot(x, M_kNm, lw=1.8, label=case.name, color=case.color)
        ax3.plot(x, V_kN, lw=1.8, label=case.name, color=case.color)

    for ax, ylabel in ((ax1, 'v [mm]'), (ax2, 'M [kN·m]'), (ax3, 'V [kN]')):
        ax.axhline(0.0, color='black', lw=0.7, ls='--')
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xlabel('x [m]', fontsize=9)
        ax.grid(True, ls=':', lw=0.5, alpha=0.7)
        ax.tick_params(labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    ax2.legend(loc='best', fontsize=8, frameon=False)
    fig.suptitle(title, fontsize=13, fontweight='bold')

    if save_as:
        fig.savefig(save_as, dpi=180, bbox_inches='tight')

    return fig, summaries


# ---------------------------------------------------------------------------
# __main__ — three demonstration examples
# ---------------------------------------------------------------------------

if __name__ == '__main__':

    # IPE300 steel section
    E = 210e9        # Pa
    I = 8356e-8      # m^4  (= 8356 cm^4)

    # ------------------------------------------------------------------
    # Example 1 — Simply supported, L = 6 m, UDL 10 kN/m
    # ------------------------------------------------------------------
    print("\n>>> Example 1: Simply supported beam, UDL 10 kN/m")
    b1 = BeamFEM(length=6.0, E=E, I=I, n_elements=200)
    b1.add_support(0.0, 'pin')
    b1.add_support(6.0, 'roller')
    b1.add_udl(10e3)               # 10 kN/m over full span
    b1.solve()
    b1.results_summary()
    b1.plot(title="Example 1 — Simply Supported, UDL 10 kN/m, IPE300",
            save_as="beam_1.png")

    # ------------------------------------------------------------------
    # Example 2 — Cantilever, L = 4 m, 20 kN tip load
    # ------------------------------------------------------------------
    print("\n>>> Example 2: Cantilever, 20 kN tip load")
    b2 = BeamFEM(length=4.0, E=E, I=I, n_elements=200)
    b2.add_support(0.0, 'fixed')
    b2.add_point_load(4.0, 20e3)   # 20 kN downward at free end
    b2.solve()
    b2.results_summary()
    b2.plot(title="Example 2 — Cantilever, 20 kN Tip Load, IPE300",
            save_as="beam_2.png")

    # ------------------------------------------------------------------
    # Example 3 — Two-span continuous, L = 10 m, UDL 8 kN/m
    #             Supports at 0, 5, 10 m
    # ------------------------------------------------------------------
    print("\n>>> Example 3: Two-span continuous beam, UDL 8 kN/m")
    b3 = BeamFEM(length=10.0, E=E, I=I, n_elements=200)
    b3.add_support(0.0,  'pin')
    b3.add_support(5.0,  'roller')
    b3.add_support(10.0, 'roller')
    b3.add_udl(8e3)                # 8 kN/m over full span
    b3.solve()
    b3.results_summary()
    b3.plot(title="Example 3 — Two-Span Continuous Beam, UDL 8 kN/m, IPE300",
            save_as="beam_3.png")
