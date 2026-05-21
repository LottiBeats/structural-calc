"""
timber.py - Timber beam module (EN 1995-1-1)
Unit-aware with forallpeople. No manual conversions.

Closed-form and FEM/imported-action workflow:
- default: calculate M_Ed and V_Ed from wL^2/8 and wL/2
- optional: pass beam_results with imported M_Ed / V_Ed / delta values
"""

from handcalcs.decorator import handcalc
import forallpeople as si
si.environment('structural', top_level=True)

from calc_core import hc_block, S, T, N, TBL, MH, CheckContext, FIG
from timber_grades import get_timber_grade

KMOD = {
    (1, "permanent"): 0.60, (1, "long"): 0.70, (1, "medium"): 0.80,
    (1, "short"): 0.90,     (1, "instant"): 1.10,
    (2, "permanent"): 0.60, (2, "long"): 0.70, (2, "medium"): 0.80,
    (2, "short"): 0.90,     (2, "instant"): 1.10,
    (3, "permanent"): 0.50, (3, "long"): 0.55, (3, "medium"): 0.65,
    (3, "short"): 0.70,     (3, "instant"): 0.90,
}


def timber_beam(
    label,
    span,
    g_k,
    q_k,
    b,
    h,
    timber_grade=None,
    f_mk=None,
    f_vk=None,
    E_0_05=None,
    service_class=1,
    load_duration="medium",
    gamma_M=1.3,
    beam_results=None,
    fire_design=None,
    l_ef=None,
    compression_edge_restrained=False,
    torsional_restraint_at_supports=True,
    support_length=None,
    bearing_force=None,
    f_c_90_k=None,
    k_c_90=None,
    support_material="solid_timber",
    load_near_support=False,
    end_distance=None,
    figure_path=None,
    figure_caption="",
):
    grade_key = None
    grade_data = None
    if timber_grade is not None:
        grade_key, grade_data = get_timber_grade(timber_grade)

    if f_mk is None and grade_data is not None:
        f_mk = grade_data["f_mk"]
    if f_mk is None:
        f_mk = 24 * MPa
    if f_vk is None and grade_data is not None:
        f_vk = grade_data["f_vk"]
    if f_vk is None:
        f_vk = 4.0 * MPa
    if E_0_05 is None and grade_data is not None:
        E_0_05 = grade_data["E_0_05"]
    if E_0_05 is None:
        E_0_05 = 7_400 * MPa
    if f_c_90_k is None and grade_data is not None:
        f_c_90_k = grade_data["f_c_90_k"]
    if f_c_90_k is None:
        f_c_90_k = 2.5 * MPa
    if support_material == "solid_timber" and grade_data is not None:
        support_material = grade_data["support_material"]

    kmod = KMOD.get((service_class, load_duration), 0.80)
    cc = CheckContext()
    blocks = []

    blocks.append(MH(f"Timber beam - {b}x{h}",
                     f"{label}  |  EN 1995-1-1", material="timber"))

    blocks.append(S("Design parameters"))
    blocks.append(T(
        f"Simply supported {(grade_data['description'] if grade_data is not None else 'C24 solid timber')} beam, span {span}. "
        f"Service class {service_class}, load duration: {load_duration}. "
        f"k_mod = {kmod}, gamma_M = {gamma_M}."
    ))

    blocks.append(TBL(
        ["Property", "Symbol", "Value"],
        [
            ["Span", "L", str(span)],
            ["Permanent load", "g_k", str(g_k)],
            ["Variable load", "q_k", str(q_k)],
            ["Width", "b", str(b)],
            ["Depth", "h", str(h)],
            ["Timber grade", "-", grade_key if grade_key is not None else "manual"],
            ["Bending strength", "f_m,k", str(f_mk)],
            ["Shear strength", "f_v,k", str(f_vk)],
            ["5-percentile modulus", "E_0,05", str(E_0_05)],
            ["Bearing strength perp. grain", "f_c,90,k", str(f_c_90_k)],
        ]
    ))

    if beam_results is None:
        blocks.append(S("ULS loading"))

        @handcalc(override="long", precision=2)
        def _uls(g_k, q_k):
            w_Ed = 1.35 * g_k + 1.5 * q_k
            return w_Ed

        latex, w_Ed = _uls(g_k, q_k)
        blocks.append(hc_block(latex, "ULS design load"))

        @handcalc(override="long", precision=2)
        def _forces(w_Ed, L):
            M_Ed = (w_Ed * L**2) / 8
            V_Ed = (w_Ed * L) / 2
            return M_Ed, V_Ed

        latex, (M_Ed, V_Ed) = _forces(w_Ed, span)
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

        x_M = beam_results.get("x_M_Ed")
        x_V = beam_results.get("x_V_Ed")
        loc_parts = []
        if x_M is not None:
            loc_parts.append(f"|M| max at x = {x_M}")
        if x_V is not None:
            loc_parts.append(f"|V| max at x = {x_V}")
        if loc_parts:
            blocks.append(N(" ; ".join(loc_parts)))

    if figure_path:
        blocks.append(S("Beam analysis diagram"))
        blocks.append(FIG(figure_path, figure_caption or "Moment, shear and deflection overlays from beam analysis."))

    blocks.append(S("Bending resistance - EN 1995-1-1 cl. 6.1.6"))

    @handcalc(override="long", precision=2)
    def _bend(b, h, f_mk, kmod, gamma_M):
        W_y = (b * h**2) / 6
        f_md = kmod * f_mk / gamma_M
        return W_y, f_md

    latex, (W_y, f_md) = _bend(b, h, f_mk, kmod, gamma_M)
    blocks.append(hc_block(latex, "Section modulus and design strength"))

    @handcalc(override="long", precision=2)
    def _bend_check(M_Ed, W_y):
        sigma_md = M_Ed / W_y
        return sigma_md

    latex, sigma_md = _bend_check(M_Ed, W_y)
    blocks.append(hc_block(latex, "Design bending stress"))
    blocks.append(cc.check("Bending: sigma_m,d / f_m,d", sigma_md, f_md))

    blocks.append(S("Lateral buckling / kipning - EN 1995-1-1 cl. 6.3.3"))

    if compression_edge_restrained and torsional_restraint_at_supports:
        k_crit = 1.0
        blocks.append(N(
            "Compression edge is assumed restrained throughout the beam length and torsional rotation is prevented at supports. "
            "Therefore k_crit = 1.0 and lateral buckling is neglected."
        ))
    else:
        if l_ef is None:
            l_ef = span + 0.2 * h
            blocks.append(N(
                "No effective buckling length was provided. "
                "Using l_ef = L + 0.2h as a practical assumption for a simply supported rectangular beam."
            ))
        else:
            blocks.append(N(f"Effective buckling length for kipning provided as l_ef = {l_ef}."))

        @handcalc(override="long", precision=2)
        def _buckling(b, h, E_0_05, l_ef, f_mk):
            sigma_m_crit = 0.78 * E_0_05 * b**2 / (h * l_ef)
            lambda_rel_m = (f_mk / sigma_m_crit) ** 0.5
            return sigma_m_crit, lambda_rel_m

        latex, (sigma_m_crit, lambda_rel_m) = _buckling(b, h, E_0_05, l_ef, f_mk)
        blocks.append(hc_block(latex, "sigma_m,crit and lambda_rel,m"))

        @handcalc(override="long", precision=3)
        def _kcrit_low():
            k_crit = 1.0
            return k_crit

        @handcalc(override="long", precision=3)
        def _kcrit_mid(lambda_rel_m):
            k_crit = 1.56 - 0.75 * lambda_rel_m
            return k_crit

        @handcalc(override="long", precision=3)
        def _kcrit_high(lambda_rel_m):
            k_crit = 1 / (lambda_rel_m**2)
            return k_crit

        lambda_rel_m_value = float(lambda_rel_m)
        if lambda_rel_m_value <= 0.75:
            latex, k_crit = _kcrit_low()
            blocks.append(hc_block(latex, "k_crit"))
        elif lambda_rel_m_value <= 1.4:
            latex, k_crit = _kcrit_mid(lambda_rel_m)
            blocks.append(hc_block(latex, "k_crit"))
        else:
            latex, k_crit = _kcrit_high(lambda_rel_m)
            blocks.append(hc_block(latex, "k_crit"))

    blocks.append(cc.check("Kipning: sigma_m,d / (k_crit f_m,d)", sigma_md, k_crit * f_md))

    blocks.append(S("Shear resistance - EN 1995-1-1 cl. 6.1.7"))

    @handcalc(override="long", precision=2)
    def _shear(V_Ed, b, h, f_vk, kmod, gamma_M):
        A = b * h
        f_vd = kmod * f_vk / gamma_M
        tau_d = (1.5 * V_Ed) / A
        return f_vd, tau_d

    latex, (f_vd, tau_d) = _shear(V_Ed, b, h, f_vk, kmod, gamma_M)
    blocks.append(hc_block(latex, "Design shear stress"))
    blocks.append(cc.check("Shear: tau_d / f_v,d", tau_d, f_vd))

    if support_length is not None:
        blocks.append(S("Bearing at support / vederlag - EN 1995-1-1 cl. 6.1.5"))

        if bearing_force is None:
            bearing_force = V_Ed
            blocks.append(N(
                "No bearing force was provided, so the support reaction is approximated from V_Ed."
            ))
        else:
            blocks.append(N(f"Bearing force provided as F_c,90,Ed = {bearing_force}."))

        if k_c_90 is None:
            if load_near_support:
                k_c_90 = 1.0
                blocks.append(N(
                    "Load is assumed to act close to the support, so k_c,90 = 1.0 is used."
                ))
            else:
                k_c_90 = 1.75 if support_material == "glulam" else 1.5
                blocks.append(N(
                    f"Limited support assumed with load applied away from the support; "
                    f"k_c,90 = {k_c_90} is used for {support_material}."
                ))
        else:
            blocks.append(N(f"Bearing factor provided as k_c,90 = {k_c_90}."))

        if end_distance is None:
            add_length = 30 * mm
            blocks.append(N(
                "No end distance was provided. Using A_ef = b (l + 30 mm) for a limited support."
            ))
        elif end_distance >= 30 * mm:
            add_length = 60 * mm
            blocks.append(N(
                "End distance a >= 30 mm, so A_ef = b (l + 60 mm) is used."
            ))
        else:
            add_length = 30 * mm
            blocks.append(N(
                "End distance a < 30 mm, so A_ef = b (l + 30 mm) is used."
            ))

        @handcalc(override="long", precision=2)
        def _bearing_strength(kmod, f_c_90_k, gamma_M, b, support_length, add_length):
            f_c_90_d = kmod * f_c_90_k / gamma_M
            A_ef = b * (support_length + add_length)
            return f_c_90_d, A_ef

        latex, (f_c_90_d, A_ef) = _bearing_strength(
            kmod, f_c_90_k, gamma_M, b, support_length, add_length
        )
        blocks.append(hc_block(latex, "Bearing design strength and effective area"))

        @handcalc(override="long", precision=2)
        def _bearing_check(bearing_force, A_ef, k_c_90, f_c_90_d):
            sigma_c_90_d = bearing_force / A_ef
            F_c_90_Rd = k_c_90 * f_c_90_d * A_ef
            return sigma_c_90_d, F_c_90_Rd

        latex, (sigma_c_90_d, F_c_90_Rd) = _bearing_check(
            bearing_force, A_ef, k_c_90, f_c_90_d
        )
        blocks.append(hc_block(latex, "Bearing stress and resistance"))
        blocks.append(cc.check("Bearing: sigma_c,90,d / (k_c,90 f_c,90,d)", sigma_c_90_d, k_c_90 * f_c_90_d))
        blocks.append(cc.check("Bearing: F_c,90,Ed / F_c,90,Rd", bearing_force, F_c_90_Rd))

    if fire_design:
        blocks.append(S("Brand - EN 1995-1-2"))

        t_fire = fire_design["t_fire"]
        beta_n = fire_design.get("beta_n", 0.7 * mm)
        d0 = fire_design.get("d0", 7 * mm)
        k0 = fire_design.get("k0", 1.0)
        gamma_M_fi = fire_design.get("gamma_M_fi", 1.0)
        kmod_fi = fire_design.get("kmod_fi", 1.0)
        exposed_sides = int(fire_design.get("exposed_sides", 2))
        exposed_bottom = bool(fire_design.get("exposed_bottom", True))
        exposed_top = bool(fire_design.get("exposed_top", False))

        M_Ed_fi = fire_design.get("M_Ed")
        V_Ed_fi = fire_design.get("V_Ed")
        eta_fi = fire_design.get("eta_fi")

        if eta_fi is not None:
            if M_Ed_fi is None:
                M_Ed_fi = eta_fi * M_Ed
            if V_Ed_fi is None:
                V_Ed_fi = eta_fi * V_Ed

        if M_Ed_fi is None or V_Ed_fi is None:
            raise ValueError("fire_design requires M_Ed and V_Ed, or eta_fi to derive them.")

        blocks.append(T(
            f"Reduced cross-section method for standard fire exposure. "
            f"Requested fire duration = {t_fire}. "
            f"Exposed sides = {exposed_sides}, bottom exposed = {exposed_bottom}, top exposed = {exposed_top}."
        ))

        blocks.append(TBL(
            ["Property", "Symbol", "Value"],
            [
                ["Fire duration", "t_fi", str(t_fire)],
                ["Notional charring rate", "beta_n", str(beta_n)],
                ["Zero-strength layer", "d_0", str(d0)],
                ["Fire moment", "M_Ed,fi", str(M_Ed_fi)],
                ["Fire shear", "V_Ed,fi", str(V_Ed_fi)],
                ["k_mod in fire", "k_mod,fi", str(kmod_fi)],
                ["gamma_M in fire", "gamma_M,fi", str(gamma_M_fi)],
            ]
        ))

        @handcalc(override="long", precision=2)
        def _fire_depth(beta_n, t_fire, k0, d0):
            d_char_n = beta_n * t_fire + k0 * d0
            return d_char_n

        latex, d_char_n = _fire_depth(beta_n, t_fire, k0, d0)
        blocks.append(hc_block(latex, "Notional char depth"))

        @handcalc(override="long", precision=2)
        def _fire_section(b, h, d_char_n, exposed_sides, exposed_bottom, exposed_top):
            b_fi = b - exposed_sides * d_char_n
            h_fi = h - int(exposed_bottom) * d_char_n - int(exposed_top) * d_char_n
            A_fi = b_fi * h_fi
            W_y_fi = (b_fi * h_fi**2) / 6
            return b_fi, h_fi, A_fi, W_y_fi

        latex, (b_fi, h_fi, A_fi, W_y_fi) = _fire_section(
            b, h, d_char_n, exposed_sides, exposed_bottom, exposed_top
        )
        blocks.append(hc_block(latex, "Residual section in fire"))

        blocks.append(N(
            "Implementation note: this fire check uses the reduced cross-section method. "
            "The design actions for fire should come from the fire load combination. "
            "If eta_fi is supplied, the ambient actions are scaled to obtain M_Ed,fi and V_Ed,fi."
        ))

        @handcalc(override="long", precision=2)
        def _fire_strengths(f_mk, f_vk, kmod_fi, gamma_M_fi):
            f_md_fi = kmod_fi * f_mk / gamma_M_fi
            f_vd_fi = kmod_fi * f_vk / gamma_M_fi
            return f_md_fi, f_vd_fi

        latex, (f_md_fi, f_vd_fi) = _fire_strengths(f_mk, f_vk, kmod_fi, gamma_M_fi)
        blocks.append(hc_block(latex, "Design strengths in fire"))

        @handcalc(override="long", precision=2)
        def _fire_stresses(M_Ed_fi, V_Ed_fi, W_y_fi, A_fi):
            sigma_m_d_fi = M_Ed_fi / W_y_fi
            tau_d_fi = (1.5 * V_Ed_fi) / A_fi
            return sigma_m_d_fi, tau_d_fi

        latex, (sigma_m_d_fi, tau_d_fi) = _fire_stresses(M_Ed_fi, V_Ed_fi, W_y_fi, A_fi)
        blocks.append(hc_block(latex, "Design stresses in fire"))

        blocks.append(cc.check("Brand bøjning: sigma_m,d,fi / f_m,d,fi", sigma_m_d_fi, f_md_fi))
        blocks.append(cc.check("Brand forskydning: tau_d,fi / f_v,d,fi", tau_d_fi, f_vd_fi))

    return blocks
