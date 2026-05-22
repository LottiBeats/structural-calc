"""
calc_core.py — PDF renderer and block helpers.
Renders handcalcs LaTeX output into clean ReportLab PDF rows.

All material modules import helpers from here.

Block helpers available for use in report.py and calc modules
─────────────────────────────────────────────────────────────
COVER(project)          Cover page  — place first in your blocks list
TOC()                   Table of contents page — place after COVER()
PAGEBREAK()             Explicit page break
H1(text)                Bold free-text heading (for narrative sections)
S(text)                 Section heading (within a calc module)
T(content)              Normal paragraph — usable anywhere in the report
N(content)              Amber note/warning box
TBL(headers, rows)      Data table
MH(title, sub, mat)     Module header bar
hc_block(latex, label)  Rendered handcalc equation block
FIG(path, caption)      Embedded figure
"""

import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, Image,
    PageBreak, NextPageTemplate,
)
from reportlab.platypus.tableofcontents import TableOfContents

# ─────────────────────────────────────────────────────────────
# LOGO PATH
# ─────────────────────────────────────────────────────────────

_BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = str(_BASE_DIR / "omkreds_logo.png")

# ─────────────────────────────────────────────────────────────
# COLOURS  — minimal palette
# ─────────────────────────────────────────────────────────────

ORANGE = colors.HexColor("#E74825")   # OMKREDS primary orange

# Minimal neutral palette — no coloured fills in content area
C = {
    # text
    "text_dark":    colors.HexColor("#1C1C1E"),
    "text_mid":     colors.HexColor("#6E6E73"),
    "text_light":   colors.HexColor("#AEAEB2"),
    # OMKREDS orange (used sparingly as accent lines)
    "orange":       ORANGE,
    "orange_light": colors.HexColor("#FEF4F2"),
    # rules / dividers
    "rule_mid":     colors.HexColor("#C8C8CC"),
    "rule_light":   colors.HexColor("#E5E5EA"),
    # status colours — text only, no fills
    "pass_text":    colors.HexColor("#1A7F37"),
    "fail_text":    colors.HexColor("#CF1124"),
    "amber_text":   colors.HexColor("#B45309"),
    # keeps
    "green_dark":   colors.HexColor("#1C1C1E"),
    "green_mid":    colors.HexColor("#6E6E73"),
    "green_light":  colors.white,
    "green_bdr":    colors.HexColor("#E5E5EA"),
    "pass_bg":      colors.white,
    "pass_bdr":     colors.HexColor("#E5E5EA"),
    "fail_bg":      colors.white,
    "fail_bdr":     colors.HexColor("#E5E5EA"),
    "amber_bg":     colors.white,
    "amber_bdr":    ORANGE,
    "gray_light":   colors.HexColor("#F5F5F5"),
    "gray_mid":     colors.HexColor("#E5E5EA"),
    "text_main":    colors.HexColor("#1C1C1E"),
    "text_muted":   colors.HexColor("#6E6E73"),
}

# Material accent colours — used only for thin left rules / underlines
MATERIAL_COLORS = {
    "steel":    colors.HexColor("#12788E"),   # teal
    "timber":   colors.HexColor("#AE3419"),   # dark orange-brown
    "concrete": colors.HexColor("#595F61"),   # mid grey
    "masonry":  colors.HexColor("#731F0D"),   # deep brown-orange
    "general":  ORANGE,                       # OMKREDS orange
}

# ─────────────────────────────────────────────────────────────
# BLOCK HELPERS
# ─────────────────────────────────────────────────────────────

def COVER(project):
    """Cover page. Place first in your blocks list."""
    return [{"type": "cover", "project": project}]

def TOC():
    """Table of contents page. Place after COVER()."""
    return [{"type": "toc"}]

def PAGEBREAK():
    """Explicit page break — insert anywhere between blocks."""
    return [{"type": "pagebreak"}]

def H1(text):
    """Bold free-text heading. Returns a list so it can be concatenated with +."""
    return [{"type": "h1", "content": text}]

def S(text):    return {"type": "section",  "content": text}
def T(content): return {"type": "text",     "content": content}
def N(content): return {"type": "note",     "content": content}
def TBL(headers, rows): return {"type": "table", "headers": headers, "rows": rows}
def MH(title, subtitle, material="general"):
    return {"type": "module_header", "title": title,
            "subtitle": subtitle, "material": material}

