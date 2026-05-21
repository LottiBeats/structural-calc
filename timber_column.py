"""
timber_column.py - Timber column module (EN 1995-1-1)
Unit-aware with forallpeople. No manual conversions.

Checks a rectangular timber beam-column under axial compression and
one-axis bending. All three failure modes are covered:

  EN 1995-1-1 cl. 6.1.4 / 6.2.4  Section check (eqs. 6.19 and 6.20)
  EN 1995-1-1 cl. 6.3.2           Flexural buckling – both axes
                                   (eqs. 6.23 and 6.24)
  EN 1995-1-1 cl. 6.3.3           Lateral-torsional buckling
                                   (eqs. 6.33 and 6.35)
                                   — only when l_ef_ltb is provided

Axis convention (matches EN 1995-1-1 and the B.43 reference):
  Axis 1 (strong / major):  bending about y-y, W_1 = b h² / 6,  i_1 = h / √12
  Axis 2 (weak  / minor):   buckling about z-z,                  i_2 = b / √12
  where b = width (smaller dim) and h = depth (larger dim in bending plane).

G_0,05 is read from timber_grades.py (≈ E_0,05 / 16 per EN 338).
"""

from math import pi

from handcalcs.decorator import handcalc
import forallpeople as si

si.environment("structural", top_level=True)

from calc_core import CheckContext, MH, N, S, T, TBL, hc_block
from timber_grades import get_timber_grade


KMOD = {
    (1, "permanent"): 0.60, (1, "long"): 0.70, (1, "medium"): 0.80,
    (1, "short"): 0.90,     (1, "instant"): 1.10,
    (2, "permanent"): 0.60, (2, "long"): 0.70, (2, "medium"): 0.80,
    (2, "short"): 0.90,     (2, "instant"): 1.10,
    (3, "permanent"): 0.50, (3, "long"): 0.55, (3, "medium"): 0.65,
    (3, "short"): 0.70,     (3, "instant"): 0.90,
}

_BETA_C = {"solid_timber": 0.20, "glulam": 0.10}


