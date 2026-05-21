"""
app.py — OMKREDS Structural Report Generator
Local Streamlit web app.  Run with:  streamlit run app.py
"""

import sys, math, io, os, tempfile
from datetime import date
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# ── units ─────────────────────────────────────────────────────────────────────
import forallpeople as si
si.environment("structural", top_level=True)

import builtins as _builtins
# Snapshot the forallpeople unit names so custom-calc eval can find them
_UNIT_NS = {k: v for k, v in vars(_builtins).items() if not k.startswith("_")}
_UNIT_NS.update({
    "pi": math.pi, "e": math.e,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "exp": math.exp, "log": math.log,
    "abs": abs, "min": min, "max": max, "round": round,
})

# ── calc modules ──────────────────────────────────────────────────────────────
from calc_core import (COVER, TOC, PAGEBREAK, H1, T, N as NOTE, FIG,
                       CheckContext, S, CALC_ROW)
from holst_layout import generate_pdf_holst
from beam_fem import BeamFEM, summarise_beam_actions
from timber import timber_beam as _timber_beam
from timber_column import timber_column_bending_and_axial
from steel import steel_beam_ipe
from concrete import rc_beam_bending
from masonry import masonry_wall_vertical

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

TIMBER_GRADES = [
    "C14","C16","C18","C20","C22","C24","C27","C30","C35","C40","C45","C50",
    "D30","D35","D40","D50","D60","D70",
    "GL20H","GL22H","GL24H","GL26H","GL28H","GL30H","GL32H",
]
LOAD_DURATIONS  = ["permanent","long","medium","short","instant"]
SERVICE_CLASSES = [1, 2, 3]

UNIT_CHOICES = [
    "-","m","mm","cm",
    "kN","N","MN",
    "kN/m","N/m","kN/m**2",
    "MPa","GPa","kPa",
    "kN*m","N*m",
    "mm**2","cm**2","m**2",
    "mm**3","cm**3",
    "mm**4","cm**4",
    "kg","kN/m**3",
]
UNIT_LABELS = {
    "-":"—","m":"m","mm":"mm","cm":"cm",
    "kN":"kN","N":"N","MN":"MN",
    "kN/m":"kN/m","N/m":"N/m","kN/m**2":"kN/m²",
    "MPa":"MPa","GPa":"GPa","kPa":"kPa",
    "kN*m":"kN·m","N*m":"N·m",
    "mm**2":"mm²","cm**2":"cm²","m**2":"m²",
    "mm**3":"mm³","cm**3":"cm³",
    "mm**4":"mm⁴","cm**4":"cm⁴",
    "kg":"kg","kN/m**3":"kN/m³",
}

BLOCK_MENU = {
    "— Analysis —": None,
    "FEM beam analysis": "fem_beam",
    "— Eurocode checks —": None,
    "Timber beam-column  (EN 1995)": "timber_beam_column",
    "Timber beam  (EN 1995)": "timber_beam",
    "Steel beam IPE / HEA / HEB / L  (EN 1993)": "steel_beam",
    "Concrete beam  (EN 1992)": "concrete_beam",
    "Masonry wall  (EN 1996)": "masonry_wall",
    "— Content —": None,
    "Custom calculation": "custom_calc",
    "Section heading": "heading",
    "Paragraph text": "text",
    "Note / warning": "note",
    "Figure / image": "figure",
    "— Layout —": None,
    "Page break": "pagebreak",
}

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Structural Report Generator",
    page_icon=None,
    layout="wide",
)

st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }

/* Sidebar headings */
[data-testid="stSidebar"] h2 {
    font-size: 11px !important; letter-spacing: 0.1em;
    text-transform: uppercase; font-weight: 700;
    border-bottom: 1px solid #ddd; padding-bottom: 8px; margin-bottom: 14px;
}
[data-testid="stSidebar"] h3 {
    font-size: 10px !important; letter-spacing: 0.08em;
    text-transform: uppercase; font-weight: 600;
    margin-top: 18px; margin-bottom: 4px; color: #888 !important;
}
[data-testid="stSidebar"] { border-right: 1px solid #e8e8e8; }

/* Block expanders — clean top border, no radius */
div[data-testid="stExpander"] {
    border: 1px solid #e8e8e8 !important;
    border-top: 2px solid #111 !important;
    border-radius: 0 !important;
    margin-bottom: 4px !important;
}
div[data-testid="stExpander"] summary {
    font-size: 11px !important; font-weight: 700 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
}

/* Primary button — solid black */
div[data-testid="stButton"] > button[kind="primary"] {
    background: #111 !important; color: #fff !important;
    border: none !important; border-radius: 2px !important;
    font-weight: 700 !important; letter-spacing: 0.06em !important;
    text-transform: uppercase !important; font-size: 11px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover { background: #333 !important; }

/* Secondary buttons — outline */
div[data-testid="stButton"] > button:not([kind="primary"]) {
    border-radius: 2px !important; font-size: 11px !important;
    letter-spacing: 0.04em !important;
}

/* Download button */
div[data-testid="stDownloadButton"] > button {
    background: #111 !important; color: #fff !important;
    border: none !important; border-radius: 2px !important;
    font-weight: 700 !important; text-transform: uppercase !important;
    letter-spacing: 0.06em !important; font-size: 11px !important;
}

/* Input fields — square corners */
input, textarea { border-radius: 2px !important; }

/* Remove radio label uppercase that was set globally */
div[data-testid="stRadio"] label { font-size: 13px !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────

if "blocks" not in st.session_state:
    st.session_state.blocks = []
if "_id" not in st.session_state:
    st.session_state._id = 0

def _new_id():
    st.session_state._id += 1
    return st.session_state._id

def _default_block(btype):
    base = {"type": btype, "id": _new_id()}
    if btype == "fem_beam":
        base["data"] = {
            "label": "FEM-1",
            "span_m": 6.0,
            "E_mpa": 210000.0,
            "I_cm4": 8356.0,
            "n_elements": 100,
            "supports": [
                {"x_m": 0.0, "type": "pin"},
                {"x_m": 6.0, "type": "roller"},
            ],
            "loads": [
                {"type": "udl", "g_k_kNm": 5.0, "q_k_kNm": 3.0,
                 "x1_m": 0.0, "x2_m": 6.0, "gamma_G": 1.35, "gamma_Q": 1.50},
            ],
            # Cached results (filled after FEM run)
            "res_M_Ed_kNm":  None,
            "res_V_Ed_kN":   None,
            "res_delta_mm":  None,
            "res_x_M_m":     None,
            "res_x_V_m":     None,
            "res_x_delta_m": None,
        }
    elif btype == "timber_beam_column":
        base["data"] = {
            "label":"BC1","b_mm":100.0,"h_mm":200.0,"length_m":3.0,
            "grade":"C24","service_class":1,"load_duration":"medium",
            "gamma_M":1.35,"k_m":0.70,"eff_len":1.0,
            "N_Ed_kN":0.0,"M_Ed_kNm":0.0,
            "buck_y":True,"buck_z":False,"check_ltb":False,"l_ef_ltb_m":3.0,
        }
    elif btype == "timber_beam":
        base["data"] = {
            "label":"TB1","b_mm":100.0,"h_mm":200.0,"span_m":4.0,
            "grade":"C24","service_class":1,"load_duration":"medium",
            "gamma_M":1.35,
            "input_mode":"direct",   # "direct" | "characteristic" | "fem"
            "fem_label":"",
            "M_Ed_kNm":0.0,"V_Ed_kN":0.0,
            "g_k_kNm":1.0,"q_k_kNm":1.5,
        }
    elif btype == "steel_beam":
        base["data"] = {
            "label":"S1","section":"IPE300","grade":"S355","span_m":5.0,
            "g_k_kNm":5.0,"q_k_kNm":3.0,"gamma_M0":1.0,
            "input_mode":"characteristic",  # "direct" | "characteristic" | "fem"
            "fem_label":"",
            "M_Ed_kNm":0.0,"V_Ed_kN":0.0,
            # LTB parameters
            "l_cr_ltb_m":None,    # None = not set yet; defaults to span in UI
            "C1_ltb":1.0,
            "gamma_M1":1.0,
            # Restraint flags
            "ltb_restrained":False,
            "buck_y_restrained":False,
            "buck_x_restrained":False,
        }
    elif btype == "concrete_beam":
        base["data"] = {
            "label":"B1","b_mm":300.0,"h_mm":500.0,"d_mm":450.0,
            "span_m":6.0,"f_ck_mpa":25.0,"f_yk_mpa":500.0,
            "As_prov_mm2":1500.0,"direct":False,
            "g_k_kNm":10.0,"q_k_kNm":8.0,
            "M_Ed_kNm":0.0,"V_Ed_kN":0.0,
        }
    elif btype == "masonry_wall":
        base["data"] = {
            "label":"MW1","height_m":2.7,"thickness_mm":150.0,"length_m":1.0,
            "N_k_kN":30.0,"f_b_mpa":10.0,"f_m_mpa":4.0,"gamma_M":2.5,
        }
    elif btype == "custom_calc":
        base["data"] = {
            "title":"Custom Calculation",
            "vars":[
                {"name":"","value":0.0,"unit":"-"},
            ],
            "formulas":[""],
            "checks":[],
        }
    elif btype in ("heading","text","note"):
        base["text"] = ""
    elif btype == "figure":
        base["path"] = ""
        base["caption"] = ""
    return base

# ─────────────────────────────────────────────────────────────────────────────
# FEM HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _run_fem(data: dict):
    """Build, load, and solve a BeamFEM from a fem_beam data dict.
    Returns (summary_dict, beam_object) or raises on error."""
    span   = float(data["span_m"])
    E      = float(data["E_mpa"]) * 1e6       # Pa
    I      = float(data["I_cm4"]) * 1e-8      # m⁴  (cm⁴ → m⁴)
    n_el   = max(20, int(data.get("n_elements", 100)))

    beam = BeamFEM(length=span, E=E, I=I, n_elements=n_el)

    for sup in data.get("supports", []):
        beam.add_support(float(sup["x_m"]), sup["type"])

    for load in data.get("loads", []):
        ltype = load["type"]
        if ltype == "udl":
            gG = float(load.get("gamma_G", 1.35))
            gQ = float(load.get("gamma_Q", 1.50))
            w  = gG * float(load["g_k_kNm"]) * 1e3 \
               + gQ * float(load["q_k_kNm"]) * 1e3   # N/m
            x1 = float(load.get("x1_m", 0.0))
            x2 = float(load.get("x2_m", span))
            beam.add_udl(w, x1, x2)
        elif ltype == "point":
            beam.add_point_load(float(load["x_m"]),
                                float(load["P_Ed_kN"]) * 1e3)
        elif ltype == "trapezoidal":
            gG = float(load.get("gamma_G", 1.35))
            gQ = float(load.get("gamma_Q", 1.50))
            w1 = gG * float(load["g_k1_kNm"]) * 1e3 \
               + gQ * float(load["q_k1_kNm"]) * 1e3
            w2 = gG * float(load["g_k2_kNm"]) * 1e3 \
               + gQ * float(load["q_k2_kNm"]) * 1e3
            beam.add_trapezoidal_load(w1, w2,
                                      float(load["x1_m"]),
                                      float(load["x2_m"]))

    beam.solve()
    summary = summarise_beam_actions(beam, data.get("label", "FEM"))
    return summary, beam


def _fem_plot_bytes(beam: BeamFEM, title: str = "") -> bytes:
    """Render FEM results as a 4-panel PNG (beam layout + δ + M + V) and return bytes."""
    import matplotlib.gridspec as gridspec
    x      = beam.x_fine
    v_mm   = beam.v_fine * 1e3
    M_kNm  = beam.M_fine * 1e-3
    V_kN   = beam.V_fine * 1e-3

    fig = plt.figure(figsize=(8, 7), dpi=110)
    if title:
        fig.suptitle(title, fontsize=9, fontweight="bold")

    gs = gridspec.GridSpec(4, 1, height_ratios=[1.3, 2, 2, 2],
                           hspace=0.65, figure=fig)
    ax0 = fig.add_subplot(gs[0])
    ax1 = fig.add_subplot(gs[1])
    ax2 = fig.add_subplot(gs[2])
    ax3 = fig.add_subplot(gs[3])

    # Panel 0: beam layout diagram
    beam._draw_beam_diagram(ax0)
    ax0.set_title("Beam layout", fontsize=8, pad=2)

    panels = [
        (ax1, v_mm,  "Displacement  [mm]",     "#2d6a9f"),
        (ax2, M_kNm, "Bending moment  [kN·m]", "#b03030"),
        (ax3, V_kN,  "Shear force  [kN]",      "#2a7a4b"),
    ]
    for ax, ydata, ylabel, col in panels:
        ax.plot(x, ydata, color=col, lw=1.4)
        ax.fill_between(x, ydata, alpha=0.12, color=col)
        ax.axhline(0, color="#555", lw=0.6, ls="--")
        ax.set_ylabel(ylabel, fontsize=7)
        ax.set_xlabel("x  [m]", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(True, ls=":", lw=0.4, alpha=0.5)

        # annotate peak value
        idx  = int(np.argmax(np.abs(ydata)))
        peak = ydata[idx]
        rng  = float(np.ptp(ydata)) or 1.0
        off  = rng * 0.22 * (1 if peak >= 0 else -1)
        ax.annotate(
            f"{peak:.3f}",
            xy=(x[idx], peak),
            xytext=(x[idx], peak + off),
            arrowprops=dict(arrowstyle="->", color=col, lw=0.8),
            fontsize=7, color=col, ha="center",
        )

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _beam_layout_preview_bytes(data: dict) -> bytes:
    """Build a compact beam layout diagram from block data (no FEM solve needed)."""
    span = float(data.get("span_m", 6.0))
    E    = float(data.get("E_mpa", 210000.0)) * 1e6
    I    = float(data.get("I_cm4", 8356.0))   * 1e-8

    # Minimal element count — we only need the diagram, not solved results
    preview = BeamFEM(length=span, E=E, I=I, n_elements=20)

    for sup in data.get("supports", []):
        try:
            preview.add_support(float(sup["x_m"]), sup["type"])
        except Exception:
            pass

    for load in data.get("loads", []):
        ltype = load.get("type", "udl")
        try:
            if ltype == "udl":
                gG = float(load.get("gamma_G", 1.35))
                gQ = float(load.get("gamma_Q", 1.50))
                w  = gG * float(load["g_k_kNm"]) * 1e3 \
                   + gQ * float(load["q_k_kNm"]) * 1e3
                preview.add_udl(w,
                                float(load.get("x1_m", 0.0)),
                                float(load.get("x2_m", span)))
            elif ltype == "point":
                preview.add_point_load(float(load["x_m"]),
                                       float(load["P_Ed_kN"]) * 1e3)
            elif ltype == "trapezoidal":
                gG = float(load.get("gamma_G", 1.35))
                gQ = float(load.get("gamma_Q", 1.50))
                w1 = gG * float(load["g_k1_kNm"]) * 1e3 \
                   + gQ * float(load["q_k1_kNm"]) * 1e3
                w2 = gG * float(load["g_k2_kNm"]) * 1e3 \
                   + gQ * float(load["q_k2_kNm"]) * 1e3
                preview.add_trapezoidal_load(w1, w2,
                                             float(load["x1_m"]),
                                             float(load["x2_m"]))
        except Exception:
            pass

    fig, ax = plt.subplots(1, 1, figsize=(7, 1.8), dpi=110)
    preview._draw_beam_diagram(ax)
    fig.tight_layout(pad=0.4)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _fem_labels_in_session() -> list[str]:
    """Return labels of all fem_beam blocks currently in session state."""
    return [
        b["data"].get("label", f"FEM-{b['id']}")
        for b in st.session_state.blocks
        if b["type"] == "fem_beam"
    ]


# ─────────────────────────────────────────────────────────────────────────────
# UNIT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def parse_qty(value: float, unit_str: str):
    """Convert a plain float + unit string to a forallpeople quantity."""
    if unit_str == "-":
        return float(value)
    try:
        unit = eval(unit_str, _UNIT_NS, {})
        return float(value) * unit
    except Exception:
        return float(value)

def fmt_qty(qty) -> str:
    try:
        return str(qty)
    except Exception:
        try:
            return f"{float(qty):.4g}"
        except Exception:
            return str(qty)

# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CALC EVALUATOR
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_custom_calc(var_rows, formula_rows):
    """
    Evaluates variables and formulas with full unit support.

    Returns:
        display_rows : list of (name, formula_display, result_str)
        ns           : dict of computed quantities (for checks)
        errors       : list of error strings
    """
    ns      = {}   # local namespace — grows as vars and formulas are evaluated
    display = []
    errors  = []

    # ── variables ─────────────────────────────────────────────────────────────
    for row in var_rows:
        name = row.get("name", "").strip()
        if not name:
            continue
        try:
            qty = parse_qty(float(row.get("value", 0.0)), row.get("unit", "-"))
            ns[name] = qty
            unit_lbl = UNIT_LABELS.get(row["unit"], row["unit"])
            val_str  = f"{row['value']:g}" if row["unit"] == "-" else f"{row['value']:g} {unit_lbl}"
            display.append((name, "", val_str))
        except Exception as exc:
            errors.append(f"Variable '{name}': {exc}")

    # ── formulas ──────────────────────────────────────────────────────────────
    for raw in formula_rows:
        raw = raw.strip()
        if not raw or "=" not in raw:
            continue
        lhs, rhs = raw.split("=", 1)
        lhs = lhs.strip()
        rhs = rhs.strip()
        try:
            result = eval(rhs, _UNIT_NS, ns)
            ns[lhs] = result
            result_str = fmt_qty(result)
            # Clean formula string for display (keep it readable)
            formula_disp = (rhs
                .replace("**", "^")
                .replace("*", " × ")
                .replace("/", " / ")
                .replace("  ", " ")
            )
            display.append((lhs, formula_disp, result_str))
        except Exception as exc:
            errors.append(f"Formula '{raw}': {exc}")
            display.append((lhs, rhs, f"ERROR: {exc}"))

    return display, ns, errors


def custom_calc_to_blocks(data: dict) -> list:
    """Convert a custom_calc data dict to a list of report blocks."""
    blocks = []
    title  = data.get("title", "Custom Calculation")
    blocks.append(S(title))

    var_rows      = [v for v in data.get("vars", [])     if v.get("name","").strip()]
    formula_rows  = [f for f in data.get("formulas", []) if f.strip() and "=" in f]

    display, ns, errors = evaluate_custom_calc(var_rows, formula_rows)

    for err in errors:
        blocks.append(NOTE(err))

    for name, formula, result in display:
        blocks.append(CALC_ROW(name, formula, result))

    chk = CheckContext()
    for c in data.get("checks", []):
        label   = c.get("label", "Check")
        d_expr  = c.get("demand", "").strip()
        cap_val = float(c.get("capacity", 1.0))
        cap_unt = c.get("unit", "-")
        if not d_expr:
            continue
        try:
            demand   = eval(d_expr, _UNIT_NS, ns)
            capacity = parse_qty(cap_val, cap_unt)
            blocks.append(chk.check(label, demand, capacity))
        except Exception as exc:
            blocks.append(T(f"Check error in '{label}': {exc}"))

    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK → REPORT CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

def block_to_report(block: dict, fem_results: dict = None) -> list:
    """Convert one session block to a list of report blocks.
    fem_results: dict of {label: summary_dict} pre-computed for this PDF run."""
    t = block["type"]
    if fem_results is None:
        fem_results = {}

    if t == "heading":
        return H1(block.get("text", ""))

    elif t == "text":
        return [T(block.get("text", ""))]

    elif t == "note":
        return [NOTE(block.get("text", ""))]

    elif t == "pagebreak":
        return PAGEBREAK()

    elif t == "figure":
        path = block.get("path", "").strip()
        if not path or not Path(path).exists():
            return [NOTE(f"Figure not found: {path}")]
        return [FIG(path, block.get("caption", ""))]

    elif t == "fem_beam":
        d = block["data"]
        blocks_out = [S(f"FEM analysis — {d.get('label','')}")]
        try:
            summary, beam = _run_fem(d)
            # Save diagram to temp file for FIG block
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            png_bytes = _fem_plot_bytes(beam, title=d.get("label",""))
            with open(tmp_path, "wb") as f:
                f.write(png_bytes)
            M_kNm  = summary["M_Ed_Nm"]  / 1e3
            V_kN   = summary["V_Ed_N"]   / 1e3
            d_mm   = summary["delta_max_m"] * 1e3
            blocks_out += [
                T(f"Simply-supported beam FEM analysis. "
                  f"Span {d['span_m']} m, "
                  f"EI = {d['E_mpa']*d['I_cm4']*1e-2:.0f} kN·m²."),
                CALC_ROW("M_Ed", "", f"{M_kNm:.3f} kN·m"),
                CALC_ROW("V_Ed", "", f"{V_kN:.3f} kN"),
                CALC_ROW("delta_max", "", f"{d_mm:.3f} mm"),
                FIG(tmp_path, caption=f"FEM results — {d.get('label','')}"),
            ]
        except Exception as exc:
            blocks_out.append(NOTE(f"FEM error: {exc}"))
        return blocks_out

    elif t == "timber_beam_column":
        d = block["data"]
        l_ef_ltb = None
        if d.get("check_ltb") and d.get("l_ef_ltb_m"):
            l_ef_ltb = d["l_ef_ltb_m"] * m
        return timber_column_bending_and_axial(
            label                = d["label"],
            length               = d["length_m"]  * m,
            N_Ed                 = d["N_Ed_kN"]   * kN,
            M_Ed                 = d["M_Ed_kNm"]  * kN * m,
            b                    = d["b_mm"]       * mm,
            h                    = d["h_mm"]       * mm,
            timber_grade         = d["grade"],
            service_class        = d["service_class"],
            load_duration        = d["load_duration"],
            gamma_M              = d["gamma_M"],
            k_m                  = d["k_m"],
            effective_length_factor = d["eff_len"],
            l_ef_ltb             = l_ef_ltb,
            check_buckling_axis_1= d["buck_y"],
            check_buckling_axis_2= d["buck_z"],
            check_ltb            = d["check_ltb"],
        )

    elif t == "timber_beam":
        d = block["data"]
        mode = d.get("input_mode", "direct" if d.get("direct", True) else "characteristic")
        if mode == "fem":
            lbl = d.get("fem_label","")
            res = fem_results.get(lbl)
            if res is None:
                return [NOTE(f"FEM block '{lbl}' not found or not solved.")]
            beam_results = {
                "source": "beam_fem",
                "case_name": f"FEM — {lbl}",
                "M_Ed":      res["M_Ed_Nm"]      * N * m,
                "V_Ed":      res["V_Ed_N"]        * N,
                "delta_max": res["delta_max_m"]   * m,
            }
            g_k = 0 * kN / m
            q_k = 0 * kN / m
        elif mode == "direct":
            beam_results = {
                "source": "manual input",
                "case_name": "ULS design actions",
                "M_Ed": d.get("M_Ed_kNm",0.0) * kN * m,
                "V_Ed": d.get("V_Ed_kN",0.0)  * kN,
            }
            g_k = 0 * kN / m
            q_k = 0 * kN / m
        else:
            beam_results = None
            g_k = d.get("g_k_kNm",1.0) * kN / m
            q_k = d.get("q_k_kNm",1.5) * kN / m
        return _timber_beam(
            label         = d["label"],
            span          = d["span_m"] * m,
            g_k           = g_k,
            q_k           = q_k,
            b             = d["b_mm"] * mm,
            h             = d["h_mm"] * mm,
            timber_grade  = d["grade"],
            service_class = d["service_class"],
            load_duration = d["load_duration"],
            gamma_M       = d["gamma_M"],
            beam_results  = beam_results,
        )

    elif t == "steel_beam":
        d = block["data"]
        from section_catalog import load_steel_profiles
        db  = load_steel_profiles()
        key = d["section"].upper().replace(" ", "")
        if key not in db:
            return [NOTE(f"Steel section '{d['section']}' not found in catalog.")]
        sec  = db[key]

        # Section properties come from catalog — not user-editable
        W_ply = sec["Wply_cm3"] * mm**3 * 1e3   # cm³ → mm³ → Physical (mm³)
        h     = sec["h_mm"]     * mm
        t_w   = sec["tw_mm"]    * mm

        # Steel grade → f_y
        GRADE_FY = {"S235": 235, "S275": 275, "S355": 355, "S420": 420, "S460": 460}
        grade     = d.get("grade", "S355")
        f_y_mpa   = GRADE_FY.get(grade, 355)
        f_y       = f_y_mpa * MPa
        gamma_M0  = float(d.get("gamma_M0", 1.0))

        mode = d.get("input_mode", "characteristic")
        if mode == "fem":
            lbl = d.get("fem_label","")
            res = fem_results.get(lbl)
            if res is None:
                return [NOTE(f"FEM block '{lbl}' not found or not solved.")]
            beam_results = {
                "source": "beam_fem",
                "case_name": f"FEM — {lbl}",
                "M_Ed":      res["M_Ed_Nm"]    * N * m,
                "V_Ed":      res["V_Ed_N"]      * N,
                "delta_max": res["delta_max_m"] * m,
            }
            g_k = 0 * kN / m
            q_k = 0 * kN / m
        elif mode == "direct":
            beam_results = {
                "source": "manual input",
                "case_name": "ULS design actions",
                "M_Ed": d.get("M_Ed_kNm", 0.0) * kN * m,
                "V_Ed": d.get("V_Ed_kN",  0.0) * kN,
            }
            g_k = 0 * kN / m
            q_k = 0 * kN / m
        else:
            beam_results = None
            g_k = d.get("g_k_kNm", 5.0) * kN / m
            q_k = d.get("q_k_kNm", 3.0) * kN / m

        # b and t_f only passed for I-sections (needed for LTB)
        _family   = sec.get("family", "")
        _b_qty    = sec["b_mm"]  * mm if _family in ("IPE", "HEA", "HEB") else None
        _tf_qty   = sec["tf_mm"] * mm if _family in ("IPE", "HEA", "HEB") else None

        # Effective LTB length — only when LTB is not suppressed
        _ltb_restrained = bool(d.get("ltb_restrained", False))
        _lcr_raw = d.get("l_cr_ltb_m")
        _l_cr_ltb = (
            float(_lcr_raw) * m
            if (_lcr_raw is not None and not _ltb_restrained and _b_qty is not None)
            else None
        )

        return steel_beam_ipe(
            label             = d["label"],
            section           = d["section"],
            span              = d["span_m"] * m,
            g_k               = g_k,
            q_k               = q_k,
            W_ply             = W_ply,
            h                 = h,
            t_w               = t_w,
            b                 = _b_qty,
            t_f               = _tf_qty,
            f_y               = f_y,
            gamma_M0          = gamma_M0,
            gamma_M1          = float(d.get("gamma_M1", 1.0)),
            beam_results      = beam_results,
            l_cr_ltb          = _l_cr_ltb,
            C1                = float(d.get("C1_ltb", 1.0)),
            ltb_restrained    = _ltb_restrained,
            buck_y_restrained = bool(d.get("buck_y_restrained", False)),
            buck_x_restrained = bool(d.get("buck_x_restrained", False)),
        )

    elif t == "concrete_beam":
        d = block["data"]
        if d.get("direct", False):
            beam_results = {
                "source": "manual input",
                "case_name": "ULS design actions",
                "M_Ed": d["M_Ed_kNm"] * kN * m,
                "V_Ed": d["V_Ed_kN"]  * kN,
            }
            g_k = 0 * kN / m
            q_k = 0 * kN / m
        else:
            beam_results = None
            g_k = d["g_k_kNm"] * kN / m
            q_k = d["q_k_kNm"] * kN / m
        return rc_beam_bending(
            label    = d["label"],
            span     = d["span_m"]     * m,
            g_k      = g_k,
            q_k      = q_k,
            b        = d["b_mm"]       * mm,
            h        = d["h_mm"]       * mm,
            d        = d["d_mm"]       * mm,
            f_ck     = d["f_ck_mpa"]  * MPa,
            f_yk     = d["f_yk_mpa"]  * MPa,
            As_prov  = d["As_prov_mm2"] * mm**2,
            beam_results = beam_results,
        )

    elif t == "masonry_wall":
        d = block["data"]
        return masonry_wall_vertical(
            label     = d["label"],
            height    = d["height_m"]       * m,
            thickness = d["thickness_mm"]   * mm,
            length    = d["length_m"]       * m,
            N_k       = d["N_k_kN"]         * kN,
            f_b       = d["f_b_mpa"]        * MPa,
            f_m       = d["f_m_mpa"]        * MPa,
            gamma_M   = d["gamma_M"],
        )

    elif t == "custom_calc":
        return custom_calc_to_blocks(block.get("data", {}))

    return []


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def build_and_generate_pdf(project: dict, blocks: list) -> bytes:
    # ── Pre-solve all FEM blocks so results are available to linked checks ──
    fem_results = {}
    for block in blocks:
        if block["type"] == "fem_beam":
            lbl = block["data"].get("label","")
            try:
                summary, _ = _run_fem(block["data"])
                fem_results[lbl] = summary
            except Exception as exc:
                fem_results[lbl] = None

    all_blocks = COVER(project) + TOC()

    for block in blocks:
        try:
            result = block_to_report(block, fem_results=fem_results)
            if isinstance(result, list):
                all_blocks.extend(result)
            else:
                all_blocks.append(result)
        except Exception as exc:
            import traceback
            all_blocks.append(NOTE(f"Error in '{block['type']}': {exc}"))

    all_blocks += PAGEBREAK()

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        generate_pdf_holst(project, all_blocks, tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# BLOCK EDITOR WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

def _uid(block, suffix):
    return f"{block['id']}_{suffix}"

def edit_heading(block):
    block["text"] = st.text_input("Heading text", block.get("text","New section"),
                                  key=_uid(block,"ht"))

def edit_text(block):
    block["text"] = st.text_area("Paragraph", block.get("text",""),
                                 key=_uid(block,"tx"), height=80)

def edit_note(block):
    block["text"] = st.text_area("Note / warning", block.get("text",""),
                                 key=_uid(block,"nt"), height=60)

def edit_figure(block):
    block["path"]    = st.text_input("File path (absolute)",
                                     block.get("path",""), key=_uid(block,"fp"))
    block["caption"] = st.text_input("Caption", block.get("caption",""),
                                     key=_uid(block,"fc"))
    if block["path"] and Path(block["path"]).exists():
        st.image(block["path"], width=300)
    elif block["path"]:
        st.warning("File not found.")

def edit_timber_beam_column(block):
    d = block["data"]
    c1, c2, c3 = st.columns(3)
    d["label"]  = c1.text_input("Label", d["label"], key=_uid(block,"label"))
    d["grade"]  = c2.selectbox("Timber grade", TIMBER_GRADES,
                               index=TIMBER_GRADES.index(d["grade"]), key=_uid(block,"grade"))
    d["service_class"] = c3.selectbox("Service class", SERVICE_CLASSES,
                                      index=SERVICE_CLASSES.index(d["service_class"]),
                                      key=_uid(block,"sc"))

    c1, c2, c3, c4 = st.columns(4)
    d["b_mm"]     = c1.number_input("b [mm]",      value=d["b_mm"],     min_value=10.0, key=_uid(block,"b"))
    d["h_mm"]     = c2.number_input("h [mm]",      value=d["h_mm"],     min_value=10.0, key=_uid(block,"h"))
    d["length_m"] = c3.number_input("Length [m]",  value=d["length_m"], min_value=0.1,  key=_uid(block,"len"))
    d["gamma_M"]  = c4.number_input("γ_M",         value=d["gamma_M"],  min_value=1.0,  key=_uid(block,"gM"))

    c1, c2, c3 = st.columns(3)
    d["load_duration"] = c1.selectbox("Load duration", LOAD_DURATIONS,
                                      index=LOAD_DURATIONS.index(d["load_duration"]),
                                      key=_uid(block,"ld"))
    d["N_Ed_kN"]  = c2.number_input("N_Ed [kN]",   value=d["N_Ed_kN"],   key=_uid(block,"N"))
    d["M_Ed_kNm"] = c3.number_input("M_Ed [kN·m]", value=d["M_Ed_kNm"],  key=_uid(block,"M"))

    c1, c2, c3, c4 = st.columns(4)
    d["eff_len"]   = c1.number_input("Eff. length factor", value=d["eff_len"], min_value=0.1, key=_uid(block,"ef"))
    d["k_m"]       = c2.number_input("k_m",                value=d["k_m"],                   key=_uid(block,"km"))
    d["buck_y"]    = c3.checkbox("Buckling (y)", value=d["buck_y"],  key=_uid(block,"by"))
    d["buck_z"]    = c4.checkbox("Buckling (z)", value=d["buck_z"],  key=_uid(block,"bz"))

    d["check_ltb"] = st.checkbox("Check lateral-torsional buckling (LTB)",
                                  value=d["check_ltb"], key=_uid(block,"ltb"))
    if d["check_ltb"]:
        d["l_ef_ltb_m"] = st.number_input("l_ef,ltb [m]", value=d.get("l_ef_ltb_m", d["length_m"]),
                                           min_value=0.1, key=_uid(block,"letb"))

def edit_timber_beam(block):
    d = block["data"]
    c1, c2, c3 = st.columns(3)
    d["label"]  = c1.text_input("Label", d["label"], key=_uid(block,"label"))
    d["grade"]  = c2.selectbox("Timber grade", TIMBER_GRADES,
                               index=TIMBER_GRADES.index(d["grade"]), key=_uid(block,"grade"))
    d["service_class"] = c3.selectbox("Service class", SERVICE_CLASSES,
                                      index=SERVICE_CLASSES.index(d["service_class"]),
                                      key=_uid(block,"sc"))

    c1, c2, c3, c4 = st.columns(4)
    d["b_mm"]    = c1.number_input("b [mm]",   value=d["b_mm"],    min_value=10.0, key=_uid(block,"b"))
    d["h_mm"]    = c2.number_input("h [mm]",   value=d["h_mm"],    min_value=10.0, key=_uid(block,"h"))
    d["span_m"]  = c3.number_input("Span [m]", value=d["span_m"],  min_value=0.1,  key=_uid(block,"span"))
    d["gamma_M"] = c4.number_input("γ_M",      value=d["gamma_M"], min_value=1.0,  key=_uid(block,"gM"))

    d["load_duration"] = st.selectbox("Load duration", LOAD_DURATIONS,
                                      index=LOAD_DURATIONS.index(d["load_duration"]),
                                      key=_uid(block,"ld"))

    MODE_OPTIONS = ["Direct design actions (M_Ed, V_Ed)",
                    "Characteristic loads (g_k, q_k)",
                    "From FEM block"]
    cur_mode = d.get("input_mode","direct")
    mode_idx = {"direct":0,"characteristic":1,"fem":2}.get(cur_mode, 0)
    action_mode = st.radio("Load input method", MODE_OPTIONS,
                            index=mode_idx, key=_uid(block,"mode"))
    d["input_mode"] = {"Direct design actions (M_Ed, V_Ed)":"direct",
                       "Characteristic loads (g_k, q_k)":"characteristic",
                       "From FEM block":"fem"}[action_mode]

    if d["input_mode"] == "direct":
        c1, c2 = st.columns(2)
        d["M_Ed_kNm"] = c1.number_input("M_Ed [kN·m]", value=d.get("M_Ed_kNm",0.0), key=_uid(block,"MEd"))
        d["V_Ed_kN"]  = c2.number_input("V_Ed [kN]",   value=d.get("V_Ed_kN",0.0),  key=_uid(block,"VEd"))
    elif d["input_mode"] == "characteristic":
        c1, c2 = st.columns(2)
        d["g_k_kNm"] = c1.number_input("g_k [kN/m]", value=d.get("g_k_kNm",1.0), min_value=0.0, key=_uid(block,"gk"))
        d["q_k_kNm"] = c2.number_input("q_k [kN/m]", value=d.get("q_k_kNm",1.5), min_value=0.0, key=_uid(block,"qk"))
    else:  # fem
        fem_lbls = _fem_labels_in_session()
        if fem_lbls:
            cur = d.get("fem_label", fem_lbls[0])
            idx = fem_lbls.index(cur) if cur in fem_lbls else 0
            d["fem_label"] = st.selectbox("FEM block", fem_lbls, index=idx,
                                           key=_uid(block,"femlbl"))
            # Preview cached results
            fem_blk = next((b for b in st.session_state.blocks
                            if b["type"]=="fem_beam"
                            and b["data"].get("label")==d["fem_label"]), None)
            if fem_blk and fem_blk["data"].get("res_M_Ed_kNm") is not None:
                fd = fem_blk["data"]
                fc1, fc2, fc3 = st.columns(3)
                fc1.metric("M_Ed", f"{fd['res_M_Ed_kNm']:.3f} kN·m")
                fc2.metric("V_Ed", f"{fd['res_V_Ed_kN']:.3f} kN")
                fc3.metric("δ_max", f"{fd['res_delta_mm']:.3f} mm")
        else:
            st.info("Add a FEM beam block first.")

def edit_steel_beam(block):
    from section_catalog import load_steel_profiles, all_section_names
    d = block["data"]

    # ── Label + grade ──────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    d["label"] = c1.text_input("Label", d.get("label","S1"), key=_uid(block,"label"))

    GRADES = {"S235": 235, "S275": 275, "S355": 355, "S420": 420, "S460": 460}
    grade_keys = list(GRADES.keys())
    cur_grade  = d.get("grade", "S355")
    if cur_grade not in grade_keys:
        cur_grade = "S355"
    d["grade"]   = c2.selectbox("Steel grade", grade_keys,
                                 index=grade_keys.index(cur_grade),
                                 key=_uid(block,"grade"))
    d["gamma_M0"] = c3.number_input("γ_M0", value=float(d.get("gamma_M0", 1.0)),
                                     min_value=0.5, max_value=2.0,
                                     key=_uid(block,"gM0"))

    # ── Section selector ───────────────────────────────────────────────────────
    st.markdown("**Section**")
    db = load_steel_profiles()
    all_keys = list(db.keys())           # e.g. ["IPE80", "IPE100", ...]

    cur_sec = d.get("section", "IPE300").upper().replace(" ","")
    if cur_sec not in all_keys:
        cur_sec = "IPE300"
    sec_idx = all_keys.index(cur_sec)

    # Group selector by family + section
    _fs1, _fs2 = st.columns([2, 1])
    selected_key = _fs1.selectbox(
        "Section",
        all_keys,
        index=sec_idx,
        key=_uid(block,"sec"),
        format_func=lambda k: db[k]["designation"],
    )
    d["section"] = db[selected_key]["designation"]
    sec = db[selected_key]

    # Show section properties from catalog (read-only)
    _fs2.markdown(
        f"<div style='font-size:11px; color:#666; padding-top:6px;'>"
        f"h = {sec['h_mm']:.0f} mm &nbsp;·&nbsp; "
        f"b = {sec['b_mm']:.0f} mm<br>"
        f"t<sub>w</sub> = {sec['tw_mm']:.1f} mm &nbsp;·&nbsp; "
        f"t<sub>f</sub> = {sec['tf_mm']:.1f} mm<br>"
        f"W<sub>pl,y</sub> = <b>{sec['Wply_cm3']:.0f} cm³</b> &nbsp;·&nbsp; "
        f"I<sub>y</sub> = {sec['Iy_cm4']:.0f} cm⁴"
        f"</div>",
        unsafe_allow_html=True,
    )

    f_y_mpa = GRADES[d["grade"]]
    M_Rd_kNm = sec["Wply_cm3"] * 1e-6 * f_y_mpa * 1e3 / d["gamma_M0"]  # kN·m
    st.caption(
        f"f_y = {f_y_mpa} MPa  ·  "
        f"M_Rd = W_pl,y × f_y / γ_M0 = "
        f"{sec['Wply_cm3']:.0f} cm³ × {f_y_mpa} MPa = **{M_Rd_kNm:.1f} kN·m**"
    )

    # ── Span ──────────────────────────────────────────────────────────────────
    d["span_m"] = st.number_input("Span [m]", value=float(d.get("span_m",5.0)),
                                   min_value=0.1, key=_uid(block,"span"))

    # ── Restraint flags ───────────────────────────────────────────────────────
    st.markdown("**Stability restraints**")
    st.caption(
        "Tick each mode that is prevented by continuous or closely-spaced physical "
        "restraints (slab, decking, bracing). Unticked modes appear as warnings in "
        "the report."
    )
    rc1, rc2, rc3 = st.columns(3)
    d["ltb_restrained"]    = rc1.checkbox(
        "Restrained — LTB",
        value=bool(d.get("ltb_restrained", False)),
        key=_uid(block, "ltbr"),
        help="Bottom (compression) flange restrained against lateral displacement → χ_LT = 1.0",
    )
    d["buck_y_restrained"] = rc2.checkbox(
        "Restrained — y-axis",
        value=bool(d.get("buck_y_restrained", False)),
        key=_uid(block, "byr"),
        help="Beam braced against out-of-plane movement (y-direction) by secondary beams/diaphragm",
    )
    d["buck_x_restrained"] = rc3.checkbox(
        "Restrained — x-axis",
        value=bool(d.get("buck_x_restrained", False)),
        key=_uid(block, "bxr"),
        help="Support conditions prevent in-plane buckling (x-direction / plane of bending)",
    )

    # ── LTB parameters (shown when not restrained) ────────────────────────────
    if not d["ltb_restrained"]:
        _family = sec.get("family", "")
        if _family in ("IPE", "HEA", "HEB"):
            st.markdown("**LTB parameters** *(EN 1993-1-1 cl. 6.3.2.2 — general case)*")
            lt1, lt2, lt3 = st.columns(3)
            _lcr_default = float(d.get("l_cr_ltb_m") or d.get("span_m", 5.0))
            d["l_cr_ltb_m"] = lt1.number_input(
                "L_cr  [m]",
                value=_lcr_default,
                min_value=0.1,
                key=_uid(block, "ltblen"),
                help="Effective LTB length = span between lateral restraints to compression flange",
            )
            d["C1_ltb"] = lt2.number_input(
                "C₁ factor",
                value=float(d.get("C1_ltb", 1.0)),
                min_value=0.5, max_value=2.5, step=0.01,
                key=_uid(block, "C1ltb"),
                help=(
                    "Equivalent uniform moment factor:\n"
                    "1.00 = uniform moment (conservative)\n"
                    "1.13 ≈ triangular moment\n"
                    "1.29 ≈ parabolic / UDL mid-span\n"
                    "1.77 = single end moment"
                ),
            )
            d["gamma_M1"] = lt3.number_input(
                "γ_M1",
                value=float(d.get("gamma_M1", 1.0)),
                min_value=0.5, max_value=2.0,
                key=_uid(block, "gM1"),
                help="Partial factor for member stability (EN 1993-1-1 cl. 6.1; = 1.0 in most NAs)",
            )
            # Live LTB preview
            _lcr = d["l_cr_ltb_m"]
            _C1  = d["C1_ltb"]
            _E   = 210_000.0
            _G   = 80_770.0
            _b   = sec["b_mm"]
            _h   = sec["h_mm"]
            _tw  = sec["tw_mm"]
            _tf  = sec["tf_mm"]
            _Wpl = sec["Wply_cm3"] * 1e3   # cm³ → mm³
            _fy  = {"S235":235,"S275":275,"S355":355,"S420":420,"S460":460}.get(d.get("grade","S355"),355)
            _gM1 = d["gamma_M1"]
            try:
                _Iz  = (_tf*_b**3/6 + (_h-2*_tf)*_tw**3/12) * 1e-8    # mm⁴ → cm⁴
                _Iw  = (_b**3*_tf*(_h-_tf)**2/24) * 1e-12              # mm⁶ → m⁶ ... keep in mm⁶ for now
                _It  = ((2*_b*_tf**3+(_h-2*_tf)*_tw**3)/3) * 1e-8     # mm⁴ → cm⁴
                import math as _m
                _Lcr_mm = _lcr * 1e3
                _EIz    = _E * _Iz * 1e-8 * 1e6   # MPa × cm⁴ → N·mm²... easier in SI
                # work in N and mm
                _EIz_mm  = _E * (_Iz * 1e4)          # N/mm² × mm⁴
                _GIt_mm  = _G * (_It * 1e4)          # N/mm² × mm⁴
                _Iw_mm   = _b**3*_tf*(_h-_tf)**2/24  # mm⁶
                _Iz_mm   = _tf*_b**3/6+(_h-2*_tf)*_tw**3/12  # mm⁴
                _Mcr_Nmm = (_C1 * (_m.pi**2*_EIz_mm/_Lcr_mm**2)
                           * (_m.sqrt(_Iw_mm/_Iz_mm + _Lcr_mm**2*_GIt_mm/(_m.pi**2*_EIz_mm))))
                _Mcr_kNm = _Mcr_Nmm * 1e-6
                _lbar    = (_m.sqrt(_Wpl * _fy / (_Mcr_Nmm)))
                if _lbar <= 2.0:
                    hob = _h / _b
                    _aLT = 0.34 if hob <= 2 else 0.49
                    _phi = 0.5*(1 + _aLT*(_lbar-0.2) + _lbar**2)
                    _chi = min(1/(_phi + _m.sqrt(max(_phi**2-_lbar**2, 0.0))), 1.0)
                else:
                    _chi = 0.0
                _Mb_kNm = _chi * _Wpl * _fy / (_gM1 * 1e6)
                _col = "#2a7a4b" if _lbar <= 0.2 else ("#f0a500" if _lbar <= 1.0 else "#b03030")
                st.markdown(
                    f"<p style='font-size:12px; color:{_col};'>"
                    f"M_cr = {_Mcr_kNm:.1f} kN·m  ·  "
                    f"λ̄_LT = {_lbar:.3f}  ·  "
                    f"χ_LT = {_chi:.3f}  ·  "
                    f"<b>M_b,Rd = {_Mb_kNm:.1f} kN·m</b></p>",
                    unsafe_allow_html=True,
                )
            except Exception:
                pass
        else:
            st.caption(
                "ℹ️ LTB calculation is available for IPE / HEA / HEB sections. "
                "For L-profiles, check LTB using specialist tables or software."
            )

    # ── Load input ────────────────────────────────────────────────────────────
    MODE_OPTIONS = ["Direct design actions (M_Ed, V_Ed)",
                    "Characteristic loads (g_k, q_k)",
                    "From FEM block"]
    cur_mode = d.get("input_mode","characteristic")
    mode_idx = {"direct":0,"characteristic":1,"fem":2}.get(cur_mode, 1)
    action_mode = st.radio("Load input method", MODE_OPTIONS,
                            index=mode_idx, key=_uid(block,"mode"))
    d["input_mode"] = {"Direct design actions (M_Ed, V_Ed)":"direct",
                       "Characteristic loads (g_k, q_k)":"characteristic",
                       "From FEM block":"fem"}[action_mode]

    if d["input_mode"] == "direct":
        c1, c2 = st.columns(2)
        d["M_Ed_kNm"] = c1.number_input("M_Ed [kN·m]", value=float(d.get("M_Ed_kNm",0.0)),
                                         key=_uid(block,"MEd"))
        d["V_Ed_kN"]  = c2.number_input("V_Ed [kN]",   value=float(d.get("V_Ed_kN",0.0)),
                                         key=_uid(block,"VEd"))
        # Live check preview
        if d["M_Ed_kNm"] > 0:
            ratio = d["M_Ed_kNm"] / M_Rd_kNm
            color = "#2a7a4b" if ratio <= 1.0 else "#b03030"
            st.markdown(
                f"<p style='font-size:12px; color:{color};'>"
                f"M_Ed / M_Rd = {d['M_Ed_kNm']:.2f} / {M_Rd_kNm:.1f} = "
                f"<b>{ratio:.3f}</b> {'✓ OK' if ratio <= 1.0 else '✗ FAIL'}</p>",
                unsafe_allow_html=True,
            )
    elif d["input_mode"] == "characteristic":
        c1, c2 = st.columns(2)
        d["g_k_kNm"] = c1.number_input("g_k [kN/m]", value=float(d.get("g_k_kNm",5.0)),
                                        min_value=0.0, key=_uid(block,"gk"))
        d["q_k_kNm"] = c2.number_input("q_k [kN/m]", value=float(d.get("q_k_kNm",3.0)),
                                        min_value=0.0, key=_uid(block,"qk"))
        # Live check preview
        w_Ed = 1.35 * d["g_k_kNm"] + 1.5 * d["q_k_kNm"]
        M_Ed_prev = w_Ed * d["span_m"]**2 / 8.0
        ratio = M_Ed_prev / M_Rd_kNm
        color = "#2a7a4b" if ratio <= 1.0 else "#b03030"
        st.caption(
            f"w_Ed = {w_Ed:.2f} kN/m  ·  "
            f"M_Ed = {M_Ed_prev:.1f} kN·m  ·  "
            f"M_Ed / M_Rd = "
        )
        st.markdown(
            f"<p style='font-size:12px; color:{color}; margin-top:-8px;'>"
            f"<b>{ratio:.3f}  {'✓ OK' if ratio <= 1.0 else '✗ FAIL'}</b></p>",
            unsafe_allow_html=True,
        )
    else:  # fem
        fem_lbls = _fem_labels_in_session()
        if fem_lbls:
            cur = d.get("fem_label", fem_lbls[0])
            idx = fem_lbls.index(cur) if cur in fem_lbls else 0
            d["fem_label"] = st.selectbox("FEM block", fem_lbls, index=idx,
                                           key=_uid(block,"femlbl"))
            fem_blk = next((b for b in st.session_state.blocks
                            if b["type"]=="fem_beam"
                            and b["data"].get("label")==d["fem_label"]), None)
            if fem_blk and fem_blk["data"].get("res_M_Ed_kNm") is not None:
                fd = fem_blk["data"]
                fc1, fc2, fc3 = st.columns(3)
                fc1.metric("M_Ed", f"{fd['res_M_Ed_kNm']:.3f} kN·m")
                fc2.metric("V_Ed", f"{fd['res_V_Ed_kN']:.3f} kN")
                fc3.metric("δ_max", f"{fd['res_delta_mm']:.3f} mm")
                # Live check preview from FEM
                ratio = fd["res_M_Ed_kNm"] / M_Rd_kNm
                color = "#2a7a4b" if ratio <= 1.0 else "#b03030"
                st.markdown(
                    f"<p style='font-size:12px; color:{color};'>"
                    f"M_Ed / M_Rd = {fd['res_M_Ed_kNm']:.2f} / {M_Rd_kNm:.1f} = "
                    f"<b>{ratio:.3f}</b> {'✓ OK' if ratio <= 1.0 else '✗ FAIL'}</p>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Add a FEM beam block first.")

def edit_concrete_beam(block):
    d = block["data"]
    c1, c2 = st.columns(2)
    d["label"]   = c1.text_input("Label",    d["label"],    key=_uid(block,"label"))
    d["span_m"]  = c2.number_input("Span [m]", value=d["span_m"], min_value=0.1, key=_uid(block,"span"))

    c1, c2, c3 = st.columns(3)
    d["b_mm"] = c1.number_input("b [mm]", value=d["b_mm"], min_value=10.0, key=_uid(block,"b"))
    d["h_mm"] = c2.number_input("h [mm]", value=d["h_mm"], min_value=10.0, key=_uid(block,"h"))
    d["d_mm"] = c3.number_input("d [mm] (effective depth)", value=d["d_mm"], min_value=10.0, key=_uid(block,"d"))

    c1, c2, c3 = st.columns(3)
    d["f_ck_mpa"]    = c1.number_input("f_ck [MPa]",    value=d["f_ck_mpa"],    key=_uid(block,"fck"))
    d["f_yk_mpa"]    = c2.number_input("f_yk [MPa]",    value=d["f_yk_mpa"],    key=_uid(block,"fyk"))
    d["As_prov_mm2"] = c3.number_input("As,prov [mm²]", value=d["As_prov_mm2"], key=_uid(block,"As"))

    action_mode = st.radio("Load input method",
                           ["Direct design actions (M_Ed, V_Ed)",
                            "Characteristic loads (g_k, q_k)"],
                           index=0 if d.get("direct",False) else 1, key=_uid(block,"direct"))
    d["direct"] = (action_mode == "Direct design actions (M_Ed, V_Ed)")

    if d["direct"]:
        c1, c2 = st.columns(2)
        d["M_Ed_kNm"] = c1.number_input("M_Ed [kN·m]", value=d.get("M_Ed_kNm",0.0), key=_uid(block,"MEd"))
        d["V_Ed_kN"]  = c2.number_input("V_Ed [kN]",   value=d.get("V_Ed_kN",0.0),  key=_uid(block,"VEd"))
    else:
        c1, c2 = st.columns(2)
        d["g_k_kNm"] = c1.number_input("g_k [kN/m]", value=d.get("g_k_kNm",10.0), min_value=0.0, key=_uid(block,"gk"))
        d["q_k_kNm"] = c2.number_input("q_k [kN/m]", value=d.get("q_k_kNm",8.0),  min_value=0.0, key=_uid(block,"qk"))

def edit_masonry_wall(block):
    d = block["data"]
    c1, c2 = st.columns(2)
    d["label"]      = c1.text_input("Label", d["label"], key=_uid(block,"label"))
    d["gamma_M"]    = c2.number_input("γ_M", value=d["gamma_M"], min_value=1.0, key=_uid(block,"gM"))

    c1, c2, c3 = st.columns(3)
    d["height_m"]      = c1.number_input("Height [m]",       value=d["height_m"],      min_value=0.1, key=_uid(block,"ht"))
    d["thickness_mm"]  = c2.number_input("Thickness [mm]",   value=d["thickness_mm"],  min_value=50.0,key=_uid(block,"th"))
    d["length_m"]      = c3.number_input("Length [m]",       value=d["length_m"],      min_value=0.1, key=_uid(block,"ln"))

    c1, c2, c3 = st.columns(3)
    d["N_k_kN"]   = c1.number_input("N_k [kN]",   value=d["N_k_kN"],   key=_uid(block,"Nk"))
    d["f_b_mpa"]  = c2.number_input("f_b [MPa]",  value=d["f_b_mpa"],  key=_uid(block,"fb"))
    d["f_m_mpa"]  = c3.number_input("f_m [MPa]",  value=d["f_m_mpa"],  key=_uid(block,"fm"))

def edit_custom_calc(block):
    d = block["data"]
    d["title"] = st.text_input("Section title", d.get("title","Custom Calculation"),
                               key=_uid(block,"title"))

    # ── Variables ─────────────────────────────────────────────────────────────
    st.markdown("**Variables** *(name, value, unit)*")
    new_vars = []
    for vi, var in enumerate(d.get("vars",[])):
        vc1, vc2, vc3, vc4 = st.columns([2, 2, 2, 1])
        vname = vc1.text_input("Name",  var.get("name",""),     key=_uid(block,f"vn{vi}"),
                               label_visibility="collapsed", placeholder="name  e.g. g_k")
        vval  = vc2.number_input("Value", value=float(var.get("value",0.0)),
                                 key=_uid(block,f"vv{vi}"), label_visibility="collapsed",
                                 format="%.4g")
        vunit = vc3.selectbox("Unit", UNIT_CHOICES,
                              index=UNIT_CHOICES.index(var.get("unit","-")),
                              key=_uid(block,f"vu{vi}"), label_visibility="collapsed",
                              format_func=lambda u: UNIT_LABELS.get(u, u))
        keep  = not vc4.button("✕", key=_uid(block,f"vdel{vi}"), help="Remove")
        if keep:
            new_vars.append({"name": vname, "value": vval, "unit": vunit})
    d["vars"] = new_vars

    if st.button("+ Add variable", key=_uid(block,"vadd")):
        d["vars"].append({"name":"", "value":0.0, "unit":"-"})
        st.experimental_rerun()

    st.markdown("---")

    # ── Formulas ──────────────────────────────────────────────────────────────
    st.markdown("**Formulas** *(write any expression — units flow automatically)*")
    st.caption("Examples:  `w_Ed = 1.35 * g_k + 1.5 * q_k`   ·   `F_Ed = w_Ed * L`   ·   `sigma = F_Ed / A`")
    new_formulas = []
    for fi, formula in enumerate(d.get("formulas",[])):
        fc1, fc2 = st.columns([6, 1])
        fval = fc1.text_input("Formula", formula, key=_uid(block,f"f{fi}"),
                              label_visibility="collapsed",
                              placeholder="e.g.   F_Ed = g_k * L")
        keep = not fc2.button("✕", key=_uid(block,f"fdel{fi}"), help="Remove")
        if keep:
            new_formulas.append(fval)
    d["formulas"] = new_formulas

    if st.button("+ Add formula", key=_uid(block,"fadd")):
        d["formulas"].append("")
        st.experimental_rerun()

    st.markdown("---")

    # ── Live preview ──────────────────────────────────────────────────────────
    active_vars     = [v for v in d["vars"]     if v.get("name","").strip()]
    active_formulas = [f for f in d["formulas"] if f.strip() and "=" in f]

    if active_vars or active_formulas:
        with st.expander("Preview calculation result", expanded=True):
            rows, ns, errs = evaluate_custom_calc(active_vars, active_formulas)
            for name, formula, result in rows:
                if formula:
                    st.markdown(
                        f"<code style='font-size:13px'>"
                        f"<b>{name}</b>  =  {formula}  =  "
                        f"<span style='color:#12788E'><b>{result}</b></span></code>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<code style='font-size:13px'>"
                        f"<b>{name}</b>  =  "
                        f"<span style='color:#12788E'>{result}</span></code>",
                        unsafe_allow_html=True,
                    )
            for e in errs:
                st.error(e)

    st.markdown("---")

    # ── Pass/Fail checks ──────────────────────────────────────────────────────
    st.markdown("**Pass / Fail checks**")
    st.caption("demand: type a variable name or expression  ·  capacity: value + unit")
    new_checks = []
    for ci, chk in enumerate(d.get("checks",[])):
        cc1, cc2, cc3, cc4, cc5 = st.columns([3, 2, 2, 2, 1])
        clabel  = cc1.text_input("Label",    chk.get("label","Check"),
                                 key=_uid(block,f"cl{ci}"), label_visibility="collapsed",
                                 placeholder="Check label")
        cdemand = cc2.text_input("Demand",   chk.get("demand",""),
                                 key=_uid(block,f"cd{ci}"), label_visibility="collapsed",
                                 placeholder="demand variable / expr")
        ccap    = cc3.number_input("Capacity", float(chk.get("capacity",1.0)),
                                   key=_uid(block,f"cc{ci}"), label_visibility="collapsed")
        cunit   = cc4.selectbox("Unit", UNIT_CHOICES,
                                index=UNIT_CHOICES.index(chk.get("unit","-")),
                                key=_uid(block,f"cu{ci}"), label_visibility="collapsed",
                                format_func=lambda u: UNIT_LABELS.get(u, u))
        keep    = not cc5.button("✕", key=_uid(block,f"cdel{ci}"), help="Remove")
        if keep:
            new_checks.append({"label":clabel,"demand":cdemand,
                               "capacity":ccap,"unit":cunit})
    d["checks"] = new_checks

    if st.button("+ Add check", key=_uid(block,"cadd")):
        d["checks"].append({"label":"Check","demand":"","capacity":1.0,"unit":"kN"})
        st.experimental_rerun()


def edit_fem_beam(block):
    d = block["data"]
    SUPPORT_TYPES = ["pin", "roller", "fixed"]
    LOAD_TYPES    = ["udl", "point", "trapezoidal"]
    LOAD_LABELS   = {"udl": "UDL", "point": "Point load", "trapezoidal": "Trapezoidal"}

    # ── Identity ──────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    d["label"]  = c1.text_input("Label", d.get("label","FEM-1"), key=_uid(block,"lbl"))
    d["span_m"] = c2.number_input("Span [m]", value=float(d.get("span_m",6.0)),
                                   min_value=0.1, key=_uid(block,"span"))
    d["n_elements"] = int(c3.number_input("Elements (precision)",
                          value=int(d.get("n_elements",100)),
                          min_value=20, max_value=500, step=10, key=_uid(block,"nel")))

    # ── Stiffness ─────────────────────────────────────────────────────────────
    st.markdown("**Section stiffness — EI**")
    sc1, sc2, sc3 = st.columns(3)
    d["E_mpa"]  = sc1.number_input("E [MPa]", value=float(d.get("E_mpa",210000.0)),
                                    min_value=1.0, key=_uid(block,"E"),
                                    help="Steel ≈ 210 000  |  Timber ≈ 11 000  |  Concrete ≈ 30 000")
    d["I_cm4"]  = sc2.number_input("I [cm⁴]", value=float(d.get("I_cm4",8356.0)),
                                    min_value=0.001, format="%.1f", key=_uid(block,"I"))
    EI = d["E_mpa"] * 1e6 * d["I_cm4"] * 1e-8
    sc3.metric("EI  [kN·m²]", f"{EI/1e3:.0f}")

    # ── Supports ──────────────────────────────────────────────────────────────
    st.markdown("**Supports**")
    # Visible column headers
    _sh1, _sh2, _sh3 = st.columns([2, 2, 1])
    _sh1.caption("Position  x  [m]")
    _sh2.caption("Support type")

    supports = d.setdefault("supports", [])
    new_supports = []
    for si_i, sup in enumerate(supports):
        s1, s2, s3 = st.columns([2, 2, 1])
        xval  = s1.number_input("x [m]", value=float(sup.get("x_m", 0.0)),
                                 min_value=0.0, max_value=float(d["span_m"]),
                                 key=_uid(block, f"sx{si_i}"),
                                 label_visibility="collapsed")
        stype = s2.selectbox("Type", SUPPORT_TYPES,
                             index=SUPPORT_TYPES.index(sup.get("type", "pin")),
                             key=_uid(block, f"st{si_i}"),
                             label_visibility="collapsed")
        keep  = not s3.button("Remove", key=_uid(block, f"sdel{si_i}"))
        if keep:
            new_supports.append({"x_m": xval, "type": stype})
    d["supports"] = new_supports
    if st.button("+ Add support", key=_uid(block, "sadd")):
        d["supports"].append({"x_m": d["span_m"], "type": "roller"})
        st.experimental_rerun()

    # ── Loads ─────────────────────────────────────────────────────────────────
    st.markdown("**Loads  (ULS combination applied automatically)**")
    loads = d.setdefault("loads", [])
    new_loads = []
    for li, load in enumerate(loads):
        ltype    = load.get("type", "udl")
        lc0, lc_rest, lc_del = st.columns([2, 7, 1])
        new_type = lc0.selectbox("Type", LOAD_TYPES,
                                  index=LOAD_TYPES.index(ltype),
                                  key=_uid(block, f"ltype{li}"),
                                  label_visibility="collapsed",
                                  format_func=lambda t: LOAD_LABELS[t])
        load["type"] = new_type

        with lc_rest:
            if new_type == "udl":
                # Visible column headers
                h1,h2,h3,h4,h5,h6 = st.columns(6)
                h1.caption("g_k  [kN/m]")
                h2.caption("q_k  [kN/m]")
                h3.caption("γ_G")
                h4.caption("γ_Q")
                h5.caption("x₁  [m]")
                h6.caption("x₂  [m]")
                u1,u2,u3,u4,u5,u6 = st.columns(6)
                load["g_k_kNm"] = u1.number_input("g_k", value=float(load.get("g_k_kNm", 5.0)),
                                                   key=_uid(block, f"lgk{li}"),
                                                   label_visibility="collapsed")
                load["q_k_kNm"] = u2.number_input("q_k", value=float(load.get("q_k_kNm", 3.0)),
                                                   key=_uid(block, f"lqk{li}"),
                                                   label_visibility="collapsed")
                load["gamma_G"] = u3.number_input("γ_G", value=float(load.get("gamma_G", 1.35)),
                                                   key=_uid(block, f"lgG{li}"),
                                                   label_visibility="collapsed")
                load["gamma_Q"] = u4.number_input("γ_Q", value=float(load.get("gamma_Q", 1.50)),
                                                   key=_uid(block, f"lgQ{li}"),
                                                   label_visibility="collapsed")
                load["x1_m"]   = u5.number_input("x1",  value=float(load.get("x1_m", 0.0)),
                                                   key=_uid(block, f"lx1{li}"),
                                                   label_visibility="collapsed")
                load["x2_m"]   = u6.number_input("x2",  value=float(load.get("x2_m", d["span_m"])),
                                                   key=_uid(block, f"lx2{li}"),
                                                   label_visibility="collapsed")
                w_Ed = load["gamma_G"] * load["g_k_kNm"] + load["gamma_Q"] * load["q_k_kNm"]
                st.caption(
                    f"w_Ed = {load['gamma_G']}×{load['g_k_kNm']} "
                    f"+ {load['gamma_Q']}×{load['q_k_kNm']} = **{w_Ed:.3f} kN/m**"
                )

            elif new_type == "point":
                ph1, ph2 = st.columns(2)
                ph1.caption("P_Ed  [kN]  (design load)")
                ph2.caption("Position  x  [m]")
                p1, p2 = st.columns(2)
                load["P_Ed_kN"] = p1.number_input("P_Ed [kN]",
                                                   value=float(load.get("P_Ed_kN", 10.0)),
                                                   key=_uid(block, f"lP{li}"),
                                                   label_visibility="collapsed")
                load["x_m"]     = p2.number_input("x [m]",
                                                   value=float(load.get("x_m", d["span_m"] / 2)),
                                                   key=_uid(block, f"lpx{li}"),
                                                   label_visibility="collapsed")

            elif new_type == "trapezoidal":
                # Two rows of headers for 8 narrow columns
                th1,th2,th3,th4,th5,th6,th7,th8 = st.columns(8)
                th1.caption("g_k₁ [kN/m]")
                th2.caption("q_k₁ [kN/m]")
                th3.caption("g_k₂ [kN/m]")
                th4.caption("q_k₂ [kN/m]")
                th5.caption("γ_G")
                th6.caption("γ_Q")
                th7.caption("x₁ [m]")
                th8.caption("x₂ [m]")
                t1,t2,t3,t4,t5,t6,t7,t8 = st.columns(8)
                load["g_k1_kNm"] = t1.number_input("g_k1", value=float(load.get("g_k1_kNm", 5.0)),
                                                    key=_uid(block, f"lgk1{li}"),
                                                    label_visibility="collapsed")
                load["q_k1_kNm"] = t2.number_input("q_k1", value=float(load.get("q_k1_kNm", 3.0)),
                                                    key=_uid(block, f"lqk1{li}"),
                                                    label_visibility="collapsed")
                load["g_k2_kNm"] = t3.number_input("g_k2", value=float(load.get("g_k2_kNm", 0.0)),
                                                    key=_uid(block, f"lgk2{li}"),
                                                    label_visibility="collapsed")
                load["q_k2_kNm"] = t4.number_input("q_k2", value=float(load.get("q_k2_kNm", 0.0)),
                                                    key=_uid(block, f"lqk2{li}"),
                                                    label_visibility="collapsed")
                load["gamma_G"]  = t5.number_input("γ_G",  value=float(load.get("gamma_G", 1.35)),
                                                    key=_uid(block, f"ltgG{li}"),
                                                    label_visibility="collapsed")
                load["gamma_Q"]  = t6.number_input("γ_Q",  value=float(load.get("gamma_Q", 1.50)),
                                                    key=_uid(block, f"ltgQ{li}"),
                                                    label_visibility="collapsed")
                load["x1_m"]     = t7.number_input("x1",   value=float(load.get("x1_m", 0.0)),
                                                    key=_uid(block, f"ltx1{li}"),
                                                    label_visibility="collapsed")
                load["x2_m"]     = t8.number_input("x2",   value=float(load.get("x2_m", d["span_m"])),
                                                    key=_uid(block, f"ltx2{li}"),
                                                    label_visibility="collapsed")

        keep = not lc_del.button("Remove", key=_uid(block, f"ldel{li}"))
        if keep:
            new_loads.append(load)
    d["loads"] = new_loads

    lcols = st.columns(3)
    for i, (lbl, ltype_default) in enumerate([
        ("+ UDL", "udl"), ("+ Point load", "point"), ("+ Trapezoidal", "trapezoidal")
    ]):
        if lcols[i].button(lbl, key=_uid(block, f"ladd{ltype_default}")):
            defaults = {
                "udl":         {"type":"udl","g_k_kNm":5.0,"q_k_kNm":3.0,
                                 "gamma_G":1.35,"gamma_Q":1.50,
                                 "x1_m":0.0,"x2_m":d["span_m"]},
                "point":       {"type":"point","P_Ed_kN":10.0,"x_m":d["span_m"]/2},
                "trapezoidal": {"type":"trapezoidal","g_k1_kNm":5.0,"q_k1_kNm":3.0,
                                 "g_k2_kNm":0.0,"q_k2_kNm":0.0,
                                 "gamma_G":1.35,"gamma_Q":1.50,
                                 "x1_m":0.0,"x2_m":d["span_m"]},
            }
            d["loads"].append(defaults[ltype_default])
            st.experimental_rerun()

    # ── Live beam layout preview ───────────────────────────────────────────────
    if d.get("supports") or d.get("loads"):
        try:
            preview_png = _beam_layout_preview_bytes(d)
            st.image(preview_png, use_column_width=True)
        except Exception:
            pass  # silent — don't clutter UI with preview errors

    # ── Run FEM + show results ─────────────────────────────────────────────────
    st.markdown("---")
    can_run = len(d.get("supports", [])) >= 2 and len(d.get("loads", [])) >= 1
    if can_run:
        try:
            summary, beam = _run_fem(d)
            # Cache results into block data
            d["res_M_Ed_kNm"]  = summary["M_Ed_Nm"]     / 1e3
            d["res_V_Ed_kN"]   = summary["V_Ed_N"]      / 1e3
            d["res_delta_mm"]  = summary["delta_max_m"] * 1e3
            d["res_x_M_m"]     = summary["x_M_Ed_m"]
            d["res_x_V_m"]     = summary["x_V_Ed_m"]
            d["res_x_delta_m"] = summary["x_delta_max_m"]

            # Key result metrics
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("M_Ed",  f"{d['res_M_Ed_kNm']:.3f} kN·m",
                                f"at x = {d['res_x_M_m']:.3f} m")
            rc2.metric("V_Ed",  f"{d['res_V_Ed_kN']:.3f} kN",
                                f"at x = {d['res_x_V_m']:.3f} m")
            rc3.metric("δ_max", f"{d['res_delta_mm']:.3f} mm",
                                f"at x = {d['res_x_delta_m']:.3f} m")

            # Results diagram (4-panel, compact)
            png = _fem_plot_bytes(beam, title=d["label"])
            st.image(png, use_column_width=True)

        except Exception as exc:
            st.error(f"FEM error: {exc}")
    else:
        st.caption("Add at least 2 supports and 1 load to run the analysis.")


EDITORS = {
    "heading":            edit_heading,
    "text":               edit_text,
    "note":               edit_note,
    "figure":             edit_figure,
    "fem_beam":           edit_fem_beam,
    "timber_beam_column": edit_timber_beam_column,
    "timber_beam":        edit_timber_beam,
    "steel_beam":         edit_steel_beam,
    "concrete_beam":      edit_concrete_beam,
    "masonry_wall":       edit_masonry_wall,
    "custom_calc":        edit_custom_calc,
}

ICONS = {
    "heading":            "",
    "text":               "",
    "note":               "",
    "figure":             "",
    "pagebreak":          "",
    "timber_beam_column": "",
    "timber_beam":        "",
    "steel_beam":         "",
    "concrete_beam":      "",
    "masonry_wall":       "",
    "custom_calc":        "",
}

LABELS = {
    "heading":            "Section heading",
    "text":               "Paragraph",
    "note":               "Note",
    "figure":             "Figure",
    "pagebreak":          "Page break",
    "fem_beam":           "FEM beam analysis",
    "timber_beam_column": "Timber beam-column — EN 1995",
    "timber_beam":        "Timber beam — EN 1995",
    "steel_beam":         "Steel beam IPE / HEA / HEB / L — EN 1993",
    "concrete_beam":      "Concrete beam — EN 1992",
    "masonry_wall":       "Masonry wall — EN 1996",
    "custom_calc":        "Custom calculation",
}

def _block_summary(block) -> str:
    t = block["type"]
    if t in ("heading","text","note"):
        return block.get("text","")[:60]
    if t == "custom_calc":
        return block.get("data",{}).get("title","")
    if t in ("timber_beam_column","timber_beam","steel_beam","concrete_beam","masonry_wall"):
        d = block.get("data",{})
        return d.get("label","")
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — PROJECT METADATA
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    logo_path = BASE_DIR / "Billede2.png"
    if logo_path.exists():
        st.image(str(logo_path), width=140)
    st.markdown("## Project")

    proj_firm     = st.text_input("Firm",        "Your Firm",       key="proj_firm")
    proj_project  = st.text_input("Project / Sag", "Project Name",  key="proj_project")
    proj_title    = st.text_input("Title",        "Structural Calculations", key="proj_title")
    proj_section  = st.text_input("Afsnit",       "",               key="proj_section",
                                  help="Document section shown in the Afsnit header cell")
    proj_ref      = st.text_input("Sagsnr / Ref", "SC-2025-001",    key="proj_ref")
    proj_rev      = st.text_input("Revision",     "A",              key="proj_rev")
    proj_standard = st.text_input("Standard",     "EN 1990 / EN 1995-1-1", key="proj_std")

    st.markdown("### People & dates")
    proj_engineer      = st.text_input("Beregnet af",     "",  key="proj_eng")
    proj_checker       = st.text_input("Kontrolleret af", "",  key="proj_chk")
    proj_approver      = st.text_input("Godkendt af",     "",  key="proj_apr")
    proj_date          = st.text_input("Dato",            date.today().strftime("%d/%m/%Y"), key="proj_date")
    proj_checker_date  = st.text_input("Dato (kontrol)",  date.today().strftime("%d/%m/%Y"), key="proj_chk_date")
    proj_approver_date = st.text_input("Dato (godkendt)", date.today().strftime("%d/%m/%Y"), key="proj_apr_date")

    st.markdown("### Firm contact")
    proj_address = st.text_input("Address", "", key="proj_address")
    proj_phone   = st.text_input("Phone",   "", key="proj_phone")
    proj_cvr     = st.text_input("CVR",     "", key="proj_cvr")
    proj_email   = st.text_input("Email",   "", key="proj_email")

    PROJECT = {
        "firm":           proj_firm,
        "project":        proj_project,
        "title":          proj_title,
        "section":        proj_section or proj_title,
        "ref":            proj_ref,
        "revision":       proj_rev,
        "standard":       proj_standard,
        "engineer":       proj_engineer,
        "checker":        proj_checker,
        "approver":       proj_approver or proj_checker,
        "date":           proj_date,
        "checker_date":   proj_checker_date,
        "approver_date":  proj_approver_date,
        "address":        proj_address,
        "phone":          proj_phone,
        "cvr":            proj_cvr,
        "email":          proj_email,
    }

    st.markdown("---")
    out_name = st.text_input("PDF filename", "report.pdf", key="out_name")
    if not out_name.endswith(".pdf"):
        out_name += ".pdf"

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — HEADER + GENERATE BUTTON
# ─────────────────────────────────────────────────────────────────────────────

col_h, col_btn = st.columns([4, 1])
with col_h:
    st.markdown(
        f"<h1 style='font-size:22px; font-weight:700; letter-spacing:0.02em; margin-bottom:2px;'>"
        f"Report Builder</h1>"
        f"<p style='font-size:12px; color:#999; margin-top:0;'>"
        f"{proj_project} &nbsp;·&nbsp; {proj_ref} &nbsp;·&nbsp; Rev {proj_rev}"
        f"</p>",
        unsafe_allow_html=True,
    )
with col_btn:
    st.markdown("<div style='padding-top:14px'>", unsafe_allow_html=True)
    gen_btn = st.button("Generate PDF", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if gen_btn:
    if not st.session_state.blocks:
        st.warning("Add at least one block before generating.")
    else:
        with st.spinner("Building PDF..."):
            try:
                pdf_bytes = build_and_generate_pdf(PROJECT, st.session_state.blocks)
                st.download_button(
                    label    = f"Download  {out_name}",
                    data     = pdf_bytes,
                    file_name= out_name,
                    mime     = "application/pdf",
                    use_container_width=True,
                )
            except Exception as exc:
                import traceback
                st.error(f"PDF generation failed: {exc}")
                st.code(traceback.format_exc())

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — BLOCK LIST
# ─────────────────────────────────────────────────────────────────────────────

if not st.session_state.blocks:
    st.markdown(
        "<p style='color:#bbb; font-size:13px; padding:24px 0;'>"
        "No blocks yet — use Add block below to start building your report."
        "</p>",
        unsafe_allow_html=True,
    )

to_delete = set()

for i, block in enumerate(st.session_state.blocks):
    t       = block["type"]
    label   = LABELS.get(t, t)
    summary = _block_summary(block)
    header  = f"**{label}**" + (f"  —  {summary}" if summary else "")

    with st.expander(header, expanded=(t == "custom_calc" and not summary)):
        if t == "pagebreak":
            st.caption("A page break will be inserted here.")
        elif t in EDITORS:
            EDITORS[t](block)

        st.markdown("")
        bc1, bc2, bc3, _ = st.columns([1, 1, 1, 5])
        if bc1.button("Up", key=f"up_{block['id']}", help="Move up") and i > 0:
            lst = st.session_state.blocks
            lst[i], lst[i-1] = lst[i-1], lst[i]
            st.experimental_rerun()
        if bc2.button("Down", key=f"dn_{block['id']}", help="Move down") \
                and i < len(st.session_state.blocks) - 1:
            lst = st.session_state.blocks
            lst[i], lst[i+1] = lst[i+1], lst[i]
            st.experimental_rerun()
        if bc3.button("Delete", key=f"del_{block['id']}"):
            to_delete.add(block["id"])

if to_delete:
    st.session_state.blocks = [b for b in st.session_state.blocks
                                if b["id"] not in to_delete]
    st.experimental_rerun()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN — ADD BLOCK
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<p style='font-size:11px; letter-spacing:0.08em; text-transform:uppercase; "
    "color:#999; margin-bottom:8px;'>Add block</p>",
    unsafe_allow_html=True,
)

menu_keys   = [k for k in BLOCK_MENU]
add_col1, add_col2 = st.columns([4, 1])

selected = add_col1.selectbox(
    "Block type", menu_keys,
    format_func=lambda k: k,
    label_visibility="collapsed",
    key="add_select",
)
add_pressed = add_col2.button("Add", use_container_width=True, key="add_btn")

if add_pressed:
    btype = BLOCK_MENU.get(selected)
    if btype is not None:
        st.session_state.blocks.append(_default_block(btype))
        st.experimental_rerun()
    else:
        st.warning("Please select a block type (not a separator).")
