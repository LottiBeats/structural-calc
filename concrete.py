"""
concrete.py - RC beam module (EN 1992-1-1)
Unit-aware with forallpeople. No manual conversions.

Closed-form and FEM/imported-action workflow:
- default: calculate M_Ed from wL^2/8
- optional: pass beam_results with imported M_Ed / V_Ed / delta values
"""

from handcalcs.decorator import handcalc
import forallpeople as si
si.environment('structural', top_level=True)

from calc_core import hc_block, S, T, N, MH, CheckContext, FIG


def rc_beam_bending(
    label,
    span,
    g_k,
    q_k,
    b,
    h,
    d,
    f_ck=None,
    f_yk=None,
    As_prov=None,
    gamma_C=1.5,
    gamma_S=1.15,
    beam_results=None,
    figure_path=None,
    figure_caption="",
):
    if f_ck is None:
        f_ck = 30 * MPa
    if f_yk is None:
        f_yk = 500 * MPa

    cc = CheckContext()
    blocks = []

    blocks.append(MH(f"RC beam - {b}x{h}",
                     f"{label}  |  EN 1992-1-1", material="concrete"))

    blocks.append(S("Design parameters"))
    blocks.append(T(
        f"Simply supported RC beam {b}x{h}, effective depth d = {d}. "
        f"Concrete C{float(f_ck / MPa):.0f}/37, reinforcement B500B. Span = {span}."
    ))

    if beam_results is None:
        blocks.append(S("ULS loading and design moment"))

        @handcalc(override="long", precision=2)
        def _uls(g_k, q_k, L):
            w_Ed = 1.35 * g_k + 1.5 * q_k
            M_Ed = (w_Ed * L**2) / 8
            V_Ed = (w_Ed * L) / 2
            return w_Ed, M_Ed, V_Ed

        latex, (w_Ed, M_Ed, V_Ed) = _uls(g_k, q_k, span)
        blocks.append(hc_block(latex, "ULS load, moment and shear"))
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
        V_Ed = beam_results.get("V_Ed")

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

    blocks.append(S("Material design strengths"))

    @handcalc(override="long", precision=2)
    def _strengths(f_ck, f_yk, gamma_C, gamma_S):
        f_cd = (0.85 * f_ck) / gamma_C
        f_yd = f_yk / gamma_S
        return f_cd, f_yd

    latex, (f_cd, f_yd) = _strengths(f_ck, f_yk, gamma_C, gamma_S)
    blocks.append(hc_block(latex, "Design strengths"))

    blocks.append(S("Required reinforcement area"))

    @handcalc(override="long", precision=2)
    def _steel(M_Ed, f_yd, d):
        z = 0.9 * d
        As_req = M_Ed / (f_yd * z)
        return z, As_req

    latex, (z, As_req) = _steel(M_Ed, f_yd, d)
    blocks.append(hc_block(latex, "Required steel area"))
    blocks.append(N("z = 0.9d is a conservative estimate. Verify with iterative z per EN 1992 cl. 6.1 for final design."))

    blocks.append(S("Minimum reinforcement - EN 1992-1-1 cl. 9.2.1.1"))

    @handcalc(override="long", precision=3)
    def _asmin_terms(f_ck, f_yk, b, d):
        f_ctm = 0.3 * (f_ck / MPa)**(2/3) * MPa
        rho_min_1 = 0.26 * (f_ctm / f_yk)
        As_min_1 = rho_min_1 * (b / mm) * (d / mm) * mm**2
        As_min_2 = 0.0013 * (b / mm) * (d / mm) * mm**2
        return f_ctm, rho_min_1, As_min_1, As_min_2

    latex, (f_ctm, rho_min_1, As_min_1, As_min_2) = _asmin_terms(f_ck, f_yk, b, d)
    blocks.append(hc_block(latex, "Minimum reinforcement terms"))

    As_min = As_min_1 if float(As_min_1 / As_min_2) >= 1.0 else As_min_2

    @handcalc(override="long", precision=2)
    def _asmin_selected(As_input):
        As_min = As_input
        return As_min

    latex, As_min = _asmin_selected(As_min)
    blocks.append(hc_block(latex, "Adopted minimum reinforcement"))
    if float(As_min_1 / As_min_2) >= 1.0:
        blocks.append(N("As_min governed by 0.26 f_ctm / f_yk * b * d."))
    else:
        blocks.append(N("As_min governed by 0.0013 * b * d."))

    if As_prov is not None:
        blocks.append(S("Reinforcement provided"))
        blocks.append(cc.check("As,prov >= As,req", As_req, As_prov))
        blocks.append(cc.check("As,prov >= As,min", As_min, As_prov))

    if V_Ed is not None:
        blocks.append(S("Imported shear action"))
        @handcalc(override="long", precision=2)
        def _shear_action(V_input):
            V_Ed = V_input
            return V_Ed
        latex, V_Ed = _shear_action(V_Ed)
        blocks.append(hc_block(latex, "Design shear action available for shear checks"))

    return blocks