def timber_column_bending_and_axial(
    label,
    length,
    N_Ed,
    M_Ed,
    b,
    h,
    timber_grade=None,
    f_c0k=None,
    f_mk=None,
    E_0_05=None,
    G_0_05=None,
    service_class=1,
    load_duration="medium",
    gamma_M=1.3,
    k_m=0.70,
    material_type="solid_timber",
    effective_length_factor=1.0,
    l_ef_ltb=None,
    check_buckling_axis_1=True,
    check_buckling_axis_2=True,
    check_ltb=True,
    buckling_axis=None,   # kept for backwards compatibility, not used
):
    """
    Return report blocks for a timber beam-column ULS check.

    Parameters
    ----------
    label : str
        Identifier shown in the module header.
    length : quantity [m]
        Physical (unbraced) member height / length.
    N_Ed : quantity [N / kN]
        Design axial compressive force.
    M_Ed : quantity [N·m / kN·m]
        Design bending moment about the strong axis (axis 1).
    b : quantity [m / mm]
        Cross-section width  (dimension perpendicular to bending plane).
    h : quantity [m / mm]
        Cross-section depth  (dimension in the bending plane).
    timber_grade : str, optional
        Grade string, e.g. "C24".  Looked up in timber_grades.py.
    f_c0k, f_mk, E_0_05, G_0_05 : quantity, optional
        Override individual material properties.
    service_class : int
        1 = dry interior, 2 = covered outdoor, 3 = exposed.
    load_duration : str
        "permanent", "long", "medium", "short", or "instant".
    gamma_M : float
        Material partial factor (1.3 for solid timber / glulam).
    k_m : float
        Redistribution factor (0.70 rectangular, 1.00 other shapes).
    material_type : str
        "solid_timber" or "glulam"  — sets β_c for buckling curve.
    effective_length_factor : float
        Effective length factor μ for both axes.
        1.0 = pin-pin, 0.7 = pin-fixed, 2.0 = cantilever.
    l_ef_ltb : quantity [m / mm], optional
        Effective length for lateral-torsional buckling.
        When provided the LTB check (cl. 6.3.3) is included.
        Typical values from EN 1995-1-1 Table 6.1:
          Simply supported, UDL:              l_ef = 0.9 L + 2 h
          Simply supported, mid-point load:   l_ef = 0.8 L + 2 h
          Simply supported, constant moment:  l_ef = L
          Cantilever, UDL:                    l_ef = 0.5 L + 2 h
    check_buckling_axis_1, check_buckling_axis_2, check_ltb : bool
        Enable or disable axis-1 buckling, axis-2 buckling, and LTB checks.
    """

    # ------------------------------------------------------------------
    # Grade data
    # ------------------------------------------------------------------
    grade_key = None
    grade_data = None
    if timber_grade is not None:
        grade_key, grade_data = get_timber_grade(timber_grade)

    if f_c0k   is None: f_c0k   = grade_data["f_c0k"]   if grade_data else 21 * MPa
    if f_mk    is None: f_mk    = grade_data["f_mk"]    if grade_data else 24 * MPa
    if E_0_05  is None: E_0_05  = grade_data["E_0_05"]  if grade_data else 7_400 * MPa
    if G_0_05  is None: G_0_05  = grade_data.get("G_0_05", E_0_05 / 16) if grade_data else E_0_05 / 16
    if material_type == "solid_timber" and grade_data is not None:
        material_type = grade_data["material_type"]

    kmod   = KMOD.get((service_class, load_duration), 0.80)
    beta_c = _BETA_C.get(material_type, _BETA_C["solid_timber"])
    cc     = CheckContext()
    blocks = []
    section_properties = None
    I_t = None
    show_section_plot = False
    section_label = f"{b}\u00d7{h}"

    # ------------------------------------------------------------------
    # Module header
    # ------------------------------------------------------------------
    
    blocks.append(MH(f"Timber column - {section_label or f'{b}×{h}'}",
                     f"{label}  |  EN 1995-1-1", material="timber"))

    if show_section_plot:
        plot_parts = (
            section_properties.get("parts")
            if section_properties is not None and section_properties.get("parts")
            else [{"name": "Section", "b": b, "h": h, "x": 0.0, "y": 0.0, "is_void": False}]
        )
        plot_path = plot_composite_section(plot_parts, figure_path=figure_path)
        blocks.append(S("Cross-section"))
        blocks.append(FIG(
            plot_path,
            figure_caption or "Timber cross-section used for the beam-column check.",
            width_mm=110,
        ))

    # ------------------------------------------------------------------
    # Design parameters
    # ------------------------------------------------------------------
    blocks.append(S("Design parameters"))
    blocks.append(T(
        f"Rectangular timber beam-column, grade "
        f"{grade_data['description'] if grade_data else 'manual'}. "
        f"Service class {service_class}, load duration: {load_duration}, "
        f"k_mod = {kmod}, \u03b3_M = {gamma_M}."
    ))
    blocks.append(TBL(
        ["Property", "Symbol", "Value"],
        [
            ["Column length",            "L",        str(length)],
            ["Design axial force",       "N_Ed",     str(N_Ed)],
            ["Design bending moment",    "M_y,Ed",   str(M_Ed)],
            ["Width",                    "b",        str(b if section_properties is None else section_properties.get("width_total", b))],
            ["Depth",                    "h",        str(h if section_properties is None else section_properties.get("height_total", h))],
            ["Timber grade",             "\u2013",   grade_key if grade_key else "manual"],
            ["Compression strength",     "f_c,0,k",  str(f_c0k)],
            ["Bending strength",         "f_m,k",    str(f_mk)],
            ["5-percentile E-modulus",   "E_0,05",   str(E_0_05)],
            ["5-percentile G-modulus",   "G_0,05",   str(G_0_05)],
            ["Material model",           "\u2013",   material_type],
            ["Effective length factor",  "\u03bc",   str(effective_length_factor)],
        ],
    ))

    # ------------------------------------------------------------------
    # Section properties
    # ------------------------------------------------------------------
    blocks.append(S("Section properties"))

    if section_properties is None:
        @handcalc(override="long", precision=2)
        def _section_props(b, h):
            A       = b * h
            W_y     = (b * h**2) / 6
            I_1     = (b * h**3) / 12
            I_2     = (h * b**3) / 12
            i_1     = (I_1 / A) ** 0.5
            i_2     = (I_2 / A) ** 0.5
            return A, W_y, I_1, I_2, i_1, i_2

        latex, (A, W_y, I_1, I_2, i_1, i_2) = _section_props(b, h)
        blocks.append(hc_block(latex, "A, W_y, I_1 (strong), I_2 (weak), i_1, i_2"))

        blocks.append(N(
            "Axis 1 = strong axis (major): bending in the h-direction, i_1 = h/\u221a12. "
            "Axis 2 = weak axis (minor): buckling in the b-direction, i_2 = b/\u221a12."
        ))
    else:
        required_keys = ("A", "W_y", "I_1", "I_2", "i_1", "i_2")
        missing = [key for key in required_keys if key not in section_properties]
        if missing:
            raise ValueError(f"section_properties is missing keys: {', '.join(missing)}")

        A = section_properties["A"]
        W_y = section_properties["W_y"]
        I_1 = section_properties["I_1"]
        I_2 = section_properties["I_2"]
        i_1 = section_properties["i_1"]
        i_2 = section_properties["i_2"]

        @handcalc(override="long", precision=4)
        def _section_props_custom(A, W_y, I_1, I_2, i_1, i_2):
            return A, W_y, I_1, I_2, i_1, i_2

        latex, _ = _section_props_custom(A, W_y, I_1, I_2, i_1, i_2)
        blocks.append(hc_block(latex, "A, W_y, I_1 (strong), I_2 (weak), i_1, i_2"))

        blocks.append(N(
            "Section properties are imported from a custom composite section. "
            "Axis 1 is treated as the strong axis and axis 2 as the weak axis."
        ))

    # ------------------------------------------------------------------
    # Design material strengths
    # ------------------------------------------------------------------
    blocks.append(S("Design material strengths"))

    @handcalc(override="long", precision=2)
    def _design_strengths(f_c0k, f_mk, kmod, gamma_M):
        f_c0d = kmod * f_c0k / gamma_M
        f_md  = kmod * f_mk  / gamma_M
        return f_c0d, f_md

    latex, (f_c0d, f_md) = _design_strengths(f_c0k, f_mk, kmod, gamma_M)
    blocks.append(hc_block(latex, "f_c,0,d and f_m,d"))

    # ------------------------------------------------------------------
    # Section stresses
    # ------------------------------------------------------------------
    blocks.append(S("Section stresses"))

    @handcalc(override="long", precision=2)
    def _stresses(N_Ed, M_Ed, A, W_y):
        sigma_c0d = N_Ed / A
        sigma_m1d = M_Ed / W_y
        sigma_m2d = 0 * sigma_m1d
        return sigma_c0d, sigma_m1d, sigma_m2d

    latex, (sigma_c0d, sigma_m1d, sigma_m2d) = _stresses(N_Ed, M_Ed, A, W_y)
    sigma_md = sigma_m1d
    blocks.append(hc_block(latex, "\u03c3_c,0,d, \u03c3_m,1,d and \u03c3_m,2,d"))

    # ------------------------------------------------------------------
    # Section check – no buckling reduction (eqs. 6.19 and 6.20)
    # ------------------------------------------------------------------
    blocks.append(S("Section check \u2013 EN 1995-1-1 eqs. 6.19 and 6.20"))

    @handcalc(override="long", precision=3)
    def _compression_only(sigma_c0d, f_c0d):
        eta_6_2 = sigma_c0d / f_c0d
        return eta_6_2

    latex, eta_6_2 = _compression_only(sigma_c0d, f_c0d)
    blocks.append(hc_block(latex, "Eq. 6.2"))
    blocks.append(cc.check("Compression eq. 6.2", float(eta_6_2), 1.0))

    @handcalc(override="long", precision=3)
    def _section_6_19(sigma_c0d, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m):
        eta_19 = (sigma_c0d / f_c0d)**2 + sigma_m1d / f_md + k_m * sigma_m2d / f_md
        return eta_19

    @handcalc(override="long", precision=3)
    def _section_6_20(sigma_c0d, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m):
        eta_20 = (sigma_c0d / f_c0d)**2 + k_m * sigma_m1d / f_md + sigma_m2d / f_md
        return eta_20

    latex, eta_19 = _section_6_19(sigma_c0d, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m)
    blocks.append(hc_block(latex, "Eq. 6.19"))
    blocks.append(cc.check("Section eq. 6.19", float(eta_19), 1.0))

    latex, eta_20 = _section_6_20(sigma_c0d, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m)
    blocks.append(hc_block(latex, "Eq. 6.20"))
    blocks.append(cc.check("Section eq. 6.20", float(eta_20), 1.0))

    # ------------------------------------------------------------------
    # Flexural buckling – axis 1 (strong) – cl. 6.3.2
    # ------------------------------------------------------------------
    if check_buckling_axis_1:
        blocks.append(S("Flexural buckling \u2013 axis 1 (strong) \u2013 EN 1995-1-1 cl. 6.3.2"))

        @handcalc(override="long", precision=2)
        def _buckling_1(mu, length, i1, f_c0k, E05):
            l_eff    = mu * length
            lam1     = l_eff / i1
            lambda_rel_1 = (lam1 / pi) * (f_c0k / E05) ** 0.5
            return l_eff, lam1, lambda_rel_1

        latex, (l_eff_1, lambda_1, lambda_rel_1) = _buckling_1(
            effective_length_factor, length, i_1, f_c0k, E_0_05
        )
        blocks.append(hc_block(latex, "l_eff,1, \u03bb_1 and \u03bb_rel,1"))

        @handcalc(override="long", precision=3)
        def _k_c1(lambda_rel_1, beta_c):
            k_1  = 0.5 * (1 + beta_c * (lambda_rel_1 - 0.3) + lambda_rel_1**2)
            k_c1 = 1 / (k_1 + (k_1**2 - lambda_rel_1**2) ** 0.5)
            return k_1, k_c1

        if float(lambda_rel_1) <= 0.3:
            k_c1 = 1.0
            blocks.append(N(
                "\u03bb_rel,1 \u2264 0.3: no flexural-buckling reduction about the strong axis (k_c,1 = 1.0)."
            ))
        else:
            latex, (k_1, k_c1_qty) = _k_c1(lambda_rel_1, beta_c)
            k_c1 = min(float(k_c1_qty), 1.0)
            blocks.append(hc_block(latex, "k_1 and k_c,1"))
    else:
        k_c1 = 1.0
        blocks.append(N("Beam is restrained against buckling about axis 1; k_c,1 = 1.0."))

    # ------------------------------------------------------------------
    # Flexural buckling – axis 2 (weak) – cl. 6.3.2
    # ------------------------------------------------------------------
    if check_buckling_axis_2:
        blocks.append(S("Flexural buckling \u2013 axis 2 (weak) \u2013 EN 1995-1-1 cl. 6.3.2"))

        @handcalc(override="long", precision=2)
        def _buckling_2(mu, length, i2, f_c0k, E05):
            l_eff = mu * length
            lam2  = l_eff / i2
            lambda_rel_2 = (lam2 / pi) * (f_c0k / E05) ** 0.5
            return l_eff, lam2, lambda_rel_2

        latex, (l_eff_2, lambda_2, lambda_rel_2) = _buckling_2(
            effective_length_factor, length, i_2, f_c0k, E_0_05
        )
        blocks.append(hc_block(latex, "l_eff,2, \u03bb_2 and \u03bb_rel,2"))

        @handcalc(override="long", precision=3)
        def _k_c2(lambda_rel_2, beta_c):
            k_2  = 0.5 * (1 + beta_c * (lambda_rel_2 - 0.3) + lambda_rel_2**2)
            k_c2 = 1 / (k_2 + (k_2**2 - lambda_rel_2**2) ** 0.5)
            return k_2, k_c2

        if float(lambda_rel_2) <= 0.3:
            k_c2 = 1.0
            blocks.append(N(
                "\u03bb_rel,2 \u2264 0.3: no flexural-buckling reduction about the weak axis (k_c,2 = 1.0)."
            ))
        else:
            latex, (k_2, k_c2_qty) = _k_c2(lambda_rel_2, beta_c)
            k_c2 = min(float(k_c2_qty), 1.0)
            blocks.append(hc_block(latex, "k_2 and k_c,2"))
    else:
        k_c2 = 1.0
        blocks.append(N("Beam is restrained against buckling about axis 2; k_c,2 = 1.0."))

    # ------------------------------------------------------------------
    # Interaction – strong-axis buckling governs (eq. 6.23)
    # ------------------------------------------------------------------
    if check_buckling_axis_1:
        blocks.append(S("Interaction check \u2013 eq. 6.23 (axis 1 buckling)"))

        @handcalc(override="long", precision=3)
        def _eq_6_23(sigma_c0d, k_c1, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m):
            eta_23 = sigma_c0d / (k_c1 * f_c0d) + sigma_m1d / f_md + k_m * sigma_m2d / f_md
            return eta_23

        latex, eta_23 = _eq_6_23(sigma_c0d, k_c1, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m)
        blocks.append(hc_block(latex, "Eq. 6.23"))
        blocks.append(cc.check("Interaction eq. 6.23 (axis 1 buckling)", float(eta_23), 1.0))

    # ------------------------------------------------------------------
    # Interaction – weak-axis buckling governs (eq. 6.24)
    # ------------------------------------------------------------------
    if check_buckling_axis_2:
        blocks.append(S("Interaction check \u2013 eq. 6.24 (axis 2 buckling)"))

        @handcalc(override="long", precision=3)
        def _eq_6_24(sigma_c0d, k_c2, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m):
            eta_24 = sigma_c0d / (k_c2 * f_c0d) + k_m * sigma_m1d / f_md + sigma_m2d / f_md
            return eta_24

        latex, eta_24 = _eq_6_24(sigma_c0d, k_c2, f_c0d, sigma_m1d, sigma_m2d, f_md, k_m)
        blocks.append(hc_block(latex, "Eq. 6.24"))
        blocks.append(cc.check("Interaction eq. 6.24 (axis 2 buckling)", float(eta_24), 1.0))

    # ------------------------------------------------------------------
    # Lateral-torsional buckling – cl. 6.3.3
    # (only performed when l_ef_ltb is explicitly provided)
    # ------------------------------------------------------------------
    if check_ltb and l_ef_ltb is not None:
        blocks.append(S("Lateral-torsional buckling \u2013 EN 1995-1-1 cl. 6.3.3"))
        blocks.append(T(
            "LTB is relevant when the compression edge is unrestrained over the member length. "
            f"Effective length for LTB: l_ef = {l_ef_ltb}."
        ))

        if I_t is None:
            if section_properties is not None:
                raise ValueError("LTB for a custom section requires I_t to be provided explicitly.")

            # Torsion constant I_t (Prandtl approximation for rectangular section)
            # I_t = a³b/3 × (1 - 0.63a/b + 0.052(a/b)^5),  a = shorter dim
            if float(b) <= float(h):
                b_thin, b_wide = b, h
            else:
                b_thin, b_wide = h, b

            @handcalc(override="long", precision=4)
            def _torsion(b_thin, b_wide):
                ratio = b_thin / b_wide
                I_t   = b_thin**3 * b_wide / 3 * (1 - 0.63 * ratio + 0.052 * ratio**5)
                return ratio, I_t

            latex, (_, I_t) = _torsion(b_thin, b_wide)
            blocks.append(hc_block(latex, "Torsion constant I_t (Prandtl, rectangular section)"))
        else:
            @handcalc(override="long", precision=4)
            def _torsion_custom(I_t):
                return I_t

            latex, _ = _torsion_custom(I_t)
            blocks.append(hc_block(latex, "Torsion constant I_t (user supplied for custom section)"))

        # sigma_m,crit – split into two steps so each line stays simple
        @handcalc(override="long", precision=4)
        def _ltb_product(E05, I2, G05, It):
            EI_GI = E05 * I2 * G05 * It
            return EI_GI

        latex, EI_GI = _ltb_product(E_0_05, I_2, G_0_05, I_t)
        blocks.append(hc_block(latex, "E\u00b7I\u2082\u00b7G\u00b7I_t product for \u03c3_m,crit"))

        @handcalc(override="long", precision=2)
        def _sigma_m_crit(EI_GI, l_ef, W_y):
            sigma_m_crit = pi * EI_GI ** 0.5 / (l_ef * W_y)
            return sigma_m_crit

        latex, sigma_m_crit = _sigma_m_crit(EI_GI, l_ef_ltb, W_y)
        blocks.append(hc_block(latex, "\u03c3_m,crit  (eq. 6.31)"))

        # lambda_rel,m and k_crit
        @handcalc(override="long", precision=3)
        def _lambda_rel_m(f_mk, sigma_m_crit):
            lambda_rel_m = (f_mk / sigma_m_crit) ** 0.5
            return lambda_rel_m

        latex, lambda_rel_m = _lambda_rel_m(f_mk, sigma_m_crit)
        blocks.append(hc_block(latex, "\u03bb_rel,m  (eq. 6.30)"))

        @handcalc(override="long", precision=3)
        def _kcrit_mid(lambda_rel_m):
            k_crit = 1.56 - 0.75 * lambda_rel_m
            return k_crit

        @handcalc(override="long", precision=3)
        def _kcrit_high(lambda_rel_m):
            k_crit = 1 / lambda_rel_m**2
            return k_crit

        lrm = float(lambda_rel_m)
        if lrm <= 0.75:
            k_crit = 1.0
            blocks.append(N(
                "\u03bb_rel,m \u2264 0.75: no LTB reduction (k_crit = 1.0, eq. 6.34)."
            ))
        elif lrm <= 1.4:
            latex, k_crit_qty = _kcrit_mid(lambda_rel_m)
            k_crit = float(k_crit_qty)
            blocks.append(hc_block(latex, "k_crit  (eq. 6.34, intermediate slenderness)"))
        else:
            latex, k_crit_qty = _kcrit_high(lambda_rel_m)
            k_crit = float(k_crit_qty)
            blocks.append(hc_block(latex, "k_crit  (eq. 6.34, high slenderness)"))

        # eq. 6.33: pure bending LTB check
        @handcalc(override="long", precision=3)
        def _eq_6_33(sigma_md, k_crit, f_md):
            eta_33 = sigma_md / (k_crit * f_md)
            return eta_33

        latex, eta_33 = _eq_6_33(sigma_md, k_crit, f_md)
        blocks.append(hc_block(latex, "Eq. 6.33 \u2013 bending only"))
        blocks.append(cc.check("LTB eq. 6.33: \u03c3_m,d / (k_crit f_m,d)", float(eta_33), 1.0))

        # eq. 6.35: combined LTB + weak-axis buckling – split into parts
        @handcalc(override="long", precision=3)
        def _eq_6_35(sigma_md, k_crit, f_md, sigma_c0d, k_c2, f_c0d):
            ratio_m = sigma_md / (k_crit * f_md)
            ratio_c = sigma_c0d / (k_c2 * f_c0d)
            eta_35  = ratio_m**2 + ratio_c
            return ratio_m, ratio_c, eta_35

        latex, (_, _, eta_35) = _eq_6_35(sigma_md, k_crit, f_md, sigma_c0d, k_c2, f_c0d)
        blocks.append(hc_block(latex, "Eq. 6.35 \u2013 LTB combined with axis-2 buckling"))
        blocks.append(cc.check("LTB eq. 6.35: combined", float(eta_35), 1.0))
    elif l_ef_ltb is not None and not check_ltb:
        blocks.append(N("Beam compression edge is restrained against lateral-torsional buckling; LTB check not required."))

    return blocks