def hc_block(latex, label=""):
    return {"type": "handcalc", "latex": latex, "label": label}

def FIG(path, caption="", width_mm=170):
    return {"type": "figure", "path": path, "caption": caption, "width_mm": width_mm}

def CALC_ROW(name, formula="", result="", label=""):
    """Single pre-parsed calculation row — bypasses LaTeX entirely.
    name    : variable name, e.g. 'F_Ed'
    formula : symbolic expression, e.g. 'g_k × L'  (empty for a bare assignment)
    result  : formatted result string, e.g. '19.44 kN'
    label   : optional small annotation below the row
    """
    return {"type": "calc_row", "name": name, "formula": formula,
            "result": result, "label": label}


# ─────────────────────────────────────────────────────────────
# CHECK CONTEXT
# ─────────────────────────────────────────────────────────────

class CheckContext:
    def check(self, label, demand, capacity):
        try:
            ratio = float(demand / capacity)
        except Exception:
            ratio = 999
        ratio  = round(ratio, 3)
        passes = ratio <= 1.0
        status = f"{ratio:.3f} < 1.0   OK" if passes else f"{ratio:.3f} > 1.0   FAIL"
        return {"type": "check", "label": label, "passes": passes, "value": status}

    def check_bool(self, label, passes, ok_text="OK", fail_text="FAIL"):
        return {
            "type": "check",
            "label": label,
            "passes": bool(passes),
            "value": ok_text if passes else fail_text,
        }


# ─────────────────────────────────────────────────────────────
# LATEX → PLAIN TEXT RENDERER
# ─────────────────────────────────────────────────────────────

# Supports up to 3 levels of brace nesting so \frac{1}{\sqrt{k^2-\lambda_{rel}^2}}
# is matched correctly.  Each _Ln adds one more level of depth.
_L1 = r'[^{}]*'
_L2 = r'(?:[^{}]|\{' + _L1 + r'\})*'
_L3 = r'(?:[^{}]|\{' + _L2 + r'\})*'
_FRAC_INNER = r'(?:[^{}]|\{' + _L3 + r'\})*'

