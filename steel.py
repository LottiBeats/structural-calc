"""
steel.py - Steel beam module (EN 1993-1-1)
Unit-aware with forallpeople. No manual conversions.

Closed-form and FEM/imported-action workflow:
- default: calculate M_Ed and V_Ed from wL^2/8 and wL/2
- optional: pass beam_results with imported M_Ed / V_Ed / delta values
"""

from math import pi

from handcalcs.decorator import handcalc
import forallpeople as si
si.environment('structural', top_level=True)

from calc_core import hc_block, S, T, N, TBL, MH, CheckContext, FIG


def steel_beam_ipe(
    label,
    section,
    span,
    g_k,
    q_k,
    W_ply,
    h,
    t_w,
    f_y=None,
    gamma_M0=1.0,
    beam_results=None,
    figure_path=None,
    figure_caption="",
    # Section dimensions needed for LTB — pass from the section catalog
    b=None,          # flange width  [m or mm as forallpeople qty]
    t_f=None,        # flange thickness [m or mm]
    # LTB parameters
    l_cr_ltb=None,   # effective LTB length [m]; None → check skipped
    C1=1.0,          # equivalent uniform moment factor (1.0 = conservative)
    gamma_M1=1.0,    # partial factor for member stability (EN 1993-1-1)
    # Restraint flags — set True when the mode is prevented by restraints
    ltb_restrained=False,
    buck_y_restrained=False,
    buck_x_restrained=False,
):
    if f_y is None:
        f_y = 355 * MPa

    cc = CheckContext()
    blocks = []

    blocks.append(MH(f"Steel beam - {section}",
                     f"{label}  |  EN 1993-1-1", material="steel"))

    blocks.append(S("Design parameters"))
    blocks.append(T(
        f"Simply supported {section}, span {span}. "
        f"Steel grade S{float(f_y / MPa):.0f}. Loads per EN 1990/EN 1991-1-1."
    ))
    _dim_rows = [
        ["Section",           "-",       section],
        ["Span",              "L",       str(span)],
        ["Permanent load",    "g_k",     str(g_k)],
        ["Variable load",     "q_k",     str(q_k)],
        ["Plastic modulus",   "W_pl,y",  str(W_ply)],
        ["Height",            "h",       str(h)],
        ["Web thickness",     "t_w",     str(t_w)],
        ["Yield strength",    "f_y",     str(f_y)],
        ["γ_M0",              "γ_M0",    str(gamma_M0)],
        ["γ_M1",              "γ_M1",    str(gamma_M1)],
    ]
    if b is not None:
        _dim_rows.insert(6, ["Flange width",     "b",    str(b)])
    if t_f is not None:
        _dim_rows.insert(7, ["Flange thickness", "t_f",  str(t_f)])
    if l_cr_ltb is not None and not ltb_restrained:
        _dim_rows.append(["Eff. LTB length",  "L_cr",  str(l_cr_ltb)])
        _dim_rows.append(["Moment factor",    "C₁",    str(C1)])
    blocks.append(TBL(["Property", "Symbol", "Value"], _dim_rows))

    if beam_results is None:
        blocks.append(S("ULS loading"))

        @handcalc(override="long", precision=2)
        def _uls(g_k, q_k):
            w_Ed = 1.35 * g_k + 1.5 * q_k
            return w_Ed

        latex, w_Ed = _uls(g_k, q_k)
        blocks.append(hc_block(latex, "ULS design load w_Ed"))

        blocks.append(S("Design actions"))

        @handcalc(override="long", precision=2)
        def _actions(w_Ed, L):
            M_Ed = (w_Ed * L**2) / 8
            V_Ed = (w_Ed * L) / 2
            return M_Ed, V_Ed

        latex, (M_Ed, V_Ed) = _actions(w_Ed, span)
        blocks.append(hc_block(latex, "Design moment and shear"))
        blocks.append(N("Closed-form actions used: simply supported beam under full-span UDL."))
    else:
        blocks.append(S("Imported beam analysis actions"))
        source = beam_results.get("source", "Beam analysis")
        case_name = beam_results.get("case_name", "")
        if case_name:
            blocks.append(T(f"Moment and shear imported from {source}: {case_name}."))
        else:
            blocks.append(T(f"Moment and shear imported from {source}."))

        M_Ed = beam_results["M_Ed"]
        V_Ed = beam_results["V_Ed"]

        @handcalc(override="long", precision=2)
        def _import_actions(M_input, V_input):
            M_Ed = M_input
            V_Ed = V_input
            return M_Ed, V_Ed

        latex, (M_Ed, V_Ed) = _import_actions(M_Ed, V_Ed)
        blocks.append(hc_block(latex, "Imported design actions"))

        delta_max = beam_results.get("delta_max")
        if delta_max is not None:
            @handcalc(override="long", precision=2)
            def _import_deflection(delta_input):
                delta_max = delta_input
                return delta_max

            latex, delta_max = _import_deflection(delta_max)
            blocks.append(hc_block(latex, "Imported maximum deflection"))

    if figure_path:
        blocks.append(S("Beam analysis diagram"))
        blocks.append(FIG(figure_path, figure_caption or "Moment, shear and deflection overlays from beam analysis."))

    blocks.append(S("Bending resistance - EN 1993-1-1 cl. 6.2.5"))

    @handcalc(override="long", precision=2)
    def _bend(W_ply, f_y, gamma_M0):
        M_Rk = W_ply * f_y
        M_Rd = M_Rk / gamma_M0
        return M_Rk, M_Rd

    latex, (M_Rk, M_Rd) = _bend(W_ply, f_y, gamma_M0)
    blocks.append(hc_block(latex, "Plastic moment resistance"))
    blocks.append(cc.check("Bending check: M_Ed / M_Rd", M_Ed, M_Rd))

    blocks.append(S("Shear resistance - EN 1993-1-1 cl. 6.2.6"))

    @handcalc(override="long", precision=2)
    def _shear(V_Ed, h, t_w, f_y, gamma_M0):
        A_v = h * t_w
        V_Rk = A_v * f_y / 3**0.5
        V_Rd = V_Rk / gamma_M0
        return V_Rd

    latex, V_Rd = _shear(V_Ed, h, t_w, f_y, gamma_M0)
    blocks.append(hc_block(latex, "Shear resistance"))
    blocks.append(cc.check("Shear check: V_Ed / V_Rd", V_Ed, V_Rd))

    # ── Lateral-torsional buckling (LTB) — EN 1993-1-1 cl. 6.3.2 ───────────
    blocks.append(S("Lateral-torsional buckling — EN 1993-1-1 cl. 6.3.2"))

    if ltb_restrained:
        blocks.append(N(
            "The compression flange (bottom) is assumed continuously restrained against "
            "lateral displacement — e.g. by a floor slab, decking, or closely-spaced "
            "purlins. Lateral-torsional buckling is not governing. "
            "χ_LT = 1.0 — no reduction to bending resistance is required."
        ))

    elif b is not None and t_f is not None and l_cr_ltb is not None:
        # ── Full LTB check — general case, cl. 6.3.2.2 ──────────────────────
        E_s = 210_000 * MPa   # elastic modulus for steel
        G_s =  80_770 * MPa   # shear modulus  G = E / (2(1+0.3))

        blocks.append(T(
            "General case per EN 1993-1-1 cl. 6.3.2.2. "
            f"Effective LTB length L_cr = {l_cr_ltb}. "
            f"Equivalent uniform moment factor C₁ = {C1} "
            "(1.0 = uniform moment, conservative; "
            "≈ 1.13 triangular moment, ≈ 1.29 parabolic / UDL). "
            "Section constants I_z, I_w, I_t derived from nominal I-section geometry "
            "(fillets neglected — conservative)."
        ))

        @handcalc(override="long", precision=4)
        def _ltb_props(b, h, t_w, t_f):
            I_z = t_f * b**3 / 6 + (h - 2*t_f) * t_w**3 / 12
            I_w = b**3 * t_f * (h - t_f)**2 / 24
            I_t = (2*b*t_f**3 + (h - 2*t_f)*t_w**3) / 3
            return I_z, I_w, I_t

        latex, (I_z, I_w, I_t) = _ltb_props(b, h, t_w, t_f)
        blocks.append(hc_block(
            latex,
            "Weak-axis second moment I_z, warping constant I_w, torsional constant I_t"
        ))

        @handcalc(override="long", precision=3)
        def _Mcr(C1, l_cr_ltb, E_s, G_s, I_z, I_w, I_t):
            N_Ez = pi * pi * E_s * I_z / l_cr_ltb**2
            W_LT = (I_w/I_z + l_cr_ltb**2 * G_s * I_t / (pi * pi * E_s * I_z))**0.5
            M_cr = C1 * N_Ez * W_LT
            return N_Ez, W_LT, M_cr

        latex, (N_Ez, W_LT, M_cr) = _Mcr(C1, l_cr_ltb, E_s, G_s, I_z, I_w, I_t)
        blocks.append(hc_block(
            latex,
            "Elastic critical moment M_cr — N_Ez = pi2*EI_z/L_cr2, W_LT = sqrt(I_w/I_z + L_cr2*G*I_t/pi2*EI_z)"
        ))

        @handcalc(override="long", precision=3)
        def _lambda_LT(W_ply, f_y, M_cr):
            lambda_bar_LT = (W_ply * f_y / M_cr)**0.5
            return lambda_bar_LT

        latex, lambda_bar_LT = _lambda_LT(W_ply, f_y, M_cr)
        blocks.append(hc_block(latex, "Non-dimensional slenderness λ̄_LT"))

        # Buckling curve for rolled I-sections — EN 1993-1-1 Table 6.5
        h_over_b = float(h) / float(b)
        if h_over_b <= 2.0:
            alpha_LT  = 0.34   # curve b
            curve_ltb = "b"
        else:
            alpha_LT  = 0.49   # curve c
            curve_ltb = "c"

        lbar = float(lambda_bar_LT)

        if lbar <= 0.2:
            chi_LT = 1.0
            blocks.append(N(
                f"Non-dimensional slenderness λ̄_LT = {lbar:.3f} ≤ 0.2: "
                "LTB is not critical. χ_LT = 1.0."
            ))
        else:
            @handcalc(override="long", precision=3)
            def _chi_LT(alpha_LT, lbar):
                phi_LT = 0.5 * (1 + alpha_LT * (lbar - 0.2) + lbar**2)
                chi_LT = 1 / (phi_LT + (phi_LT**2 - lbar**2)**0.5)
                return phi_LT, chi_LT

            latex, (phi_LT, chi_LT_raw) = _chi_LT(alpha_LT, lbar)
            chi_LT = min(float(chi_LT_raw), 1.0)
            blocks.append(hc_block(
                latex,
                f"φ_LT and χ_LT — buckling curve {curve_ltb} "
                f"(α_LT = {alpha_LT}, h/b = {h_over_b:.2f})"
            ))

        @handcalc(override="long", precision=2)
        def _Mb_Rd(chi_LT, W_ply, f_y, gamma_M1):
            M_b_Rd = chi_LT * W_ply * f_y / gamma_M1
            return M_b_Rd

        latex, M_b_Rd = _Mb_Rd(chi_LT, W_ply, f_y, gamma_M1)
        blocks.append(hc_block(latex, "LTB design buckling resistance M_b,Rd"))
        blocks.append(cc.check("LTB check: M_Ed / M_b,Rd", M_Ed, M_b_Rd))

    else:
        blocks.append(N(
            "LTB has NOT been verified. Enter the effective LTB length (span between "
            "lateral restraints to the compression flange) in the block settings to "
            "enable the full cl. 6.3.2.2 check. Alternatively tick 'Restrained — LTB' "
            "if continuous restraint is provided. Note: for L-profiles (angle sections) "
            "LTB should be checked using specialist tables or software."
        ))

    # ── Out-of-plane stability — y-axis ──────────────────────────────────────
    blocks.append(S("Out-of-plane stability — y-axis"))
    if buck_y_restrained:
        blocks.append(N(
            "The beam is assumed restrained against lateral (out-of-plane) displacement "
            "about the y-axis — e.g. by secondary beams, bracing, or a rigid floor "
            "diaphragm framing into the web. Buckling about the y-axis is not governing."
        ))
    else:
        blocks.append(N(
            "y-axis stability has NOT been verified. If the beam is unbraced laterally, "
            "confirm that adequate restraint against out-of-plane movement is provided, "
            "or carry out a separate buckling check. Tick 'Restrained — y-axis' in the "
            "block settings to document that restraint is present."
        ))

    # ── In-plane stability — x-axis ───────────────────────────────────────────
    blocks.append(S("In-plane stability — x-axis"))
    if buck_x_restrained:
        blocks.append(N(
            "The beam is assumed restrained against displacement in the plane of bending "
            "(x-axis). Supports and loading configuration prevent buckling in the vertical "
            "plane. Buckling about the x-axis is not governing."
        ))
    else:
        blocks.append(N(
            "x-axis stability has NOT been verified. Confirm that the support conditions "
            "prevent in-plane instability (e.g. snap-through or arch action under reversed "
            "curvature). Tick 'Restrained — x-axis' in the block settings to document "
            "that restraint is present."
        ))

    return blocks

