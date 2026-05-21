"""
masonry.py — Masonry wall module (EN 1996-1-1)
Unit-aware with forallpeople. No manual conversions.
"""

from pathlib import Path
import tempfile
import math
import os

from handcalcs.decorator import handcalc
import forallpeople as si
si.environment('structural', top_level=True)

from calc_core import hc_block, S, T, N, TBL, MH, CheckContext, FIG


def masonry_wall_vertical(
    label,
    height,         # e.g. 3.0 * m
    thickness,      # e.g. 250 * mm
    length,         # e.g. 5.0 * m
    N_k,            # e.g. 120 * kN  (characteristic vertical load)
    f_b,            # e.g. 10  * MPa (unit compressive strength)
    f_m,            # e.g. 6   * MPa (mortar strength)
    gamma_M = 2.5,
    K       = 0.55,
    alpha   = 0.7,
    beta    = 0.3,
):
    cc = CheckContext()
    blocks = []

    blocks.append(MH(f"Masonry wall — {thickness}",
                     f"{label}  |  EN 1996-1-1", material="masonry"))

    blocks.append(S("Design parameters"))
    blocks.append(T(
        f"Unreinforced masonry wall, t = {thickness}, height = {height}, "
        f"length = {length}. Units f_b = {f_b}, mortar f_m = {f_m}. "
        f"γ_M = {gamma_M}, K = {K}."
    ))

    blocks.append(S("Characteristic compressive strength — EN 1996-1-1 Eq. 3.1"))

    @handcalc(override="long", precision=3)
    def _fk(K, f_b, alpha, f_m, beta, gamma_M):
        f_k = K * f_b**alpha * f_m**beta   # Characteristic strength
        f_d = f_k / gamma_M                # Design strength
        return f_k, f_d

    latex, (f_k, f_d) = _fk(K, f_b, alpha, f_m, beta, gamma_M)
    blocks.append(hc_block(latex, "Masonry compressive strength"))

    blocks.append(S("Slenderness check"))

    @handcalc(override="long", precision=2)
    def _slender(height, thickness):
        lambda_w = height / thickness     # Slenderness ratio
        return lambda_w

    latex, lambda_w = _slender(height, thickness)
    blocks.append(hc_block(latex, "Slenderness ratio"))
    blocks.append(N("Maximum slenderness = 27 for walls with lateral restraint (EN 1996-1-1 cl. 5.5.1.4)."))

    blocks.append(S("Vertical load capacity"))

    @handcalc(override="long", precision=2)
    def _capacity(N_k, thickness, length, f_d, lambda_w):
        N_Ed  = 1.35 * N_k                       # Design load
        A     = thickness * length                # Wall plan area
        phi   = 1 - (lambda_w / 140)**2          # Reduction factor (simplified)
        N_Rd  = phi * f_d * A                    # Design resistance
        return N_Ed, A, phi, N_Rd

    latex, (N_Ed, A, phi, N_Rd) = _capacity(N_k, thickness, length, f_d, lambda_w)
    blocks.append(hc_block(latex, "Wall capacity"))
    blocks.append(cc.check("Vertical load: N_Ed / N_Rd", N_Ed, N_Rd))

    return blocks