def _latex_to_plain(latex):
    """Convert handcalcs LaTeX to a list of plain-text calc lines."""
    body = re.sub(r'\\begin\{aligned\}|\\end\{aligned\}|(?<!\\)\\\[|(?<!\\)\\\]', '', latex)
    raw_parts = [p.strip() for p in re.split(r'\\\\\s*(?:\[[\w.]+\])?', body) if p.strip()]

    groups = []
    for part in raw_parts:
        cols = [c.strip() for c in part.split('&')]
        if cols[0] == '' and groups:
            groups[-1].extend(cols[1:])
        else:
            groups.append(cols)

    def clean(s):
        s = re.sub(r'\\text\w*\{([^}]+)\}', '', s)
        s = re.sub(r'\\mathrm\{([^}]+)\}',  r'\1', s)
        s = re.sub(r'\\[hv]space\*?\{[^}]+\}', '', s)
        s = re.sub(r'\\(?:d|t)?frac\s*\{(' + _FRAC_INNER + r')\}\s*\{(' + _FRAC_INNER + r')\}',
                   r'(\1)/(\2)', s)
        s = re.sub(r'\\sqrt\{([^}]+)\}',    r'√(\1)', s)
        s = re.sub(r'_\{([^}]+)\}',         r'_\1',   s)
        s = re.sub(r'\\sqrt\s*\{([^}]+)\}', r'√(\1)', s)
        s = re.sub(r'\^\{([^}]+)\}',        r'^\1',   s)
        s = re.sub(r'\{([^}]+)\}',          r'\1',    s)
        s = re.sub(r'[{}]',                 '',       s)
        s = re.sub(r'\\[,;:!]',             '',       s)
        s = re.sub(r'\\(?:quad|qquad)\b',   ' ',      s)
        s = re.sub(r'\\cdot',               ' × ',    s)
        s = re.sub(r'\\times',              ' × ',    s)
        s = re.sub(r'\\left\(|\\right\)',   '',       s)
        s = re.sub(r'\\cdot',               ' × ',     s)
        s = re.sub(r'\\times',              ' × ',     s)
        s = re.sub(r'\\left\s*([\(\)\[\]])',  r'\1',   s)
        s = re.sub(r'\\right\s*([\(\)\[\]])', r'\1',   s)
        greek = {'alpha':'α','beta':'β','gamma':'γ','delta':'δ',
                 'epsilon':'ε','zeta':'ζ','eta':'η','theta':'θ',
                 'lambda':'λ','mu':'μ','nu':'ν','xi':'ξ','pi':'π',
                 'rho':'ρ','sigma':'σ','tau':'τ','phi':'φ','chi':'χ',
                 'psi':'ψ','omega':'ω','Gamma':'Γ','Delta':'Δ',
                 'Sigma':'Σ','Phi':'Φ','Omega':'Ω'}
        for name, sym in greek.items():
            s = re.sub(r'\\' + name + r'(?![a-zA-Z])', sym, s)
        s = re.sub(r'\blambda_rel(?=_[a-zA-Z0-9,]+|\b)', 'λ_rel', s)
        s = re.sub(r'\blrel(?=_[a-zA-Z0-9,]+|\b)', 'λ_rel', s)
        s = re.sub(r'\bsigma(?=_[a-zA-Z0-9,]+|\b)', 'σ', s)
        s = re.sub(r'\bsig(?=_[a-zA-Z0-9,]+|\b)', 'σ', s)
        s = re.sub(r'\bphi(?=_[a-zA-Z0-9,]+|\b)', 'φ', s)
        s = re.sub(r'\bbeta(?=_[a-zA-Z0-9,]+|\b)', 'β', s)
        s = s.replace('$$', '')
        s = re.sub(r'\\',                   '',       s)
        s = re.sub(r'\[[\w.]+\]',           '',       s)
        s = re.sub(r'\^\s*\((\d+)\)\s*/\s*\((\d+)\)', r'^(\1/\2)', s)
        s = re.sub(r'\^(-?)1\.666+\d*', r'^(\g<1>5/3)', s)
        s = re.sub(r'\^(-?)1\.333+\d*', r'^(\g<1>4/3)', s)
        s = re.sub(r'\^(-?)0\.666+\d*', r'^(\g<1>2/3)', s)
        s = re.sub(r'\^(-?)0\.333+\d*', r'^(\g<1>1/3)', s)
        s = re.sub(r'\s+',                  ' ',      s).strip()
        return s

    lines = []
    for cols in groups:
        cleaned = []
        for i, c in enumerate(cols):
            c = clean(c)
            if i > 0 and c.startswith('='):
                c = c[1:].strip()
            if c and c != '=':
                cleaned.append(c)
        if cleaned:
            lines.append(cleaned)
    return lines


# ─────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────