def timber_column_side_by_side(
    label,
    length,
    N_Ed,
    M_Ed,
    b_single,
    h_single,
    n_members=2,
    gap=0.0,
    figure_path=None,
    figure_caption="",
    show_section_plot=True,
    **kwargs,
):
    """
    Convenience wrapper for a built-up timber section with identical members
    placed side by side.
    """
    parts = side_by_side_rectangles_section(
        b=b_single,
        h=h_single,
        n=n_members,
        gap=gap,
        name_prefix="Member",
    )
    props = composite_section_properties(parts)
    auto_I_t = kwargs.pop("I_t", None)
    if auto_I_t is None:
        if float(b_single) <= float(h_single):
            b_thin, b_wide = b_single, h_single
        else:
            b_thin, b_wide = h_single, b_single
        ratio = b_thin / b_wide
        single_I_t = b_thin**3 * b_wide / 3 * (1 - 0.63 * ratio + 0.052 * ratio**5)
        auto_I_t = n_members * single_I_t
    props["section_label"] = f"{n_members} × {b_single}×{h_single} side-by-side"

    blocks = timber_column_bending_and_axial(
        label=label,
        length=length,
        N_Ed=N_Ed,
        M_Ed=M_Ed,
        b=props["width_total"],
        h=props["height_total"],
        section_properties=props,
        I_t=auto_I_t,
        **kwargs,
    )
    blocks.insert(
        1,
        N(
            "For the built-up side-by-side section, I_t is taken as the sum of the "
            "individual rectangular member torsion constants."
        ),
    )

    return blocks