def _plot_masonry_trykline(
    floor_names,
    heights,
    wall_width,
    y_positions,
    y_mid,
    axial_loads,
    shear_forces,
    top_moment,
    x_trykline,
    figure_path=None,
):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8.5, 7.0))

    for i in range(len(heights)):
        ax.fill_between(
            [0, wall_width],
            y_positions[i],
            y_positions[i + 1],
            color="peachpuff",
            edgecolor="black",
            alpha=0.4,
        )

    for i, name in enumerate(floor_names):
        ax.text(-0.9, y_mid[i], name, va="center", fontsize=9)

    for i, load in enumerate(axial_loads):
        ax.arrow(
            wall_width / 2.0,
            y_positions[i + 1] + 0.1,
            0,
            -0.4,
            head_width=0.15,
            head_length=0.15,
            fc="blue",
            ec="blue",
            linewidth=0.8,
        )
        ax.text(
            wall_width / 2.0 + 0.25,
            y_positions[i + 1] + 0.1,
            f"N{i + 1} = {load:.1f} kN",
            color="blue",
            fontsize=8,
        )

    for i, shear in enumerate(shear_forces):
        ax.arrow(
            wall_width + 0.2,
            y_mid[i],
            -0.4,
            0,
            head_width=0.15,
            head_length=0.15,
            fc="red",
            ec="red",
            linewidth=0.8,
        )
        ax.text(
            wall_width + 0.35,
            y_mid[i],
            f"V{i + 1} = {shear:.1f} kN",
            color="red",
            fontsize=8,
            va="center",
        )

    ax.text(
        wall_width + 0.35,
        y_positions[-1] + 0.3,
        f"M_top = {top_moment:.1f} kNm",
        color="green",
        fontsize=9,
    )

    centerline_x = wall_width / 2.0
    ax.plot(
        x_trykline,
        y_positions,
        "-o",
        color="blue",
        label="Tryklinie",
        linewidth=1.8,
        alpha=0.8,
    )
    ax.axvline(
        centerline_x,
        color="red",
        linestyle="--",
        linewidth=1,
        alpha=0.6,
        label="Væggens centerlinje",
    )

    ax.set_xlim(-1.5, wall_width + 2.0)
    ax.set_ylim(0, y_positions[-1] + 1.0)
    ax.set_title("Masonry Wall with Loads and Tryklinie", fontsize=12)
    ax.set_xlabel("Width (m)", fontsize=10)
    ax.set_ylabel("Height (m)", fontsize=10)
    ax.set_aspect("auto")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(fontsize=9, loc="upper right")
    fig.tight_layout()

    if figure_path is None:
        fd, figure_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
    else:
        Path(figure_path).parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(figure_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return figure_path


def _plot_masonry_plan_centroid(
    elements,
    x_max,
    y_max,
    x_c,
    y_c,
    figure_path=None,
):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    fig, ax = plt.subplots(figsize=(8.5, 6.5))

    for idx, (d_n, b_n, x, y) in enumerate(elements, start=1):
        rect = Rectangle(
            (x - b_n / 2.0, y - d_n / 2.0),
            b_n,
            d_n,
            linewidth=1.0,
            edgecolor="blue",
            facecolor="lightblue",
            alpha=0.9,
        )
        ax.add_patch(rect)
        ax.scatter(x, y, color="blue", s=14)
        ax.text(x + 0.25, y + 0.25, f"{idx}", fontsize=8)

    ax.scatter([x_c], [y_c], color="red", marker="x", s=120, label="Resultant centroid")
    ax.axvline(x=x_max / 2.0, color="green", linestyle="--", linewidth=1.0)
    ax.axhline(y=y_max / 2.0, color="green", linestyle="--", linewidth=1.0)

    ax.set_xlim(0.0, x_max)
    ax.set_ylim(0.0, y_max)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_title("Wall elements and resultant centroid")
    ax.grid(True, linestyle=":", linewidth=0.5, alpha=0.6)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()

    if figure_path is None:
        fd, figure_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
    else:
        Path(figure_path).parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(figure_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return figure_path


def masonry_wall_multi_storey_ritter(
    label,
    floor_names,
    heights,
    wall_width,
    thickness,
    compressive_strength,
    design_strength,
    unit_weight,
    axial_loads,
    shear_forces,
    top_moment,
    Kt=0.9,
    figure_path=None,
    figure_caption="",
):
    if not (
        len(floor_names) == len(heights) == len(axial_loads) == len(shear_forces)
    ):
        raise ValueError("floor_names, heights, axial_loads and shear_forces must have the same length.")

    cc = CheckContext()
    blocks = []

    blocks.append(
        MH(
            f"Masonry wall - {thickness}",
            f"{label}  |  Multi-storey wall stability / Ritter",
            material="masonry",
        )
    )

    blocks.append(S("Design parameters"))
    blocks.append(T(
        f"Multi-storey masonry wall with width = {wall_width} m and thickness = {thickness} mm. "
        f"The storey-by-storey check follows the same workflow as your script: self-weight per storey "
        f"is taken as G = unit_weight * h, moments are accumulated from top to bottom from storey shears, "
        f"and the vertical resistance is estimated using the Ritter-style reduction with Kt = {Kt}."
    ))
    blocks.append(N(
        "Assumption carried over from the script: unit_weight is treated as a line load parameter for each storey "
        "via G = unit_weight * h, and the resulting G-values are added directly to the storey axial loads."
    ))

    blocks.append(TBL(
        ["Property", "Symbol", "Value"],
        [
            ["Wall width", "b", f"{wall_width} m"],
            ["Wall thickness", "t", f"{thickness} mm"],
            ["Compressive strength", "f_k", f"{compressive_strength} MPa"],
            ["Design strength", "f_d", f"{design_strength} MPa"],
            ["Unit weight parameter", "g", f"{unit_weight} kN/m^2"],
            ["Top moment", "M_top", f"{top_moment} kNm"],
            ["Long-term factor", "K_t", f"{Kt}"],
        ]
    ))

    G = [unit_weight * h for h in heights]
    N_total = [axial_loads[i] + G[i] for i in range(len(axial_loads))]

    y_positions = [0.0]
    for h in heights:
        y_positions.append(y_positions[-1] + h)
    y_mid = [(y_positions[i] + y_positions[i + 1]) / 2.0 for i in range(len(heights))]

    moments = []
    for i in range(len(heights)):
        m_val = top_moment
        for j in range(i, len(heights)):
            m_val += shear_forces[j] * heights[j]
        moments.append(m_val)

    eccentricities = []
    td = thickness / 1000.0
    N_rd_list = []
    kr_list = []
    a_eff_list = []

    for i in range(len(heights)):
        n_total = N_total[i]
        m_val = moments[i]
        e_val = m_val / n_total if abs(n_total) > 1e-12 else float("inf")
        eccentricities.append(e_val)

        td_eff = td - 2.0 * e_val
        if td_eff <= 0:
            kr_list.append(0.0)
            a_eff_list.append(0.0)
            N_rd_list.append(0.0)
            continue

        a_eff = wall_width * td_eff
        a_eff_list.append(a_eff)

        kr = 1.0
        for _ in range(20):
            kr_new = 1.0 / (1.0 + (12.0 / (kr * math.pi**2)) * (heights[i] / td_eff) ** 2)
            if abs(kr_new - kr) < 1e-5:
                kr = kr_new
                break
            kr = kr_new

        kr_list.append(kr)
        n_rd = Kt * kr * a_eff * design_strength * 1e3
        N_rd_list.append(n_rd)

    centerline_x = wall_width / 2.0
    x_trykline = [centerline_x - e for e in eccentricities] + [centerline_x]

    blocks.append(S("Storey loads and eccentricity"))
    blocks.append(TBL(
        ["Floor", "h [m]", "G [kN]", "N [kN]", "N_total [kN]", "V [kN]", "M [kNm]", "e = M/N [m]"],
        [
            [
                floor_names[i],
                f"{heights[i]:.2f}",
                f"{G[i]:.2f}",
                f"{axial_loads[i]:.2f}",
                f"{N_total[i]:.2f}",
                f"{shear_forces[i]:.2f}",
                f"{moments[i]:.2f}",
                f"{eccentricities[i]:.4f}" if math.isfinite(eccentricities[i]) else "inf",
            ]
            for i in range(len(heights))
        ]
    ))

    blocks.append(S("Ritter resistance by storey"))
    blocks.append(TBL(
        ["Floor", "t_eff [m]", "A_eff [m^2]", "K_r [-]", "N_Rd [kN]", "Utilization N/N_Rd [-]"],
        [
            [
                floor_names[i],
                f"{max(td - 2.0 * eccentricities[i], 0.0):.4f}" if math.isfinite(eccentricities[i]) else "0.0000",
                f"{a_eff_list[i]:.4f}",
                f"{kr_list[i]:.3f}",
                f"{N_rd_list[i]:.1f}",
                f"{(N_total[i] / N_rd_list[i]):.3f}" if N_rd_list[i] > 0 else "inf",
            ]
            for i in range(len(heights))
        ]
    ))

    for i in range(len(heights)):
        demand = N_total[i]
        capacity = N_rd_list[i]
        if capacity <= 0:
            blocks.append(N(
                f"{floor_names[i]}: invalid effective thickness because t - 2e <= 0. "
                "The eccentricity is too large for the assumed wall geometry."
            ))
        else:
            blocks.append(cc.check(f"{floor_names[i]}: N_total / N_Rd", demand, capacity))

    blocks.append(S("Sample equation"))

    @handcalc(override="long", precision=3)
    def _ritter_example(Kt, Kr, b, t_eff, fd):
        A_eff = b * t_eff
        N_Rd = Kt * Kr * A_eff * fd * 1e3
        return A_eff, N_Rd

    first_valid = next((i for i, val in enumerate(N_rd_list) if val > 0), None)
    if first_valid is not None:
        t_eff = td - 2.0 * eccentricities[first_valid]
        latex, (A_eff_example, N_Rd_example) = _ritter_example(
            Kt, kr_list[first_valid], wall_width, t_eff, design_strength
        )
        blocks.append(hc_block(latex, f"Ritter example ({floor_names[first_valid]})"))

    plot_path = _plot_masonry_trykline(
        floor_names=floor_names,
        heights=heights,
        wall_width=wall_width,
        y_positions=y_positions,
        y_mid=y_mid,
        axial_loads=axial_loads,
        shear_forces=shear_forces,
        top_moment=top_moment,
        x_trykline=x_trykline,
        figure_path=figure_path,
    )
    blocks.append(S("Tryklinie plot"))
    blocks.append(FIG(
        plot_path,
        figure_caption or "Wall geometry, storey loads and calculated tryklinie.",
        width_mm=135,
    ))

    return blocks


def masonry_wall_plan_lateral_distribution(
    label,
    elements,
    x_max,
    y_max,
    floor_height,
    D_x,
    E_x,
    D_y,
    E_y,
    figure_path=None,
    figure_caption="",
):
    cc = CheckContext()
    blocks = []

    if not elements:
        raise ValueError("elements must contain at least one wall element.")

    blocks.append(
        MH(
            "Masonry wall plan",
            f"{label}  |  Plan stiffness, centroid and lateral distribution",
            material="masonry",
        )
    )

    blocks.append(S("Design parameters"))
    blocks.append(T(
        "Plan-based wall-group component using the same assumptions as your script. "
        "Each wall element is entered as (d_N_or_b_W, b_N, x, y). "
        "Stiffness in the N direction is taken as I_sub,N = b_N d_N^3 and stiffness in the W direction as I_sub,W = d_N b_N^3."
    ))

    blocks.append(TBL(
        ["Property", "Symbol", "Value"],
        [
            ["Plan dimension x", "x_max", f"{x_max} m"],
            ["Plan dimension y", "y_max", f"{y_max} m"],
            ["Floor height", "h_f", f"{floor_height} m"],
            ["Wind load x", "D_x + E_y", f"{D_x} + {E_y} kN/m^2"],
            ["Wind load y", "D_y + E_y", f"{D_y} + {E_y} kN/m^2"],
            ["No. of wall elements", "n", f"{len(elements)}"],
        ]
    ))
    blocks.append(N(
        "Assumption carried over directly from the script: W_fx = D_x + E_y and W_fy = D_y + E_y. "
        "E_x is therefore not used in the resulting distribution."
    ))

    i_sub_n = []
    i_sub_w = []
    i_n = []
    i_w = []
    for d_n, b_n, x, y in elements:
        i_n_val = b_n * d_n**3
        i_w_val = d_n * b_n**3
        i_sub_n.append(i_n_val)
        i_sub_w.append(i_w_val)
        i_n.append(i_n_val * x)
        i_w.append(i_w_val * y)

    sum_i_sub_n = sum(i_sub_n)
    sum_i_sub_w = sum(i_sub_w)
    x_c = sum(i_n) / sum_i_sub_n
    y_c = sum(i_w) / sum_i_sub_w

    blocks.append(S("Wall element stiffness and centroid"))
    blocks.append(TBL(
        ["Wall", "d_N/b_W [m]", "b_N [m]", "x [m]", "y [m]", "I_sub,N", "I_sub,W"],
        [
            [
                f"{i + 1}",
                f"{elements[i][0]:.3f}",
                f"{elements[i][1]:.3f}",
                f"{elements[i][2]:.3f}",
                f"{elements[i][3]:.3f}",
                f"{i_sub_n[i]:.3f}",
                f"{i_sub_w[i]:.3f}",
            ]
            for i in range(len(elements))
        ]
    ))

    @handcalc(override="long", precision=3)
    def _centroid(sum_i_n, sum_i_sub_n, sum_i_w, sum_i_sub_w):
        x_c = sum_i_n / sum_i_sub_n
        y_c = sum_i_w / sum_i_sub_w
        return x_c, y_c

    latex, (x_c_calc, y_c_calc) = _centroid(sum(i_n), sum_i_sub_n, sum(i_w), sum_i_sub_w)
    blocks.append(hc_block(latex, "Resultant centroid"))

    W_fx = D_x + E_y
    W_fy = D_y + E_y
    F_x = floor_height * W_fx
    F_y = floor_height * W_fy
    F_px = F_x * y_max
    F_py = F_y * x_max
    e_x = abs(x_c - x_max / 2.0)
    e_y = abs(y_c - y_max / 2.0)
    M_Ed_x = F_x * e_x
    M_Ed_y = F_y * e_y

    blocks.append(S("Global lateral actions"))

    @handcalc(override="long", precision=3)
    def _global_actions(floor_height, D_x, E_y, D_y, x_c, y_c, x_max, y_max):
        W_fx = D_x + E_y
        W_fy = D_y + E_y
        F_x = floor_height * W_fx
        F_y = floor_height * W_fy
        F_px = F_x * y_max
        F_py = F_y * x_max
        e_x = abs(x_c - x_max / 2.0)
        e_y = abs(y_c - y_max / 2.0)
        M_Ed_x = F_x * e_x
        M_Ed_y = F_y * e_y
        return W_fx, W_fy, F_x, F_y, F_px, F_py, e_x, e_y, M_Ed_x, M_Ed_y

    latex, _ = _global_actions(floor_height, D_x, E_y, D_y, x_c_calc, y_c_calc, x_max, y_max)
    blocks.append(hc_block(latex, "Wind resultants and eccentric moments"))

    f_list_x = []
    f_list_y = []
    a_w = []
    a_n = []
    sum_x = []
    sum_y = []

    for i in range(len(elements)):
        fx_bending = M_Ed_x * (i_sub_n[i] * x_max) / (sum_i_sub_n * x_max**2)
        fy_bending = M_Ed_y * (i_sub_w[i] * y_max) / (sum_i_sub_w * y_max**2)
        fx_shear = i_sub_w[i] * (F_py / sum_i_sub_w)
        fy_shear = i_sub_n[i] * (F_px / sum_i_sub_n)

        f_list_x.append(fx_bending)
        f_list_y.append(fy_bending)
        a_w.append(fx_shear)
        a_n.append(fy_shear)
        sum_x.append(fx_bending + fy_shear)
        sum_y.append(fy_bending + fx_shear)

    blocks.append(S("Element force distribution"))
    blocks.append(TBL(
        ["Wall", "F_bend,x [kN]", "F_shear,N [kN]", "Sum x [kN]", "F_bend,y [kN]", "F_shear,W [kN]", "Sum y [kN]"],
        [
            [
                f"{i + 1}",
                f"{f_list_x[i]:.3f}",
                f"{a_n[i]:.3f}",
                f"{sum_x[i]:.3f}",
                f"{f_list_y[i]:.3f}",
                f"{a_w[i]:.3f}",
                f"{sum_y[i]:.3f}",
            ]
            for i in range(len(elements))
        ]
    ))

    blocks.append(cc.check("Centroid eccentricity in x <= x_max/2", e_x, x_max / 2.0))
    blocks.append(cc.check("Centroid eccentricity in y <= y_max/2", e_y, y_max / 2.0))

    plot_path = _plot_masonry_plan_centroid(

        elements=elements,
        x_max=x_max,
        y_max=y_max,
        x_c=x_c,
        y_c=y_c,
        figure_path=figure_path,
    )
    blocks.append(S("Plan plot"))
    blocks.append(FIG(
        plot_path,
        figure_caption or "Wall elements in plan with resultant centroid.",
        width_mm=145,
    ))

    return blocks


def masonry_bearing_under_beam(
    label,
    N_Ed,        # beam support reaction, ULS design value  [forallpeople kN]
    a_plate,     # bearing plate dimension along beam span  [forallpeople mm]
    b_plate,     # bearing plate dimension along wall face  [forallpeople mm]
    t_leaf,      # leaf thickness                           [forallpeople mm]
    f_b,         # brick normalised compressive strength    [forallpeople MPa]
    f_m,         # mortar compressive strength              [forallpeople MPa]
    K       = 0.55,   # EN 1996-1-1 Table 3.3 (Group 1 clay, GP mortar)
    gamma_M = 2.5,    # partial factor (DA-NA, exec. class 2, category I)
):
    """Bearing check for a steel beam end on a masonry leaf.

    Load path: beam end -> steel bearing plate -> afretningslag -> masonry.
    Strength:  EN 1996-1-1 sec. 3.6.1.2 eq. 3.2
    Resistance: EN 1996-1-1 sec. 6.1.3, enhancement factor beta = 1.0 (conservative).
    """
    cc = CheckContext()
    blocks = []

    blocks.append(MH(
        "Bearing under beam end",
        f"{label}  |  EN 1996-1-1 sec. 3.6 + sec. 6.1.3",
        material="masonry",
    ))

    blocks.append(S("Configuration"))
    blocks.append(T(
        f"Beam end reaction N_Ed = {N_Ed} transferred through a steel plate "
        f"({a_plate} along span x {b_plate} across wall) bedded on an afretningslag "
        f"(mortar levelling layer). "
        f"Inner leaf: Group 1 clay units (tegl), t_leaf = {t_leaf}. "
        f"K = {K} (EN 1996-1-1 Table 3.3, Group 1 clay + GP mortar). "
        f"gamma_M = {gamma_M} (DA-NA, execution class 2, category I units). "
        f"Enhancement factor beta = 1.0 — conservative, no load spreading into wall depth."
    ))

    # ── Masonry strength ──────────────────────────────────────
    blocks.append(S("Masonry compressive strength — EN 1996-1-1 eq. 3.2"))
    blocks.append(N(
        "Exponents alpha = 0.70, beta_exp = 0.30 (Table 3.3). "
        "alpha + beta_exp = 1.0, so f_k has the same units as f_b and f_m."
    ))

    @handcalc(override="long", precision=3)
    def _fk(K, f_b, f_m, gamma_M):
        f_k = K * f_b ** 0.70 * f_m ** 0.30   # characteristic compressive strength
        f_d = f_k / gamma_M                     # design compressive strength
        return f_k, f_d

    latex, (_, f_d) = _fk(K, f_b, f_m, gamma_M)
    blocks.append(hc_block(latex, "Masonry characteristic and design strength"))

    # ── Bearing resistance ────────────────────────────────────
    blocks.append(S("Bearing resistance — EN 1996-1-1 sec. 6.1.3"))

    b_ef = min(b_plate, t_leaf)
    blocks.append(N(
        f"Effective bearing width b_ef = min(b_plate, t_leaf) "
        f"= min({b_plate}, {t_leaf}) = {b_ef}."
    ))

    @handcalc(override="long", precision=3)
    def _nb(a_plate, b_ef, f_d):
        A_b  = a_plate * b_ef    # effective bearing area
        N_Rd = A_b * f_d         # design bearing resistance
        return A_b, N_Rd

    latex, (_, N_Rd) = _nb(a_plate, b_ef, f_d)
    blocks.append(hc_block(latex, "Effective bearing area and resistance"))
    blocks.append(cc.check("Masonry bearing — EN 1996-1-1 sec. 6.1.3", N_Ed, N_Rd))

    return blocks


def masonry_wall_ritter(
    label,
    b,           # wall tributary width   [forallpeople, e.g. 1.0*m]
    t_ef,        # effective thickness     [forallpeople, e.g. 150*mm]
    h_ef,        # effective height        [forallpeople, e.g. 2700*mm]
    e_m,         # midheight eccentricity  [forallpeople, e.g. 10*mm]
    N_Ed,        # design axial force ULS  [forallpeople, e.g. 80*kN]
    f_b,         # unit norm. comp. str.   [forallpeople, e.g. 10*MPa]
    f_m,         # mortar comp. strength   [forallpeople, e.g. 4*MPa]
    K      = 0.55,   # EN 1996-1-1 Table 3.3
    gamma_M = 2.5,   # partial factor
    K1     = 0.9,    # long-term factor K_1
):
    """Single masonry wall — vertical resistance by the Ritter method.

    N_Rd = K_1 * K_2 * A * f_d
    K_2  = 1 / (1 + 12/K_2^2 * (h_ef/(t_ef-2*e_m))^2)  [iterated to convergence]
    A    = b * (t_ef - 2*e_m)
    """
    cc = CheckContext()
    blocks = []

    blocks.append(MH(
        "Masonry wall — Ritter",
        f"{label}  |  EN 1996-1-1 — Ritter capacity check",
        material="masonry",
    ))

    blocks.append(S("Design parameters"))
    blocks.append(TBL(
        ["Property", "Symbol", "Value"],
        [
            ["Wall width (tributary)", "b",        str(b)],
            ["Effective thickness",    "t_ef",     str(t_ef)],
            ["Effective height",       "h_ef",     str(h_ef)],
            ["Midheight eccentricity", "e_m",      str(e_m)],
            ["Design axial force",     "N_Ed",     str(N_Ed)],
            ["Unit comp. strength",    "f_b",      str(f_b)],
            ["Mortar strength",        "f_m",      str(f_m)],
            ["Constant K (Table 3.3)", "K",        str(K)],
            ["Partial factor",         "gamma_M",  str(gamma_M)],
            ["Long-term factor",       "K_1",      str(K1)],
        ]
    ))

    # --- 1. Masonry characteristic and design strength ---
    blocks.append(S("Characteristic compressive strength — EN 1996-1-1 eq. 3.2"))

    @handcalc(override="long", precision=3)
    def _fk(K, f_b, f_m, gamma_M):
        f_k = K * f_b**0.70 * f_m**0.30   # characteristic compressive strength
        f_d = f_k / gamma_M                 # design compressive strength
        return f_k, f_d

    latex, (f_k, f_d) = _fk(K, f_b, f_m, gamma_M)
    blocks.append(hc_block(latex, "Masonry strength"))

    # --- 2. Effective cross-section ---
    blocks.append(S("Effective cross-section — A = b * (t_ef - 2*e_m)"))

    @handcalc(override="long", precision=3)
    def _area(b, t_ef, e_m):
        t_red = t_ef - 2.0 * e_m   # reduced thickness
        A = b * t_red               # effective cross-sectional area
        return t_red, A

    latex_area, (t_red, A_eff) = _area(b, t_ef, e_m)
    blocks.append(hc_block(latex_area, "Effective area"))

    # Guard against invalid eccentricity
    try:
        t_red_m = float(t_red.to(m))
    except Exception:
        t_red_m = float(t_red) / 1000.0   # assume mm input

    if t_red_m <= 0.0:
        blocks.append(N(
            "ERROR: t_ef - 2*e_m <= 0. "
            "The midheight eccentricity exceeds half the wall thickness — geometry invalid."
        ))
        return blocks

    try:
        h_ef_m = float(h_ef.to(m))
    except Exception:
        h_ef_m = float(h_ef) / 1000.0   # assume mm input

    # --- 3. Slenderness ratio ---
    blocks.append(S("Slenderness ratio"))

    @handcalc(override="long", precision=3)
    def _lam(h_ef, t_red):
        lam_ef = h_ef / t_red   # effective slenderness ratio
        return lam_ef

    latex_lam, _ = _lam(h_ef, t_red)
    lam = h_ef_m / t_red_m   # plain float for iteration
    blocks.append(hc_block(latex_lam, f"Slenderness = {lam:.3f}"))

    # --- 4. Ritter K_2 — iterative ---
    blocks.append(S("Ritter reduction factor K_2"))
    blocks.append(N(
        "K_2 is solved iteratively from: K_2 = 1 / (1 + 12/K_2^2 * lam_ef^2). "
        "Iteration starts at K_2 = 1.0 and converges typically within 20 steps."
    ))

    K2 = 1.0
    for _ in range(100):
        K2_new = 1.0 / (1.0 + 12.0 / K2**2 * lam**2)
        if abs(K2_new - K2) < 1e-8:
            K2 = K2_new
            break
        K2 = K2_new

    @handcalc(override="long", precision=4)
    def _k2(K2, lam):
        K2_converged = 1.0 / (1.0 + 12.0 / K2**2 * lam**2)   # Ritter reduction factor
        return K2_converged

    latex_k2, _ = _k2(K2, lam)
    blocks.append(hc_block(latex_k2, f"K_2 = {K2:.4f} (converged)"))

    # --- 5. Design resistance ---
    blocks.append(S("Design resistance — N_Rd = K_1 * K_2 * A * f_d"))

    @handcalc(override="long", precision=3)
    def _nrd(K1, K2, A_eff, f_d):
        N_Rd = K1 * K2 * A_eff * f_d   # design resistance
        return N_Rd

    latex_nr, N_Rd = _nrd(K1, K2, A_eff, f_d)
    blocks.append(hc_block(latex_nr, "Ritter design resistance"))

    blocks.append(cc.check("Vertical load — Ritter: N_Ed / N_Rd", N_Ed, N_Rd))

    return blocks