def make_styles():
    return {
        # ── content styles ──────────────────────────────────
        "normal":     ParagraphStyle("normal",    fontName="Helvetica",        fontSize=9,   leading=13, textColor=C["text_dark"],  spaceAfter=2),
        "note":       ParagraphStyle("note",      fontName="Helvetica-Oblique",fontSize=8.5, leading=12, textColor=C["text_mid"],   spaceAfter=2),
        "section":    ParagraphStyle("section",   fontName="Helvetica-Bold",   fontSize=8,   leading=12, textColor=C["text_mid"],   spaceBefore=5, spaceAfter=1),
        "hc_var":     ParagraphStyle("hc_var",    fontName="Courier-Bold",     fontSize=9,   leading=12, textColor=C["text_dark"]),
        "hc_sym":     ParagraphStyle("hc_sym",    fontName="Courier",          fontSize=8.5, leading=12, textColor=C["text_mid"]),
        "hc_res":     ParagraphStyle("hc_res",    fontName="Courier-Bold",     fontSize=9,   leading=12, textColor=C["text_dark"]),
        "hc_lbl":     ParagraphStyle("hc_lbl",    fontName="Helvetica",        fontSize=7,   leading=10, textColor=C["text_light"]),
        "hc_eq":      ParagraphStyle("hc_eq",     fontName="Helvetica",        fontSize=8.5, leading=12, textColor=C["text_light"]),
        "check_pass": ParagraphStyle("check_pass",fontName="Helvetica-Bold",   fontSize=8.5, leading=11, textColor=C["pass_text"]),
        "check_fail": ParagraphStyle("check_fail",fontName="Helvetica-Bold",   fontSize=8.5, leading=11, textColor=C["fail_text"]),
        "th":         ParagraphStyle("th",        fontName="Helvetica-Bold",   fontSize=8,   leading=10, textColor=C["text_dark"], alignment=TA_CENTER),
        "td":         ParagraphStyle("td",        fontName="Helvetica",        fontSize=8,   leading=10, textColor=C["text_dark"]),
        "mod_title":  ParagraphStyle("mod_title", fontName="Helvetica-Bold",   fontSize=10,  leading=13, textColor=C["text_dark"]),
        "mod_sub":    ParagraphStyle("mod_sub",   fontName="Helvetica",        fontSize=7.5, leading=10, textColor=C["text_mid"],  alignment=TA_RIGHT),
        # ── free-text heading ────────────────────────────────
        "h1":         ParagraphStyle("h1",        fontName="Helvetica-Bold",   fontSize=11,  leading=15, textColor=C["text_dark"], spaceBefore=6, spaceAfter=3),
        # ── TOC styles ───────────────────────────────────────
        "toc_heading": ParagraphStyle("toc_heading", fontName="Helvetica-Bold", fontSize=16, leading=20,
                                      textColor=C["text_dark"], spaceBefore=0, spaceAfter=10),
        "toc_entry_0": ParagraphStyle("toc_entry_0", fontName="Helvetica-Bold", fontSize=9.5, leading=16,
                                      textColor=C["text_dark"],  leftIndent=0),
        "toc_entry_1": ParagraphStyle("toc_entry_1", fontName="Helvetica-Bold", fontSize=8.5, leading=13,
                                      textColor=C["text_mid"], leftIndent=6*mm),
        "toc_entry_2": ParagraphStyle("toc_entry_2", fontName="Helvetica",      fontSize=8,   leading=12,
                                      textColor=C["text_mid"], leftIndent=14*mm),
    }


# ─────────────────────────────────────────────────────────────
# HANDCALC BLOCK RENDERER
# ─────────────────────────────────────────────────────────────

def _fmt(s):
    """Convert _sub / ^sup notation to ReportLab <sub>/<super> tags."""
    s = re.sub(r'\^\(([^)]+)\)', r'<super>\1</super>', s)
    s = re.sub(r'\^([^ <]+)', r'<super>\1</super>', s)
    s = re.sub(r'_([^ <]+)', r'<sub>\1</sub>', s)
    return s


def _render_hc_block(b, styles):
    rows_out = []
    parsed   = _latex_to_plain(b["latex"])

    for cols in parsed:
        if not cols:
            continue

        if len(cols) == 1:
            var_name    = ""
            rest        = ""
            result_part = cols[0]
        elif len(cols) == 2:
            var_name    = cols[0]
            rest        = ""
            result_part = cols[1]
        else:
            var_name    = cols[0]
            rest        = cols[1]
            if len(rest) > 80:
                rest = rest[:77] + '…'
            result_part = cols[-1]

        cells  = []
        widths = []

        cells.append(Paragraph(_fmt(var_name), styles["hc_var"]))
        widths.append(26*mm)

        if rest:
            cells.append(Paragraph("=", styles["hc_eq"]))
            widths.append(4*mm)
            cells.append(Paragraph(_fmt(rest), styles["hc_sym"]))
            widths.append(86*mm)
            cells.append(Paragraph("=", styles["hc_eq"]))
            widths.append(4*mm)
            cells.append(Paragraph(_fmt(result_part), styles["hc_res"]))
            widths.append(30*mm)
        else:
            cells.append(Paragraph("=", styles["hc_eq"]))
            widths.append(4*mm)
            cells.append(Paragraph(_fmt(result_part), styles["hc_res"]))
            widths.append(120*mm)

        tbl = Table([cells], colWidths=widths, rowHeights=[7*mm])
        tbl.setStyle(TableStyle([
            ("LEFTPADDING",   (0,0),(-1,-1), 4),
            ("RIGHTPADDING",  (0,0),(-1,-1), 3),
            ("TOPPADDING",    (0,0),(-1,-1), 1),
            ("BOTTOMPADDING", (0,0),(-1,-1), 1),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
            # subtle bottom rule only — no background fill
            ("LINEBELOW",     (0,0),(-1,-1), 0.3, C["rule_light"]),
        ]))
        rows_out.append(tbl)
        rows_out.append(Spacer(1, 0.5*mm))

    if b.get("label"):
        label_p = Paragraph(b["label"], styles["hc_lbl"])
        rows_out = [label_p, Spacer(1, 0.5*mm)] + rows_out

    rows_out.append(Spacer(1, 1.5*mm))
    return rows_out


# ─────────────────────────────────────────────────────────────
# COVER PAGE DRAWING
# ─────────────────────────────────────────────────────────────

def _draw_cover(canvas, doc, project):
    W, H = A4
    canvas.saveState()

    # dark top band (~44 % of page height)
    band_h = H * 0.44
    canvas.setFillColor(C["text_dark"])
    canvas.rect(0, H - band_h, W, band_h, fill=1, stroke=0)

    # OMKREDS logo PNG
    logo_w = 68 * mm
    logo_h = 34 * mm
    logo_x = W * 0.08
    logo_y = H - band_h * 0.38
    canvas.drawImage(
        LOGO_PATH, logo_x, logo_y, width=logo_w, height=logo_h,
        preserveAspectRatio=True,
        mask=[245, 255, 245, 255, 245, 255],
    )

    # firm name
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 11)
    canvas.drawCentredString(W / 2, H - band_h * 0.72, project["firm"])

    # orange accent rule at band bottom
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(1.8)
    canvas.line(15 * mm, H - band_h, W - 15 * mm, H - band_h)

    # project name
    canvas.setFillColor(ORANGE)
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawCentredString(W / 2, H - band_h - 28 * mm, project["project"])

    # report title
    canvas.setFillColor(C["text_dark"])
    canvas.setFont("Helvetica", 12)
    canvas.drawCentredString(W / 2, H - band_h - 43 * mm, project["title"])

    # thin separator
    canvas.setStrokeColor(C["rule_light"])
    canvas.setLineWidth(0.5)
    canvas.line(35 * mm, H - band_h - 53 * mm, W - 35 * mm, H - band_h - 53 * mm)

    # ref / revision
    canvas.setFillColor(C["text_mid"])
    canvas.setFont("Helvetica", 10)
    canvas.drawCentredString(
        W / 2, H - band_h - 64 * mm,
        f"{project['ref']}   ·   Rev {project['revision']}"
    )

    # detail rows
    detail_y   = H - band_h - 82 * mm
    col_label  = W / 2 - 48 * mm
    col_value  = W / 2 - 10 * mm
    for label, value in [
        ("Engineer:", project["engineer"]),
        ("Checker:",  project["checker"]),
        ("Date:",     project["date"]),
    ]:
        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(C["text_mid"])
        canvas.drawString(col_label, detail_y, label)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(C["text_dark"])
        canvas.drawString(col_value, detail_y, value)
        detail_y -= 9 * mm

    # standards
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C["text_mid"])
    canvas.drawCentredString(W / 2, detail_y - 8 * mm, project["standard"])

    # bottom strip
    strip_h = 14 * mm
    canvas.setFillColor(C["gray_light"])
    canvas.rect(0, 0, W, strip_h, fill=1, stroke=0)
    canvas.setStrokeColor(C["rule_light"])
    canvas.setLineWidth(0.5)
    canvas.line(0, strip_h, W, strip_h)
    canvas.setFillColor(C["fail_text"])
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawCentredString(W / 2, strip_h / 2 - 3, "PRELIMINARY — NOT FOR CONSTRUCTION")

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────
# CONTENT PAGE HEADER / FOOTER
# ─────────────────────────────────────────────────────────────

def _draw_header_footer(canvas, doc, project):
    W, H = A4
    canvas.saveState()

    # Top bar — dark, slim
    bar_h = 13 * mm
    canvas.setFillColor(C["text_dark"])
    canvas.rect(0, H - bar_h, W, bar_h, fill=1, stroke=0)

    # Logo
    ly = H - bar_h / 2
    logo_h = bar_h * 0.78
    logo_w = logo_h * 2.2
    canvas.drawImage(
        LOGO_PATH, 10 * mm, ly - logo_h / 2, width=logo_w, height=logo_h,
        preserveAspectRatio=True,
        mask=[245, 255, 245, 255, 245, 255],
    )

    # ref + page right-aligned in top bar
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(W - 13 * mm, ly - 3,
        f"{project['ref']}  ·  Rev {project['revision']}  ·  p. {doc.page}")

    # Slim meta strip below bar
    sub_h = 5.5 * mm
    canvas.setFillColor(C["gray_light"])
    canvas.rect(0, H - bar_h - sub_h, W, sub_h, fill=1, stroke=0)
    canvas.setFillColor(C["text_mid"])
    canvas.setFont("Helvetica", 6)
    meta = (f"{project['project']}   ·   {project['title']}   ·   "
            f"Eng: {project['engineer']}   ·   Chk: {project['checker']}   ·   {project['date']}")
    canvas.drawString(13 * mm, H - bar_h - sub_h + 1.6 * mm, meta)

    # Footer — single thin rule + text
    canvas.setStrokeColor(C["rule_light"])
    canvas.setLineWidth(0.4)
    canvas.line(13 * mm, 11 * mm, W - 13 * mm, 11 * mm)
    canvas.setFillColor(C["text_light"])
    canvas.setFont("Helvetica", 6.5)
    canvas.drawString(13 * mm, 7 * mm, f"{project['firm']}  ·  {project['ref']}")
    canvas.drawRightString(W - 13 * mm, 7 * mm, "PRELIMINARY — NOT FOR CONSTRUCTION")

    canvas.restoreState()


def make_page_template(project):
    def _draw(canvas, doc):
        _draw_header_footer(canvas, doc, project)
    return _draw


# ─────────────────────────────────────────────────────────────
# TOC ANCHOR
# ─────────────────────────────────────────────────────────────

from reportlab.platypus import Flowable as _Flowable

class _TocAnchor(_Flowable):
    """Zero-size flowable that registers a TOC entry when rendered."""
    def __init__(self, level, text):
        _Flowable.__init__(self)
        self.level = level
        self.text  = text
        self.width = 0
        self.height = 0

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        pass


# ─────────────────────────────────────────────────────────────
# DOCUMENT TEMPLATE
# ─────────────────────────────────────────────────────────────

class StructuralDocTemplate(BaseDocTemplate):
    def __init__(self, filename, project, **kwargs):
        self.project = project
        BaseDocTemplate.__init__(self, filename, **kwargs)

        W, H = A4

        cover_frame = Frame(
            15 * mm, 20 * mm, W - 30 * mm, H - 40 * mm,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id='cover_frame',
        )
        content_frame = Frame(
            15 * mm, 20 * mm, W - 30 * mm, H - 45 * mm,
            leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
            id='content_frame',
        )

        self.addPageTemplates([
            PageTemplate(
                id='cover',
                frames=[cover_frame],
                onPage=lambda c, d: _draw_cover(c, d, self.project),
            ),
            PageTemplate(
                id='content',
                frames=[content_frame],
                onPage=lambda c, d: _draw_header_footer(c, d, self.project),
            ),
        ])

    def multiBuild(self, story, filename=None, canvasmaker=None, maxPasses=10):
        import copy
        from reportlab.pdfgen import canvas as _rl_canvas
        if canvasmaker is None:
            canvasmaker = _rl_canvas.Canvas
        toc = getattr(self, '_toc', None)
        for i in range(maxPasses):
            if toc:
                toc.beforeBuild()
            self._toc_counter = 0
            self.build(copy.deepcopy(story), canvasmaker=canvasmaker)
            if toc is None or toc.isSatisfied():
                break
        else:
            raise IndexError(f"TOC not resolved after {maxPasses} passes")

    def afterFlowable(self, flowable):
        if isinstance(flowable, _TocAnchor):
            self._toc_counter = getattr(self, '_toc_counter', 0) + 1
            key = f'toc_{self._toc_counter}'
            self.canv.bookmarkPage(key)
            toc = getattr(self, '_toc', None)
            if toc is not None:
                toc.addEntry(flowable.level, flowable.text, self.page, key)


# ─────────────────────────────────────────────────────────────
# STORY BUILDER
# ─────────────────────────────────────────────────────────────

def build_story(all_blocks, styles):
    story = []
    for b in all_blocks:
        t = b["type"]

        # ── structural page blocks ────────────────────────────

        if t == "cover":
            story.append(Spacer(1, 0.001))
            story.append(NextPageTemplate('content'))
            story.append(PageBreak())

        elif t == "toc":
            toc = TableOfContents()
            toc.levelStyles = [styles["toc_entry_0"], styles["toc_entry_1"], styles["toc_entry_2"]]
            story.append(Paragraph("Contents", styles["toc_heading"]))
            story.append(Spacer(1, 2 * mm))
            story.append(toc)
            story.append(PageBreak())

        elif t == "pagebreak":
            story.append(PageBreak())

        elif t == "h1":
            story.append(_TocAnchor(0, b["content"]))
            story.append(Spacer(1, 3 * mm))
            story.append(Paragraph(b["content"], styles["h1"]))
            story.append(HRFlowable(width="100%", thickness=0.8,
                color=C["text_dark"], spaceAfter=2))

        # ── calc blocks ───────────────────────────────────────

        elif t == "module_header":
            story.append(_TocAnchor(1, b["title"]))
            accent = MATERIAL_COLORS.get(b["material"], MATERIAL_COLORS["general"])

            # Minimal header: title left, subtitle right, colored bottom rule
            tbl = Table(
                [[Paragraph(b["title"],    styles["mod_title"]),
                  Paragraph(b["subtitle"], styles["mod_sub"])]],
                colWidths=[115*mm, 55*mm], rowHeights=[8.5*mm]
            )
            tbl.setStyle(TableStyle([
                ("LEFTPADDING",   (0,0),(-1,-1), 2),
                ("RIGHTPADDING",  (0,0),(-1,-1), 2),
                ("TOPPADDING",    (0,0),(-1,-1), 0),
                ("BOTTOMPADDING", (0,0),(-1,-1), 0),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                ("ALIGN",         (1,0),(1,0),   "RIGHT"),
                # Colored bottom rule replaces the fill
                ("LINEBELOW",     (0,0),(-1,-1), 1.5, accent),
            ]))
            story.append(Spacer(1, 5*mm))
            story.append(tbl)
            story.append(Spacer(1, 2.5*mm))

        elif t == "section":
            story.append(_TocAnchor(2, b["content"]))
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(b["content"].upper(), styles["section"]))
            story.append(HRFlowable(width="100%", thickness=0.3,
                color=C["rule_mid"], spaceAfter=1.5))

        elif t == "text":
            _txt = b["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
            story.append(Paragraph(_txt, styles["normal"]))

        elif t == "note":
            # Left-rule only — no filled box
            _ntxt = b["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
            tbl = Table([[Paragraph(_ntxt, styles["note"])]],
                        colWidths=[170*mm])
            tbl.setStyle(TableStyle([
                ("LINEBEFORE",   (0,0),(0,-1), 2.5, C["orange"]),
                ("LEFTPADDING",  (0,0),(-1,-1), 8),
                ("RIGHTPADDING", (0,0),(-1,-1), 6),
                ("TOPPADDING",   (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ]))
            story.append(KeepTogether([tbl, Spacer(1, 1.5*mm)]))

        elif t == "handcalc":
            story.extend(_render_hc_block(b, styles))

        elif t == "calc_row":
            name    = b.get("name", "")
            formula = b.get("formula", "")
            result  = b.get("result", "")
            lbl     = b.get("label", "")

            if formula:
                cells  = [Paragraph(_fmt(name),    styles["hc_var"]),
                          Paragraph("=",            styles["hc_eq"]),
                          Paragraph(_fmt(formula),  styles["hc_sym"]),
                          Paragraph("=",            styles["hc_eq"]),
                          Paragraph(_fmt(result),   styles["hc_res"])]
                widths = [26*mm, 4*mm, 86*mm, 4*mm, 30*mm]
            else:
                cells  = [Paragraph(_fmt(name),    styles["hc_var"]),
                          Paragraph("=",            styles["hc_eq"]),
                          Paragraph(_fmt(result),   styles["hc_res"])]
                widths = [26*mm, 4*mm, 120*mm]

            tbl = Table([cells], colWidths=widths, rowHeights=[7*mm])
            tbl.setStyle(TableStyle([
                ("LEFTPADDING",   (0,0),(-1,-1), 4),
                ("RIGHTPADDING",  (0,0),(-1,-1), 3),
                ("TOPPADDING",    (0,0),(-1,-1), 1),
                ("BOTTOMPADDING", (0,0),(-1,-1), 1),
                ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
                # No fill — just a thin bottom rule
                ("LINEBELOW",     (0,0),(-1,-1), 0.3, C["rule_light"]),
            ]))
            if lbl:
                story.append(Paragraph(lbl, styles["hc_lbl"]))
                story.append(Spacer(1, 0.5*mm))
            story.append(tbl)
            story.append(Spacer(1, 0.5*mm))

        elif t == "check":
            accent = C["pass_text"]   if b["passes"] else C["fail_text"]
            sty    = styles["check_pass"] if b["passes"] else styles["check_fail"]

            # No background fill — left accent rule + thin bottom line
            tbl = Table(
                [[Paragraph(b["label"], styles["normal"]),
                  Paragraph(b["value"], sty)]],
                colWidths=[130*mm, 40*mm], rowHeights=[7.5*mm]
            )
            tbl.setStyle(TableStyle([
                ("LINEBEFORE",   (0,0),(0,-1), 2,   accent),
                ("LINEBELOW",    (0,0),(-1,-1), 0.3, C["rule_light"]),
                ("LEFTPADDING",  (0,0),(-1,-1), 6),
                ("RIGHTPADDING", (0,0),(-1,-1), 6),
                ("TOPPADDING",   (0,0),(-1,-1), 2),
                ("BOTTOMPADDING",(0,0),(-1,-1), 2),
                ("ALIGN",  (1,0),(1,0), "RIGHT"),
                ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
            ]))
            story.append(KeepTogether([tbl, Spacer(1, 1*mm)]))

        elif t == "table":
            rows = [[Paragraph(h, styles["th"]) for h in b["headers"]]]
            for row in b["rows"]:
                rows.append([Paragraph(str(c), styles["td"]) for c in row])
            cw = 170*mm / len(b["headers"])
            tbl = Table(rows, colWidths=[cw]*len(b["headers"]))
            tbl.setStyle(TableStyle([
                # Header: no fill — just thick bottom rule + bold text
                ("LINEBELOW",      (0,0),(-1,0),  1.0, C["text_dark"]),
                # Data rows: alternating very-light tint
                ("ROWBACKGROUNDS", (0,1),(-1,-1),
                    [colors.white, colors.HexColor("#F5F5F5")]),
                # Light grid lines (horizontal only)
                ("LINEBELOW",      (0,1),(-1,-1), 0.3, C["rule_light"]),
                ("LEFTPADDING",    (0,0),(-1,-1), 5),
                ("RIGHTPADDING",   (0,0),(-1,-1), 5),
                ("TOPPADDING",     (0,0),(-1,-1), 3),
                ("BOTTOMPADDING",  (0,0),(-1,-1), 3),
                ("VALIGN",         (0,0),(-1,-1), "MIDDLE"),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 3*mm))

        elif t == "figure":
            img = Image(b["path"])
            target_w = b.get("width_mm", 170) * mm
            scale = target_w / img.imageWidth
            img.drawWidth = target_w
            img.drawHeight = img.imageHeight * scale
            flow = [img]
            caption = b.get("caption", "")
            if caption:
                flow.append(Spacer(1, 1.2*mm))
                flow.append(Paragraph(caption, styles["note"]))
            flow.append(Spacer(1, 2.5*mm))
            story.append(KeepTogether(flow))

    return story


# ─────────────────────────────────────────────────────────────
# GENERATE PDF
# ─────────────────────────────────────────────────────────────

def generate_pdf(project, all_blocks, output_path="structural_report.pdf"):
    doc = StructuralDocTemplate(
        output_path,
        project=project,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=25*mm,  bottomMargin=20*mm,
        title=project["title"],
        author=project["engineer"],
    )
    styles = make_styles()
    story  = build_story(all_blocks, styles)
    doc._toc = next((fl for fl in story if isinstance(fl, TableOfContents)), None)
    doc.multiBuild(story)
    print(f"PDF saved: {output_path}")
