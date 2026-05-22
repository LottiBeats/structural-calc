"""
app.py — OMKREDS Structural Report Generator
Local Streamlit web app.  Run with:  streamlit run app.py
"""

import sys, math, io, os, tempfile, json, base64
from datetime import date
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import streamlit as st

# Streamlit < 1.27 uses experimental_rerun; >= 1.27 uses rerun
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import db as _db
_db.init_db()

# â"€â"€ units â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
import forallpeople as si
try:
    si.environment("structural", top_level=True)
except KeyError:
    pass

import builtins as _builtins
# Snapshot the forallpeople unit names so custom-calc eval can find them
_UNIT_NS = {k: v for k, v in vars(_builtins).items() if not k.startswith("_")}
_UNIT_NS.update({
    "pi": math.pi, "e": math.e,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "exp": math.exp, "log": math.log,
    "abs": abs, "min": min, "max": max, "round": round,
})

# â"€â"€ calc modules â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
import pandas as pd
from calc_core import (COVER, TOC, PAGEBREAK, H1, T, N as NOTE, FIG, TBL,
                       CheckContext, S, CALC_ROW)
from holst_layout import generate_pdf_holst
from beam_fem import BeamFEM, summarise_beam_actions
from timber import timber_beam as _timber_beam
from timber_column import timber_column_bending_and_axial
from steel import steel_beam_ipe
from concrete import rc_beam_bending
from concrete_column import concrete_column_rect
from masonry import masonry_wall_vertical, masonry_wall_ritter
from templates import DOC_TEMPLATES
from streamlit_sortables import sort_items as _sort_items

# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# CONSTANTS
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

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
    "Concrete column  (EN 1992)": "concrete_column",
    "Masonry wall  (EN 1996)": "masonry_wall",
    "Masonry wall Ritter  (EN 1996)": "masonry_ritter",
    "— Content —": None,
    "Custom calculation": "custom_calc",
    "Python script": "python_calc",
    "Section heading": "heading",
    "Paragraph text": "text",
    "Note / warning": "note",
    "Figure / image": "figure",
    "Table": "table",
    "— Layout —": None,
    "Page break": "pagebreak",
}

# Starter template shown in new Python script blocks
_PYTHON_CALC_STARTER = """\
import numpy as np
import matplotlib.pyplot as plt

# Pre-imported: np, pd, plt, scipy
# print() output and matplotlib figures are captured automatically.

x = np.linspace(0, 10, 300)
y = np.sin(x) * np.exp(-0.1 * x)

fig, ax = plt.subplots(figsize=(7, 3))
ax.plot(x, y, color="#032E38")
ax.set_xlabel("x")
ax.set_ylabel("y")
ax.set_title("Example — replace with your calculation")
ax.grid(True, alpha=0.3)
plt.tight_layout()

print(f"Peak: {y.max():.4f}  at  x = {x[y.argmax()]:.2f}")
"""

# ── Danish structural documentation classification (DS/EN 1990 DK NA) ──────
DOC_DEFS = {
    "A1": "Projektgrundlag",
    "A2": "Statiske beregninger",
    "A3": "Konstruktionstegninger og modeller",
    "A4": "Konstruktionsaendringer",
    "B1": "Statisk projekteringsrapport",
    "B2": "Statisk kontrolrapport",
    "B3": "Statisk tilsynsrapport",
}
DOC_GROUPS = [
    ("Konstruktionsdokumentation", ["A1", "A2", "A3", "A4"]),
    ("Projektdokumentation",       ["B1", "B2", "B3"]),
]

def _empty_documents():
    return {doc_id: {"title": title, "blocks": [], "subdocs": []}
            for doc_id, title in DOC_DEFS.items()}


# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# PAGE CONFIG & STYLING
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

st.set_page_config(
    page_title="Structural Report Generator",
    page_icon=None,
    layout="wide",
)

st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
header { background: transparent !important; box-shadow: none !important; }

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

# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# SESSION STATE
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

if "blocks" not in st.session_state:
    st.session_state.blocks = []
if "_id" not in st.session_state:
    st.session_state._id = 0
if "active_doc" not in st.session_state:
    st.session_state.active_doc = None
if "documents" not in st.session_state:
    st.session_state.documents = _empty_documents()
if "projects" not in st.session_state:
    st.session_state.projects = _db.load_all_projects()
if "active_project_id" not in st.session_state:
    st.session_state.active_project_id = None
if "current_user" not in st.session_state:
    st.session_state.current_user = ""
if "active_subdoc" not in st.session_state:
    st.session_state.active_subdoc = None
if "_add_panel_open" not in st.session_state:
    st.session_state._add_panel_open = True

# ── project-save / load helpers ───────────────────────────────────────────────

_PROJ_KEYS = [
    "proj_firm", "proj_project", "proj_title", "proj_section",
    "proj_ref",  "proj_rev",     "proj_std",
    "proj_eng",  "proj_chk",     "proj_apr",
    "proj_date", "proj_chk_date","proj_apr_date",
    "proj_address","proj_phone", "proj_cvr",  "proj_email",
]

def _project_to_json() -> bytes:
    """Serialise all projects to UTF-8 JSON (v4)."""
    _save_active_project()
    payload = {"version": 4, "projects": st.session_state.projects}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

def _apply_loaded_project(data: dict):
    """Write loaded JSON data into session_state (v4 / v3 / legacy)."""
    import uuid as _uuid

    def _reassign_ids(blocks):
        out = []
        for b in (blocks or []):
            b = dict(b)
            st.session_state._id += 1
            b["id"] = st.session_state._id
            out.append(b)
        return out

    def _fix_docs(raw):
        docs = _empty_documents()
        if isinstance(raw, dict):
            for did in DOC_DEFS:
                if did in raw:
                    docs[did]["blocks"] = _reassign_ids(raw[did].get("blocks", []))
                    docs[did]["subdocs"] = raw[did].get("subdocs", [])
        return docs

    def _advance_id_past_subdocs(projects):
        """Ensure _id is higher than any block id inside subdocs (which skip _reassign_ids).

        Subdoc blocks keep their original integer ids from the database.  If _id
        is not advanced past them, _new_id() can return an id that's already in
        use → StreamlitDuplicateElementKey when the same key suffix is shared.
        """
        max_seen = st.session_state._id
        for proj in projects:
            for did, doc in proj.get("documents", {}).items():
                for sd in doc.get("subdocs", []):
                    for b in sd.get("blocks", []):
                        try:
                            bid = int(b.get("id", 0))
                            if bid > max_seen:
                                max_seen = bid
                        except (TypeError, ValueError):
                            pass
        st.session_state._id = max_seen

    v = data.get("version", 1)
    if v == 4:
        projects = data.get("projects", [])
        for proj in projects:
            raw_docs = proj.get("documents", {})
            proj["documents"] = {
                did: {
                    "title":   _empty_documents()[did]["title"],
                    "blocks":  _reassign_ids(raw_docs.get(did, {}).get("blocks", [])),
                    "subdocs": raw_docs.get(did, {}).get("subdocs", []),
                }
                for did in DOC_DEFS
            }
        _advance_id_past_subdocs(projects)
        st.session_state.projects = projects
    else:
        # v3 / v2 / v1 — wrap as a single project
        meta = data.get("project", {})
        docs = _fix_docs(data.get("documents")) if "documents" in data \
               else _fix_docs({"A2": {"blocks": data.get("blocks", [])}})
        proj = {
            "id":       _uuid.uuid4().hex[:8],
            "metadata": {k: meta.get(k, "") for k in _PROJ_KEYS},
            "documents": {did: {"title": docs[did]["title"],
                                "blocks": docs[did]["blocks"]} for did in DOC_DEFS},
            "created":  str(date.today()),
        }
        st.session_state.projects = [proj]
        _advance_id_past_subdocs([proj])

    st.session_state.active_project_id = None
    st.session_state.active_doc = None
    st.session_state.blocks = []
    # Persist all imported projects to the database
    _user = st.session_state.get("current_user", "")
    for _p in st.session_state.projects:
        _db.save_project(_p, user=_user)

# Handle a pending load triggered in a previous run
if "_pending_load" in st.session_state:
    _apply_loaded_project(st.session_state.pop("_pending_load"))

# ─────────────────────────────────────────────────────────────────────────────

def _new_id():
    st.session_state._id += 1
    return st.session_state._id

def _open_document(doc_id):
    """Switch to editing the given document (save current blocks first)."""
    current = st.session_state.get("active_doc")
    if current:
        st.session_state.documents[current]["blocks"] = list(st.session_state.blocks)
    st.session_state.blocks = list(st.session_state.documents[doc_id]["blocks"])
    st.session_state.active_doc = doc_id
    st.rerun()

def _close_document():
    """Return to the dashboard, saving current blocks into the active document."""
    active = st.session_state.get("active_doc")
    active_subdoc = st.session_state.get("active_subdoc")
    if active:
        if active_subdoc is not None:
            subdocs = st.session_state.documents[active].get("subdocs", [])
            if active_subdoc < len(subdocs):
                subdocs[active_subdoc]["blocks"] = list(st.session_state.blocks)
        else:
            st.session_state.documents[active]["blocks"] = list(st.session_state.blocks)
    st.session_state.active_doc = None
    st.session_state.active_subdoc = None
    st.session_state.blocks = []
    st.session_state.pop("_pdf_preview", None)
    st.rerun()

def _load_template(doc_id):
    """Load the built-in template for doc_id, replacing its current blocks."""
    if doc_id not in DOC_TEMPLATES:
        return
    new_blocks = []
    for b in DOC_TEMPLATES[doc_id]:
        nb = dict(b)
        nb["id"] = _new_id()
        new_blocks.append(nb)
    # Save any currently open document first
    current = st.session_state.get("active_doc")
    if current and current != doc_id:
        st.session_state.documents[current]["blocks"] = list(st.session_state.blocks)
    st.session_state.documents[doc_id]["blocks"] = new_blocks
    st.session_state.blocks = list(new_blocks)
    st.session_state.active_doc = doc_id
    st.rerun()

# ── Project-level navigation helpers ─────────────────────────────────────────

def _project_by_id(pid):
    for p in st.session_state.projects:
        if p["id"] == pid:
            return p
    return None

def _save_active_project():
    """Sync current sidebar state + live documents back into the projects list."""
    pid = st.session_state.get("active_project_id")
    if not pid:
        return
    proj = _project_by_id(pid)
    if proj is None:
        return
    proj["metadata"] = {k: st.session_state.get(k, "") for k in _PROJ_KEYS}
    active = st.session_state.get("active_doc")
    active_subdoc = st.session_state.get("active_subdoc")
    if active:
        if active_subdoc is not None:
            subdocs = st.session_state.documents[active].get("subdocs", [])
            if active_subdoc < len(subdocs):
                subdocs[active_subdoc]["blocks"] = list(st.session_state.blocks)
        else:
            st.session_state.documents[active]["blocks"] = list(st.session_state.blocks)
    proj["documents"] = {
        did: {
            "title":   st.session_state.documents[did]["title"],
            "blocks":  list(st.session_state.documents[did]["blocks"]),
            "subdocs": list(st.session_state.documents[did].get("subdocs", [])),
        }
        for did in DOC_DEFS
    }
    # Persist to database (fast — <1 ms for typical project sizes)
    _db.save_project(proj, user=st.session_state.get("current_user", ""))

def _new_project(name="New Project", ref=""):
    import uuid as _uuid
    pid = _uuid.uuid4().hex[:8]
    meta = {k: "" for k in _PROJ_KEYS}
    meta["proj_project"] = name
    meta["proj_ref"]     = ref
    meta["proj_rev"]     = "A"
    meta["proj_std"]     = "EN 1990 / EN 1995-1-1"
    meta["proj_date"]    = date.today().strftime("%d/%m/%Y")
    meta["proj_chk_date"] = date.today().strftime("%d/%m/%Y")
    meta["proj_apr_date"] = date.today().strftime("%d/%m/%Y")
    docs = _empty_documents()
    return {
        "id":       pid,
        "metadata": meta,
        "documents": {did: {"title": docs[did]["title"], "blocks": [], "subdocs": []}
                      for did in DOC_DEFS},
        "created":  str(date.today()),
    }

def _open_project(pid):
    """Load a project into session state and navigate to its dashboard."""
    _save_active_project()
    proj = _project_by_id(pid)
    if proj is None:
        return
    for k in _PROJ_KEYS:
        st.session_state[k] = proj["metadata"].get(k, "")
    docs = _empty_documents()
    for did in DOC_DEFS:
        if did in proj["documents"]:
            docs[did]["blocks"] = list(proj["documents"][did].get("blocks", []))
            docs[did]["subdocs"] = list(proj["documents"][did].get("subdocs", []))
    st.session_state.documents = docs

    # Advance _id counter past every block id already in the project so that
    # _new_id() never returns an id that's already in use.  Block ids are
    # integers when created by _new_id() / _reassign_ids but may be UUID hex
    # strings when inserted from the library — only integer ids can conflict.
    _max_id = st.session_state._id
    for _did, _doc in docs.items():
        for _blk in _doc.get("blocks", []):
            try:
                _max_id = max(_max_id, int(_blk["id"]))
            except (TypeError, ValueError, KeyError):
                pass
        for _sd in _doc.get("subdocs", []):
            for _blk in _sd.get("blocks", []):
                try:
                    _max_id = max(_max_id, int(_blk["id"]))
                except (TypeError, ValueError, KeyError):
                    pass
    st.session_state._id = _max_id
    st.session_state.blocks = []
    st.session_state.active_doc = None
    st.session_state.active_subdoc = None
    st.session_state.active_project_id = pid
    st.session_state.pop("_pdf_preview", None)
    st.rerun()

def _close_project():
    """Save current project and return to the front page."""
    _save_active_project()
    st.session_state.active_project_id = None
    st.session_state.active_doc = None
    st.session_state.active_subdoc = None
    st.session_state.blocks = []
    st.session_state.pop("_pdf_preview", None)
    st.rerun()

def _open_subdoc(subdoc_idx: int):
    """Open a specific sub-document within the currently active document."""
    active_doc = st.session_state.get("active_doc")
    if not active_doc:
        return
    # Save blocks from current subdoc (if any) before switching
    cur_subdoc = st.session_state.get("active_subdoc")
    if cur_subdoc is not None:
        subdocs = st.session_state.documents[active_doc].get("subdocs", [])
        if cur_subdoc < len(subdocs):
            subdocs[cur_subdoc]["blocks"] = list(st.session_state.blocks)
    # Load the target subdoc
    subdocs = st.session_state.documents[active_doc].get("subdocs", [])
    if 0 <= subdoc_idx < len(subdocs):
        st.session_state.blocks = list(subdocs[subdoc_idx].get("blocks", []))
    st.session_state.active_subdoc = subdoc_idx
    st.session_state.pop("_pdf_preview", None)
    st.rerun()

def _close_subdoc():
    """Return from a sub-document to its parent document's subdoc dashboard."""
    active_doc = st.session_state.get("active_doc")
    active_subdoc = st.session_state.get("active_subdoc")
    if active_doc and active_subdoc is not None:
        subdocs = st.session_state.documents[active_doc].get("subdocs", [])
        if active_subdoc < len(subdocs):
            subdocs[active_subdoc]["blocks"] = list(st.session_state.blocks)
    st.session_state.blocks = []
    st.session_state.active_subdoc = None
    st.session_state.pop("_pdf_preview", None)
    st.rerun()

def _add_subdoc(doc_id: str, name: str, adopt_blocks: bool = True):
    """Append a new sub-document to *doc_id*. If adopt_blocks, moves the
    document's current top-level blocks into the first subdoc instead."""
    doc = st.session_state.documents[doc_id]
    subdocs = doc.setdefault("subdocs", [])
    existing_blocks = list(doc.get("blocks", []))
    new_subdoc = {"name": name.strip() or f"Sub-document {len(subdocs) + 1}", "blocks": []}
    if adopt_blocks and not subdocs and existing_blocks:
        # First subdoc: inherit the document's current blocks
        new_subdoc["blocks"] = existing_blocks
        doc["blocks"] = []
    subdocs.append(new_subdoc)
    st.rerun()

def _delete_subdoc(doc_id: str, subdoc_idx: int):
    """Remove a sub-document (cannot undo!)."""
    doc = st.session_state.documents[doc_id]
    subdocs = doc.get("subdocs", [])
    if 0 <= subdoc_idx < len(subdocs):
        subdocs.pop(subdoc_idx)
    st.rerun()

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
    elif btype == "concrete_column":
        base["data"] = {
            "label":"C1",
            "h_mm":300.0,"b_mm":360.0,"c_mm":53.0,
            "da_c_mm":16.0,"n_c":2,
            "da_t_mm":16.0,"n_t":3,
            "fck_mpa":35.0,"fyk_mpa":550.0,
            "gamma_c":1.4,"gamma_s":1.2,
            "Ls_mm":4000.0,"beta_eff":1.0,
            "RH":0.55,"t0_days":28.0,"M0Eqp_over_M0Ed":0.9,
            "load_cases":[
                {"label":"A","NEd_kN":850.0,"M0Ed_kNm":39.0},
                {"label":"B","NEd_kN":900.0,"M0Ed_kNm":42.0},
                {"label":"C","NEd_kN":950.0,"M0Ed_kNm":45.0},
            ],
        }
    elif btype == "masonry_wall":
        base["data"] = {
            "label":"MW1","height_m":2.7,"thickness_mm":150.0,"length_m":1.0,
            "N_k_kN":30.0,"f_b_mpa":10.0,"f_m_mpa":4.0,"gamma_M":2.5,
        }
    elif btype == "masonry_ritter":
        base["data"] = {
            "label":"MR1",
            "b_m":1.0,"t_ef_mm":150.0,"h_ef_mm":2700.0,"e_m_mm":10.0,
            "N_Ed_kN":80.0,
            "f_b_mpa":10.0,"f_m_mpa":4.0,
            "K":0.55,"gamma_M":2.5,"K1":0.9,
        }
    elif btype == "custom_calc":
        base["data"] = {
            "title": "Custom Calculation",
            "items": [],
        }
    elif btype == "python_calc":
        base["data"] = {
            "title":        "Python Script",
            "code":         _PYTHON_CALC_STARTER,
            "_output_text": "",
            "_figs_b64":    [],   # list of base64-encoded PNG strings from last run
            "_error":       "",
        }
    elif btype in ("heading","text","note"):
        base["text"] = ""
    elif btype == "figure":
        base["path"] = ""
        base["caption"] = ""
        base["width"] = "full"  # "full" | "half" | "third"
    elif btype == "table":
        base["caption"] = ""
        base["headers"] = ["Column 1", "Column 2", "Column 3"]
        base["rows"]    = [["", "", ""], ["", "", ""]]
    return base

# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# FEM HELPERS
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

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


# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# UNIT HELPERS
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

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

# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# CUSTOM CALC EVALUATOR
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

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

    # â"€â"€ variables â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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

    # â"€â"€ formulas â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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
    """Convert a custom_calc data dict to a list of report blocks.

    Supports both the new items-based format and the legacy vars/formulas/checks
    format (auto-migrated transparently).
    """
    blocks = []
    title  = data.get("title", "Custom Calculation")
    blocks.append(S(title))

    # ── migrate legacy format ──────────────────────────────────────────────────
    if "items" not in data:
        items = []
        for v in data.get("vars", []):
            if v.get("name", "").strip():
                items.append({"type": "var", "name": v["name"],
                              "value": float(v.get("value", 0.0)),
                              "unit": v.get("unit", "-")})
        for f in data.get("formulas", []):
            if f.strip() and "=" in f:
                items.append({"type": "formula", "expr": f})
        for c in data.get("checks", []):
            items.append({"type": "check",
                          "label":    c.get("label", "Check"),
                          "demand":   c.get("demand", ""),
                          "capacity": float(c.get("capacity", 1.0)),
                          "unit":     c.get("unit", "-")})
    else:
        items = data.get("items", [])

    ns  = {}          # grows incrementally as we process each item
    chk = CheckContext()

    for item in items:
        itype = item.get("type", "")

        if itype == "text":
            content = item.get("content", "").strip()
            if content:
                blocks.append(T(content))

        elif itype == "var":
            name = item.get("name", "").strip()
            if not name:
                continue
            try:
                qty = parse_qty(float(item.get("value", 0.0)), item.get("unit", "-"))
                ns[name] = qty
                unit_lbl = UNIT_LABELS.get(item["unit"], item["unit"])
                val_str  = (f"{item['value']:g}" if item["unit"] == "-"
                            else f"{item['value']:g} {unit_lbl}")
                blocks.append(CALC_ROW(name, "", val_str))
            except Exception as exc:
                blocks.append(NOTE(f"Variable '{name}': {exc}"))

        elif itype == "formula":
            raw = item.get("expr", "").strip()
            if not raw or "=" not in raw:
                continue
            lhs, rhs = raw.split("=", 1)
            lhs = lhs.strip()
            rhs = rhs.strip()
            try:
                result = eval(rhs, _UNIT_NS, ns)
                ns[lhs] = result
                result_str   = fmt_qty(result)
                formula_disp = (rhs
                    .replace("**", "^")
                    .replace("*", " × ")
                    .replace("/", " / ")
                    .replace("  ", " "))
                blocks.append(CALC_ROW(lhs, formula_disp, result_str))
            except Exception as exc:
                blocks.append(NOTE(f"Formula '{raw}': {exc}"))

        elif itype == "figure":
            path      = item.get("path", "").strip()
            caption   = item.get("caption", "")
            width_key = item.get("width", "full")
            fig_w     = {"full": 170, "half": 82, "third": 54}.get(width_key, 170)
            if path and Path(path).exists():
                blocks.append(FIG(path, caption, width_mm=fig_w))
            elif path:
                blocks.append(NOTE(f"Figure not found: {path}"))

        elif itype == "check":
            label   = item.get("label", "Check")
            d_expr  = item.get("demand", "").strip()
            cap_val = float(item.get("capacity", 1.0))
            cap_unt = item.get("unit", "-")
            if not d_expr:
                continue
            try:
                demand   = eval(d_expr, _UNIT_NS, ns)
                capacity = parse_qty(cap_val, cap_unt)
                blocks.append(chk.check(label, demand, capacity))
            except Exception as exc:
                blocks.append(T(f"Check error in '{label}': {exc}"))

    return blocks


# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# BLOCK → REPORT CONVERTER
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

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
        _fig_w = {"full": 170, "half": 82, "third": 54}.get(block.get("width", "full"), 170)
        return [FIG(path, block.get("caption", ""), width_mm=_fig_w)]

    elif t == "table":
        hdrs = block.get("headers", [])
        rows = [[str(c) if c is not None else "" for c in r]
                for r in block.get("rows", [])]
        out  = []
        if block.get("caption"):
            out.append(T(block["caption"]))
        out.append(TBL(hdrs, rows))
        return out

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

    elif t == "concrete_column":
        d = block["data"]
        return concrete_column_rect(
            label              = d["label"],
            h_mm               = d["h_mm"],
            b_mm               = d["b_mm"],
            c_mm               = d["c_mm"],
            da_c_mm            = d["da_c_mm"],
            n_c                = int(d["n_c"]),
            da_t_mm            = d["da_t_mm"],
            n_t                = int(d["n_t"]),
            fck_mpa            = d["fck_mpa"],
            fyk_mpa            = d["fyk_mpa"],
            gamma_c            = d.get("gamma_c", 1.4),
            gamma_s            = d.get("gamma_s", 1.2),
            Ls_mm              = d["Ls_mm"],
            beta_eff           = d.get("beta_eff", 1.0),
            RH                 = d.get("RH", 0.55),
            t0_days            = d.get("t0_days", 28.0),
            M0Eqp_over_M0Ed    = d.get("M0Eqp_over_M0Ed", 0.9),
            load_cases         = d.get("load_cases", []),
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

    elif t == "masonry_ritter":
        d = block["data"]
        return masonry_wall_ritter(
            label   = d["label"],
            b       = d["b_m"]       * m,
            t_ef    = d["t_ef_mm"]   * mm,
            h_ef    = d["h_ef_mm"]   * mm,
            e_m     = d["e_m_mm"]    * mm,
            N_Ed    = d["N_Ed_kN"]   * kN,
            f_b     = d["f_b_mpa"]   * MPa,
            f_m     = d["f_m_mpa"]   * MPa,
            K       = d["K"],
            gamma_M = d["gamma_M"],
            K1      = d["K1"],
        )

    elif t == "custom_calc":
        return custom_calc_to_blocks(block.get("data", {}))

    elif t == "python_calc":
        return python_calc_to_blocks(block.get("data", {}))

    return []


# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# PDF GENERATION
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

def build_and_generate_pdf(project: dict, blocks: list) -> bytes:
    # â"€â"€ Pre-solve all FEM blocks so results are available to linked checks â"€â"€
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


# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# BLOCK EDITOR WIDGETS
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

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
    import hashlib
    uploads_dir = BASE_DIR / "uploads"
    uploads_dir.mkdir(exist_ok=True)

    cur_path = block.get("path", "")

    # ── Current image preview + remove button ─────────────────────────────
    _preview_w = {"full": None, "half": 380, "third": 250}.get(block.get("width", "full"))
    if cur_path and Path(cur_path).exists():
        p_col, btn_col = st.columns([5, 1])
        with p_col:
            if _preview_w:
                st.image(cur_path, width=_preview_w)
            else:
                st.image(cur_path, use_column_width=True)
        with btn_col:
            st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
            if st.button("✕ Remove", key=_uid(block, "frm")):
                block["path"] = ""
            st.markdown("</div>", unsafe_allow_html=True)
    elif cur_path:
        st.warning(f"Image not found: {cur_path}")

    # ── Drag-and-drop / browse uploader ───────────────────────────────────
    uploaded = st.file_uploader(
        "Drop image here, or click to browse  *(PNG / JPG)*",
        type=["png", "jpg", "jpeg"],
        key=_uid(block, "fu"),
    )
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        file_hash  = hashlib.md5(file_bytes).hexdigest()[:12]
        ext        = Path(uploaded.name).suffix.lower() or ".png"
        save_path  = uploads_dir / f"{file_hash}{ext}"
        if not save_path.exists():
            save_path.write_bytes(file_bytes)
        block["path"] = str(save_path)

    # ── Caption + width ───────────────────────────────────────────────────
    _FW_OPTIONS = {"full": "Full width", "half": "Half width", "third": "Third width"}
    fw_col, cap_col = st.columns([1, 2])
    block["width"] = fw_col.selectbox(
        "Width",
        list(_FW_OPTIONS.keys()),
        format_func=lambda k: _FW_OPTIONS[k],
        index=list(_FW_OPTIONS.keys()).index(block.get("width", "full")),
        key=_uid(block, "fw"),
    )
    block["caption"] = cap_col.text_input("Caption", block.get("caption", ""),
                                          key=_uid(block, "fc"))

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

    # â"€â"€ Label + grade â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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

    # â"€â"€ Section selector â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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

    # â"€â"€ Span â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    d["span_m"] = st.number_input("Span [m]", value=float(d.get("span_m",5.0)),
                                   min_value=0.1, key=_uid(block,"span"))

    # â"€â"€ Restraint flags â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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

    # â"€â"€ LTB parameters (shown when not restrained) â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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
                "C1 factor",
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
                    f"λ_LT = {_lbar:.3f}  ·  "
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

    # â"€â"€ Load input â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


def edit_concrete_column(block):
    d = block["data"]

    # ── header label ─────────────────────────────────────────────────────────
    d["label"] = st.text_input("Label", d.get("label", "C1"), key=_uid(block, "label"))

    # ── cross-section ─────────────────────────────────────────────────────────
    st.markdown("**Cross-section**")
    c1, c2, c3 = st.columns(3)
    d["h_mm"] = c1.number_input("h [mm]  (bending dir.)", value=float(d["h_mm"]),
                                 min_value=50.0, key=_uid(block, "h"))
    d["b_mm"] = c2.number_input("b [mm]", value=float(d["b_mm"]),
                                 min_value=50.0, key=_uid(block, "b"))
    d["c_mm"] = c3.number_input("c [mm]  (cover to bar centroid)", value=float(d["c_mm"]),
                                 min_value=10.0, key=_uid(block, "c"))

    # ── reinforcement ─────────────────────────────────────────────────────────
    st.markdown("**Reinforcement**")
    c1, c2, c3, c4 = st.columns(4)
    d["da_c_mm"] = c1.number_input("Ø compression [mm]", value=float(d["da_c_mm"]),
                                    min_value=6.0, key=_uid(block, "dac"))
    d["n_c"]     = c2.number_input("n compression",      value=int(d["n_c"]),
                                    min_value=1, step=1, key=_uid(block, "nc"))
    d["da_t_mm"] = c3.number_input("Ø tension [mm]",     value=float(d["da_t_mm"]),
                                    min_value=6.0, key=_uid(block, "dat"))
    d["n_t"]     = c4.number_input("n tension",          value=int(d["n_t"]),
                                    min_value=1, step=1, key=_uid(block, "nt"))

    # ── materials ─────────────────────────────────────────────────────────────
    st.markdown("**Materials**")
    c1, c2, c3, c4 = st.columns(4)
    d["fck_mpa"]  = c1.number_input("f_ck [MPa]", value=float(d["fck_mpa"]),
                                     min_value=12.0, key=_uid(block, "fck"))
    d["fyk_mpa"]  = c2.number_input("f_yk [MPa]", value=float(d["fyk_mpa"]),
                                     min_value=200.0, key=_uid(block, "fyk"))
    d["gamma_c"]  = c3.number_input("γ_c",         value=float(d.get("gamma_c", 1.4)),
                                     min_value=1.0, key=_uid(block, "gc"))
    d["gamma_s"]  = c4.number_input("γ_s",         value=float(d.get("gamma_s", 1.2)),
                                     min_value=1.0, key=_uid(block, "gs"))

    # ── column length & BC ────────────────────────────────────────────────────
    st.markdown("**Column length & boundary conditions**")
    c1, c2 = st.columns(2)
    d["Ls_mm"]    = c1.number_input("L_s [mm]  (column length)", value=float(d["Ls_mm"]),
                                     min_value=100.0, key=_uid(block, "Ls"))
    d["beta_eff"] = c2.number_input("β  (eff-length factor)", value=float(d.get("beta_eff", 1.0)),
                                     min_value=0.1, max_value=3.0, key=_uid(block, "beta"))

    # ── creep ─────────────────────────────────────────────────────────────────
    st.markdown("**Creep**")
    c1, c2, c3 = st.columns(3)
    d["RH"]      = c1.number_input("RH  [0–1]", value=float(d.get("RH", 0.55)),
                                    min_value=0.0, max_value=1.0, key=_uid(block, "RH"))
    d["t0_days"] = c2.number_input("t₀ [days]", value=float(d.get("t0_days", 28.0)),
                                    min_value=1.0, key=_uid(block, "t0"))
    d["M0Eqp_over_M0Ed"] = c3.number_input(
        "M₀_Eqp / M₀_Ed", value=float(d.get("M0Eqp_over_M0Ed", 0.9)),
        min_value=0.0, max_value=1.0, key=_uid(block, "mqp"))

    # ── load cases ────────────────────────────────────────────────────────────
    st.markdown("**Load cases**")
    st.caption("Enter ULS design axial force N_Ed and first-order moment M₀_Ed for each load case.")
    new_lcs = []
    for li, lc in enumerate(d.get("load_cases", [])):
        lc1, lc2, lc3, lc4 = st.columns([2, 2, 2, 1])
        lbl  = lc1.text_input("Label", lc.get("label", f"LC{li+1}"),
                               key=_uid(block, f"lclbl{li}"), label_visibility="collapsed",
                               placeholder=f"LC {li+1}")
        ned  = lc2.number_input("N_Ed [kN]", value=float(lc.get("NEd_kN", 500.0)),
                                 key=_uid(block, f"lcn{li}"), label_visibility="collapsed")
        med  = lc3.number_input("M₀_Ed [kNm]", value=float(lc.get("M0Ed_kNm", 30.0)),
                                 key=_uid(block, f"lcm{li}"), label_visibility="collapsed")
        keep = not lc4.button("✕", key=_uid(block, f"lcdel{li}"), help="Remove")
        if keep:
            new_lcs.append({"label": lbl, "NEd_kN": ned, "M0Ed_kNm": med})
    d["load_cases"] = new_lcs

    if len(new_lcs) < 9:
        if st.button("+ Add load case", key=_uid(block, "lcadd")):
            d["load_cases"].append({"label": f"LC{len(new_lcs)+1}",
                                    "NEd_kN": 500.0, "M0Ed_kNm": 30.0})
            st.rerun()


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

def edit_masonry_ritter(block):
    d = block["data"]
    c1, c2 = st.columns(2)
    d["label"]    = c1.text_input("Label", d["label"], key=_uid(block,"label"))
    d["K1"]       = c2.number_input("K_1 (long-term)", value=d["K1"], min_value=0.1, max_value=1.0, key=_uid(block,"K1"))

    c1, c2, c3 = st.columns(3)
    d["b_m"]      = c1.number_input("b [m] (width)",      value=d["b_m"],     min_value=0.1,  key=_uid(block,"bm"))
    d["t_ef_mm"]  = c2.number_input("t_ef [mm]",           value=d["t_ef_mm"], min_value=50.0, key=_uid(block,"tef"))
    d["h_ef_mm"]  = c3.number_input("h_ef [mm]",           value=d["h_ef_mm"], min_value=100.0,key=_uid(block,"hef"))

    c1, c2, c3 = st.columns(3)
    d["e_m_mm"]   = c1.number_input("e_m [mm] (eccentricity)", value=d["e_m_mm"],  min_value=0.0,  key=_uid(block,"em"))
    d["N_Ed_kN"]  = c2.number_input("N_Ed [kN]",               value=d["N_Ed_kN"], key=_uid(block,"NEd"))
    d["f_b_mpa"]  = c3.number_input("f_b [MPa]",               value=d["f_b_mpa"], key=_uid(block,"fb"))

    c1, c2, c3 = st.columns(3)
    d["f_m_mpa"]  = c1.number_input("f_m [MPa]",   value=d["f_m_mpa"],  key=_uid(block,"fm"))
    d["K"]        = c2.number_input("K (Table 3.3)", value=d["K"],        key=_uid(block,"Ktab"))
    d["gamma_M"]  = c3.number_input("gamma_M",       value=d["gamma_M"], min_value=1.0, key=_uid(block,"gM"))


def edit_custom_calc(block):
    """Flexible item-list editor for custom calculations.

    Items can be freely mixed in any order:
      text     - narrative paragraph / assumptions
      var      - named variable with value + unit (instantly in namespace)
      formula  - arithmetic expression with live inline result
      figure   - embedded image from the figures/ folder
      check    - pass/fail utilisation check against the running namespace
    """
    d = block["data"]

    # -- migrate legacy vars/formulas/checks -> items --------------------
    if "items" not in d:
        old_items = []
        for v in d.get("vars", []):
            if v.get("name", "").strip():
                old_items.append({"type": "var", "name": v["name"],
                                  "value": float(v.get("value", 0.0)),
                                  "unit":  v.get("unit", "-")})
        for f in d.get("formulas", []):
            if f.strip() and "=" in f:
                old_items.append({"type": "formula", "expr": f})
        for c in d.get("checks", []):
            old_items.append({"type": "check",
                              "label":    c.get("label", "Check"),
                              "demand":   c.get("demand", ""),
                              "capacity": float(c.get("capacity", 1.0)),
                              "unit":     c.get("unit", "-")})
        d["items"] = old_items
        d.pop("vars", None)
        d.pop("formulas", None)
        d.pop("checks", None)

    d["title"] = st.text_input("Section title", d.get("title", "Custom Calculation"),
                               key=_uid(block, "title"))

    items = d["items"]

    # build running namespace for inline result previews
    ns = {}
    for it in items:
        if it["type"] == "var" and it.get("name", "").strip():
            try:
                ns[it["name"].strip()] = parse_qty(float(it.get("value", 0.0)),
                                                   it.get("unit", "-"))
            except Exception:
                pass
        elif it["type"] == "formula":
            raw = it.get("expr", "").strip()
            if raw and "=" in raw:
                lhs, rhs = raw.split("=", 1)
                try:
                    ns[lhs.strip()] = eval(rhs.strip(), _UNIT_NS, ns)
                except Exception:
                    pass

    # per-item badge colours
    _BADGE = {
        "text":    ("TXT", "#6E6E73"),
        "var":     ("VAR", "#12788E"),
        "formula": ("FML", "#032E38"),
        "figure":  ("FIG", "#6D4E8A"),
        "check":   ("CHK", "#E74825"),
    }

    to_delete    = None
    to_move_up   = None
    to_move_down = None

    for idx, item in enumerate(items):
        itype = item.get("type", "text")
        badge_txt, badge_color = _BADGE.get(itype, ("???", "#999"))

        # Control strip: up / down / badge / delete
        # IMPORTANT: no content column here — content is rendered separately below
        # so it can create its own columns without hitting the 2-level nesting limit.
        _up_c, _dn_c, _bg_c, _dl_c = st.columns([1, 1, 14, 1])
        _bg_c.markdown(
            f"<div style='background:{badge_color}; color:white; font-size:9px; "
            f"font-weight:700; letter-spacing:0.05em; padding:3px 5px; "
            f"border-radius:3px; margin-top:8px; display:inline-block;'>"
            f"{badge_txt}</div>",
            unsafe_allow_html=True,
        )
        if idx > 0 and _up_c.button("↑", key=_uid(block, f"up{idx}"), help="Move up"):
            to_move_up = idx
        if idx < len(items) - 1 and _dn_c.button("↓", key=_uid(block, f"dn{idx}"),
                                                   help="Move down"):
            to_move_down = idx
        if _dl_c.button("✕", key=_uid(block, f"xdel{idx}"), help="Remove"):
            to_delete = idx

        # Content — NOT inside any column, so it can freely use st.columns at level 1
        if itype == "text":
            item["content"] = st.text_area(
                "Text", item.get("content", ""), height=80,
                key=_uid(block, f"txt{idx}"),
                label_visibility="collapsed",
                placeholder="Assumptions, description, references...",
            )

        elif itype == "var":
            _vc1, _vc2, _vc3 = st.columns([3, 2, 2])
            item["name"]  = _vc1.text_input(
                "Name", item.get("name", ""), key=_uid(block, f"vn{idx}"),
                label_visibility="collapsed", placeholder="e.g. g_k")
            item["value"] = _vc2.number_input(
                "Value", value=float(item.get("value", 0.0)),
                key=_uid(block, f"vv{idx}"), label_visibility="collapsed",
                format="%.4g")
            _cur_unit = item.get("unit", "-")
            if _cur_unit not in UNIT_CHOICES:
                _cur_unit = "-"
            item["unit"] = _vc3.selectbox(
                "Unit", UNIT_CHOICES,
                index=UNIT_CHOICES.index(_cur_unit),
                key=_uid(block, f"vu{idx}"),
                label_visibility="collapsed",
                format_func=lambda u: UNIT_LABELS.get(u, u))

        elif itype == "formula":
            item["expr"] = st.text_input(
                "Formula", item.get("expr", ""),
                key=_uid(block, f"fml{idx}"),
                label_visibility="collapsed",
                placeholder="e.g.  F_Ed = g_k * L   or   sigma = F_Ed / A")
            # inline result
            _expr = item.get("expr", "").strip()
            if _expr and "=" in _expr:
                _lhs = _expr.split("=")[0].strip()
                if _lhs in ns:
                    _res = fmt_qty(ns[_lhs])
                    st.markdown(
                        f"<span style='font-size:12px; color:#12788E; "
                        f"font-family:monospace;'>→ {_lhs} = {_res}</span>",
                        unsafe_allow_html=True,
                    )

        elif itype == "figure":
            import glob as _glob
            _fig_dir  = BASE_DIR / "figures"
            _all_imgs = sorted(_glob.glob(str(_fig_dir / "*")))
            _img_names = [Path(p).name for p in _all_imgs]
            _fc1, _fc2 = st.columns([3, 2])
            if _img_names:
                _cur_name = Path(item.get("path", "")).name
                _sel_idx  = (_img_names.index(_cur_name)
                             if _cur_name in _img_names else 0)
                _chosen = _fc1.selectbox(
                    "Figure", _img_names, index=_sel_idx,
                    key=_uid(block, f"figsel{idx}"),
                    label_visibility="collapsed")
                item["path"] = str(_fig_dir / _chosen)
            else:
                _fc1.caption("No images found in figures/ folder")
            item["caption"] = _fc2.text_input(
                "Caption", item.get("caption", ""),
                key=_uid(block, f"figcap{idx}"),
                label_visibility="collapsed",
                placeholder="Caption text")
            item["width"] = st.select_slider(
                "Width", options=["third", "half", "full"],
                value=item.get("width", "full"),
                key=_uid(block, f"figw{idx}"))
            _fp = item.get("path", "")
            if _fp and Path(_fp).exists():
                st.image(Path(_fp).read_bytes(), width=180)

        elif itype == "check":
            _cc1, _cc2, _cc3, _cc4 = st.columns([3, 3, 2, 2])
            item["label"]    = _cc1.text_input(
                "Label", item.get("label", "Check"),
                key=_uid(block, f"cl{idx}"),
                label_visibility="collapsed", placeholder="Check label")
            item["demand"]   = _cc2.text_input(
                "Demand", item.get("demand", ""),
                key=_uid(block, f"cd{idx}"),
                label_visibility="collapsed",
                placeholder="demand expr e.g. sigma")
            item["capacity"] = _cc3.number_input(
                "Capacity", float(item.get("capacity", 1.0)),
                key=_uid(block, f"cc{idx}"),
                label_visibility="collapsed")
            _chk_unit = item.get("unit", "-")
            if _chk_unit not in UNIT_CHOICES:
                _chk_unit = "-"
            item["unit"] = _cc4.selectbox(
                "Unit", UNIT_CHOICES,
                index=UNIT_CHOICES.index(_chk_unit),
                key=_uid(block, f"cu{idx}"),
                label_visibility="collapsed",
                format_func=lambda u: UNIT_LABELS.get(u, u))
            # inline check result
            _dexpr = item.get("demand", "").strip()
            if _dexpr:
                try:
                    _dem = eval(_dexpr, _UNIT_NS, ns)
                    _cap = parse_qty(float(item["capacity"]), item["unit"])
                    _rat = float(_dem / _cap)
                    _col = "#27AE60" if _rat <= 1.0 else "#E74825"
                    _lbl = "✓ OK" if _rat <= 1.0 else "✗ FAIL"
                    st.markdown(
                        f"<span style='font-size:12px; color:{_col}; "
                        f"font-family:monospace;'>"
                        f"→ {_rat:.3f}  {_lbl}</span>",
                        unsafe_allow_html=True,
                    )
                except Exception:
                    pass

        st.markdown(
            "<div style='border-bottom:1px solid #f0f0f0; margin:2px 0 6px;'></div>",
            unsafe_allow_html=True,
        )

    # apply mutation from this run
    if to_delete is not None:
        d["items"].pop(to_delete)
        st.rerun()
    elif to_move_up is not None and to_move_up > 0:
        lst = d["items"]
        lst[to_move_up - 1], lst[to_move_up] = lst[to_move_up], lst[to_move_up - 1]
        st.rerun()
    elif to_move_down is not None and to_move_down < len(d["items"]) - 1:
        lst = d["items"]
        lst[to_move_down], lst[to_move_down + 1] = lst[to_move_down + 1], lst[to_move_down]
        st.rerun()

    # add item buttons
    st.markdown(
        "<p style='font-size:11px; color:#999; margin:10px 0 4px; "
        "letter-spacing:0.06em; text-transform:uppercase;'>Add item</p>",
        unsafe_allow_html=True,
    )
    _a1, _a2, _a3, _a4, _a5 = st.columns(5)
    if _a1.button("+ Text",     key=_uid(block, "add_txt"), use_container_width=True):
        d["items"].append({"type": "text", "content": ""})
        st.rerun()
    if _a2.button("+ Variable", key=_uid(block, "add_var"), use_container_width=True):
        d["items"].append({"type": "var", "name": "", "value": 0.0, "unit": "-"})
        st.rerun()
    if _a3.button("+ Formula",  key=_uid(block, "add_fml"), use_container_width=True):
        d["items"].append({"type": "formula", "expr": ""})
        st.rerun()
    if _a4.button("+ Figure",   key=_uid(block, "add_fig"), use_container_width=True):
        d["items"].append({"type": "figure", "path": "", "caption": "", "width": "full"})
        st.rerun()
    if _a5.button("+ Check",    key=_uid(block, "add_chk"), use_container_width=True):
        d["items"].append({"type": "check", "label": "Check",
                           "demand": "", "capacity": 1.0, "unit": "kN"})
        st.rerun()

def edit_fem_beam(block):
    d = block["data"]
    SUPPORT_TYPES = ["pin", "roller", "fixed"]
    LOAD_TYPES    = ["udl", "point", "trapezoidal"]
    LOAD_LABELS   = {"udl": "UDL", "point": "Point load", "trapezoidal": "Trapezoidal"}

    # â"€â"€ Identity â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    c1, c2, c3 = st.columns(3)
    d["label"]  = c1.text_input("Label", d.get("label","FEM-1"), key=_uid(block,"lbl"))
    d["span_m"] = c2.number_input("Span [m]", value=float(d.get("span_m",6.0)),
                                   min_value=0.1, key=_uid(block,"span"))
    d["n_elements"] = int(c3.number_input("Elements (precision)",
                          value=int(d.get("n_elements",100)),
                          min_value=20, max_value=500, step=10, key=_uid(block,"nel")))

    # â"€â"€ Stiffness â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    st.markdown("**Section stiffness — EI**")
    sc1, sc2, sc3 = st.columns(3)
    d["E_mpa"]  = sc1.number_input("E [MPa]", value=float(d.get("E_mpa",210000.0)),
                                    min_value=1.0, key=_uid(block,"E"),
                                    help="Steel ≈ 210 000  |  Timber ≈ 11 000  |  Concrete ≈ 30 000")
    d["I_cm4"]  = sc2.number_input("I [cm⁴]", value=float(d.get("I_cm4",8356.0)),
                                    min_value=0.001, format="%.1f", key=_uid(block,"I"))
    EI = d["E_mpa"] * 1e6 * d["I_cm4"] * 1e-8
    sc3.metric("EI  [kN·m²]", f"{EI/1e3:.0f}")

    # â"€â"€ Supports â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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
        st.rerun()

    # â"€â"€ Loads â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    st.markdown("**Loads  (ULS combination applied automatically)**")
    loads = d.setdefault("loads", [])
    new_loads = []
    for li, load in enumerate(loads):
        ltype    = load.get("type", "udl")
        # Control row: type selector + Remove button — no content column
        # Content is rendered separately below so it can use its own st.columns at level 1
        lc0, lc_del = st.columns([3, 1])
        new_type = lc0.selectbox("Type", LOAD_TYPES,
                                  index=LOAD_TYPES.index(ltype),
                                  key=_uid(block, f"ltype{li}"),
                                  label_visibility="collapsed",
                                  format_func=lambda t: LOAD_LABELS[t])
        load["type"] = new_type
        keep = not lc_del.button("Remove", key=_uid(block, f"ldel{li}"))

        # Load parameters — outside any column, free to use st.columns at level 1
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
            st.rerun()

    # â"€â"€ Live beam layout preview â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    if d.get("supports") or d.get("loads"):
        try:
            preview_png = _beam_layout_preview_bytes(d)
            st.image(preview_png, use_column_width=True)
        except Exception:
            pass  # silent — don't clutter UI with preview errors

    # â"€â"€ Run FEM + show results â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
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


def edit_python_calc(block):
    """Full-Python execution block.

    The user writes arbitrary Python; it runs in an isolated namespace with
    numpy, pandas, matplotlib and scipy pre-imported.  print() output and all
    matplotlib figures created during the run are captured and displayed inline.
    Results (text + figures as base64 PNG) are stored in block["data"] so the
    PDF generator can embed any figures that were produced.
    """
    import io, contextlib, traceback as _tb, base64 as _b64

    d    = block["data"]
    _bid = block["id"]

    d["title"] = st.text_input(
        "Section title", d.get("title", "Python Script"),
        key=_uid(block, "title"),
    )

    st.caption(
        "Pre-imported: **`np`** (numpy)  ·  **`pd`** (pandas)  ·  "
        "**`plt`** (matplotlib.pyplot)  ·  **`scipy`**  ·  "
        "`print()` output and all `plt.figure()` plots are captured automatically."
    )

    code = st.text_area(
        "Code",
        d.get("code", _PYTHON_CALC_STARTER),
        height=340,
        key=_uid(block, "code"),
        label_visibility="collapsed",
    )
    d["code"] = code

    _btn_run, _btn_clr, _ = st.columns([1, 1, 5])
    _run_clicked = _btn_run.button(
        "▶  Run", key=_uid(block, "run"),
        type="primary", use_container_width=True,
    )
    if _btn_clr.button("✕  Clear", key=_uid(block, "clr"), use_container_width=True):
        d["_output_text"] = ""
        d["_figs_b64"]    = []
        d["_error"]       = ""
        st.rerun()

    if _run_clicked:
        import matplotlib as _mpl
        _mpl.use("Agg")
        import matplotlib.pyplot as _plt
        _plt.close("all")

        _stdout_buf = io.StringIO()

        # Build execution namespace with common science/engineering libs
        _ns: dict = {}
        for _alias, _mod_name in [
            ("np",      "numpy"),
            ("numpy",   "numpy"),
            ("pd",      "pandas"),
            ("pandas",  "pandas"),
            ("scipy",   "scipy"),
        ]:
            try:
                import importlib as _il
                _ns[_alias] = _il.import_module(_mod_name)
            except ImportError:
                pass
        _ns["plt"]        = _plt
        _ns["matplotlib"] = _mpl

        _err = ""
        try:
            with contextlib.redirect_stdout(_stdout_buf):
                exec(compile(code, "<python_calc>", "exec"), _ns)
        except Exception:
            _err = _tb.format_exc()

        d["_output_text"] = _stdout_buf.getvalue()
        d["_error"]       = _err

        # Capture every figure created during exec as a base64 PNG
        _figs_b64 = []
        for _fnum in _plt.get_fignums():
            _fig = _plt.figure(_fnum)
            _buf = io.BytesIO()
            _fig.savefig(_buf, format="png", dpi=150, bbox_inches="tight")
            _buf.seek(0)
            _figs_b64.append(_b64.b64encode(_buf.read()).decode())
        _plt.close("all")
        d["_figs_b64"] = _figs_b64

        st.rerun()

    # ── Display results from last run ─────────────────────────────────────────
    if d.get("_output_text"):
        st.code(d["_output_text"], language=None)
    for _fb64 in d.get("_figs_b64", []):
        st.image(_b64.b64decode(_fb64))
    if d.get("_error"):
        st.error(d["_error"])


def python_calc_to_blocks(data: dict) -> list:
    """Convert a python_calc block to PDF report blocks.

    Includes: section heading, any matplotlib figures from the last run.
    The raw code is intentionally omitted from the PDF to keep it clean.
    """
    blocks = [S(data.get("title", "Python Script"))]

    for i, fb64 in enumerate(data.get("_figs_b64", [])):
        try:
            import base64 as _b64
            _png_bytes = _b64.b64decode(fb64)
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as _tmp:
                _tmp.write(_png_bytes)
                _tmp_path = _tmp.name
            blocks.append(FIG(_tmp_path, caption="", width_mm=170))
        except Exception as exc:
            blocks.append(NOTE(f"Figure {i+1} could not be embedded: {exc}"))

    if data.get("_output_text", "").strip():
        # Include printed output as a verbatim note in the PDF
        blocks.append(T(data["_output_text"].strip()))

    if not data.get("_figs_b64") and not data.get("_output_text", "").strip():
        blocks.append(NOTE("Python script — run the block to generate output for the PDF."))

    return blocks


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
    "concrete_column":    edit_concrete_column,
    "masonry_wall":       edit_masonry_wall,
    "masonry_ritter":     edit_masonry_ritter,
    "custom_calc":        edit_custom_calc,
    "python_calc":        edit_python_calc,
}

ICONS = {
    "heading":            "",
    "text":               "",
    "note":               "",
    "figure":             "",
    "table":              "",
    "pagebreak":          "",
    "timber_beam_column": "",
    "timber_beam":        "",
    "steel_beam":         "",
    "concrete_beam":      "",
    "concrete_column":    "",
    "masonry_wall":       "",
    "masonry_ritter":     "",
    "custom_calc":        "",
    "python_calc":        "",
}

LABELS = {
    "heading":            "Section heading",
    "text":               "Paragraph",
    "note":               "Note",
    "figure":             "Figure",
    "table":              "Table",
    "pagebreak":          "Page break",
    "fem_beam":           "FEM beam analysis",
    "timber_beam_column": "Timber beam-column — EN 1995",
    "timber_beam":        "Timber beam — EN 1995",
    "steel_beam":         "Steel beam IPE / HEA / HEB / L — EN 1993",
    "concrete_beam":      "Concrete beam — EN 1992",
    "concrete_column":    "Concrete column — EN 1992",
    "masonry_wall":       "Masonry wall — EN 1996",
    "masonry_ritter":     "Masonry wall Ritter — EN 1996",
    "custom_calc":        "Custom calculation",
    "python_calc":        "Python script",
}

def _block_summary(block) -> str:
    t = block["type"]
    if t in ("heading","text","note"):
        return block.get("text","")[:60]
    if t == "table":
        cap = block.get("caption","")
        hdrs = block.get("headers",[])
        return cap or (", ".join(hdrs[:3]) + ("…" if len(hdrs) > 3 else ""))
    if t == "figure":
        return block.get("caption","") or (block.get("path","").split("/")[-1].split("\\")[-1])[:40]
    if t in ("custom_calc", "python_calc"):
        return block.get("data",{}).get("title","")
    if t in ("timber_beam_column","timber_beam","steel_beam","concrete_beam","concrete_column","masonry_wall","masonry_ritter"):
        d = block.get("data",{})
        return d.get("label","")
    return ""

# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
# SIDEBAR — PROJECT METADATA
# â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

with st.sidebar:
    logo_path = BASE_DIR / "Billede2.png"
    if logo_path.exists():
        st.image(logo_path.read_bytes(), width=140)

    # ── Who are you? ──────────────────────────────────────────────────────────
    _cu = st.text_input(
        "Your name / initials",
        value       = st.session_state.current_user,
        placeholder = "e.g. NCJ",
        key         = "_sb_user_input",
        help        = "Shown as 'last edited by' on project cards.",
    )
    st.session_state.current_user = _cu

    st.markdown("---")

    # ── Export / Import ───────────────────────────────────────────────────────
    # Projects auto-save to the local database — use these only for backups or
    # moving data between machines.
    st.markdown(
        "<p style='font-size:10px; letter-spacing:0.1em; text-transform:uppercase; "
        "color:#AEAEB2; margin-bottom:4px;'>Backup / Transfer</p>",
        unsafe_allow_html=True,
    )
    _proj_name = st.session_state.get("proj_ref", "report")
    _save_name = f"{_proj_name}.json".replace("/", "-").replace(" ", "_")
    st.download_button(
        label            = "Export JSON",
        data             = _project_to_json(),
        file_name        = _save_name,
        mime             = "application/json",
        use_container_width = True,
        help             = "Download all projects as a JSON backup. "
                           "Use 'Import JSON' on another machine to restore.",
    )

    # Import
    _uploaded = st.file_uploader(
        "Import JSON",
        type             = ["json"],
        key              = "_load_uploader",
        label_visibility = "collapsed",
        help             = "Import projects from a JSON backup file. "
                           "Existing projects with the same ID are overwritten.",
    )
    if _uploaded is not None:
        try:
            _data = json.loads(_uploaded.read().decode("utf-8"))
            _dv = _data.get("version", 1)
            if _dv == 4 and not isinstance(_data.get("projects"), list):
                raise ValueError("Invalid v4 file — missing 'projects' list.")
            elif _dv < 4 and not isinstance(_data.get("blocks"), list) \
                         and not isinstance(_data.get("documents"), dict):
                raise ValueError("Invalid project file format.")
            st.session_state["_pending_load"] = _data
            st.rerun()
        except Exception as _e:
            st.error(f"Could not load file: {_e}")

    # ── Project navigation ────────────────────────────────────────────────────
    if st.session_state.get("active_project_id"):
        if st.button("← All projects", use_container_width=True, key="sb_back_proj"):
            _close_project()
        st.markdown("---")
        st.markdown("## Project")

        proj_firm     = st.text_input("Firm",          st.session_state.get("proj_firm",""),    key="proj_firm")
        proj_project  = st.text_input("Project / Sag", st.session_state.get("proj_project",""), key="proj_project")
        proj_title    = st.text_input("Title",          st.session_state.get("proj_title","Structural Calculations"), key="proj_title")
        proj_section  = st.text_input("Afsnit",         st.session_state.get("proj_section",""), key="proj_section",
                                      help="Document section shown in the Afsnit header cell")
        proj_ref      = st.text_input("Sagsnr / Ref",   st.session_state.get("proj_ref",""),    key="proj_ref")
        proj_rev      = st.text_input("Revision",       st.session_state.get("proj_rev","A"),   key="proj_rev")
        proj_standard = st.text_input("Standard",       st.session_state.get("proj_std","EN 1990 / EN 1995-1-1"), key="proj_std")

        st.markdown("### People & dates")
        proj_engineer      = st.text_input("Beregnet af",     st.session_state.get("proj_eng",""),  key="proj_eng")
        proj_checker       = st.text_input("Kontrolleret af", st.session_state.get("proj_chk",""),  key="proj_chk")
        proj_approver      = st.text_input("Godkendt af",     st.session_state.get("proj_apr",""),  key="proj_apr")
        proj_date          = st.text_input("Dato",            st.session_state.get("proj_date", date.today().strftime("%d/%m/%Y")), key="proj_date")
        proj_checker_date  = st.text_input("Dato (kontrol)",  st.session_state.get("proj_chk_date", date.today().strftime("%d/%m/%Y")), key="proj_chk_date")
        proj_approver_date = st.text_input("Dato (godkendt)", st.session_state.get("proj_apr_date", date.today().strftime("%d/%m/%Y")), key="proj_apr_date")

        st.markdown("### Firm contact")
        proj_address = st.text_input("Address", st.session_state.get("proj_address",""), key="proj_address")
        proj_phone   = st.text_input("Phone",   st.session_state.get("proj_phone",""),   key="proj_phone")
        proj_cvr     = st.text_input("CVR",     st.session_state.get("proj_cvr",""),     key="proj_cvr")
        proj_email   = st.text_input("Email",   st.session_state.get("proj_email",""),   key="proj_email")

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

        # Active document indicator
        if st.session_state.get("active_doc"):
            _ad = st.session_state.active_doc
            st.markdown("---")
            st.markdown(
                f"<div style='background:#F5F5F5; border-left:3px solid #E74825; "
                f"padding:8px 10px; font-size:11px; color:#1C1C1E;'>"
                f"<b>Editing:</b> {_ad} — {DOC_DEFS.get(_ad, '')}</div>",
                unsafe_allow_html=True,
            )
    else:
        # Front page — no active project; still need PROJECT defined to avoid NameError
        proj_project = proj_ref = proj_rev = proj_date = ""
        PROJECT = {}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
# MAIN — three-level navigation
# ─────────────────────────────────────────────────────────────────────────────

_active_pid = st.session_state.active_project_id
_active_doc = st.session_state.active_doc

if _active_pid is None:
    # ── FRONT PAGE — project folders ─────────────────────────────────────────
    # Always pull a fresh list from the database so all engineers see each
    # other's projects without needing to reload the page manually.
    st.session_state.projects = _db.load_all_projects()

    st.markdown(
        "<h1 style='font-size:28px; font-weight:800; letter-spacing:0.01em; margin-bottom:4px;'>"
        "Projects</h1>"
        "<p style='font-size:13px; color:#6E6E73; margin-top:0; margin-bottom:24px;'>"
        "Open a project or create a new one.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("+ New project", expanded=(not st.session_state.projects)):
        with st.form("new_project_form", clear_on_submit=True):
            _np_c1, _np_c2 = st.columns(2)
            _np_name = _np_c1.text_input("Project name", placeholder="Ablelokkerne")
            _np_ref  = _np_c2.text_input("Sagsnr / Ref", placeholder="202328")
            if st.form_submit_button("Create project", use_container_width=True):
                _p = _new_project(name=_np_name or "New Project", ref=_np_ref)
                _db.save_project(_p, user=st.session_state.get("current_user", ""))
                st.session_state.projects.append(_p)
                _open_project(_p["id"])

    if not st.session_state.projects:
        st.markdown(
            "<p style='color:#bbb; font-size:13px; padding:24px 0;'>"
            "No projects yet — create one above.</p>",
            unsafe_allow_html=True,
        )
    else:
        _COLS = 3
        for _rs in range(0, len(st.session_state.projects), _COLS):
            _row = st.session_state.projects[_rs:_rs + _COLS]
            _gcols = st.columns(_COLS)
            for _gc, _proj in zip(_gcols, _row):
                with _gc:
                    _m  = _proj["metadata"]
                    _pn = _m.get("proj_project") or "Untitled"
                    _pr = _m.get("proj_ref", "")
                    _pd = _proj.get("created", "")
                    _nd = sum(
                        1 for d in DOC_DEFS
                        if len(_proj["documents"].get(d, {}).get("blocks", [])) > 0
                    )
                    # Last-edited stamp (written by db.save_project)
                    _uat = _proj.get("_updated_at", "")
                    _uby = _proj.get("_updated_by", "")
                    _stamp = _db.fmt_updated(_uat) if _uat else _pd
                    _by_str = f" · {_uby}" if _uby else ""
                    st.markdown(
                        f"<div style='border:1px solid #e8e8e8; border-top:3px solid #E74825; "
                        f"padding:16px 14px 12px; margin-bottom:6px;'>"
                        f"<div style='font-size:18px; font-weight:800; color:#1C1C1E; "
                        f"line-height:1.2; margin-bottom:4px;'>{_pn}</div>"
                        f"<div style='font-size:11px; color:#6E6E73; margin-bottom:2px;'>{_pr}</div>"
                        f"<div style='font-size:10px; color:#AEAEB2; margin-bottom:4px;'>"
                        f"{_stamp}{_by_str}</div>"
                        f"<div style='font-size:10px; color:#AEAEB2;'>"
                        f"{'&#9679;' if _nd > 0 else '&#9675;'}&nbsp;{_nd} / 7 documents"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                    _oc1, _oc2 = st.columns([3, 1])
                    if _oc1.button("Open →", key=f"proj_open_{_proj['id']}",
                                   use_container_width=True):
                        _open_project(_proj["id"])
                    if _oc2.button("✕", key=f"proj_del_{_proj['id']}",
                                   use_container_width=True, help="Delete project"):
                        _db.delete_project(_proj["id"])
                        st.session_state.projects = [
                            p for p in st.session_state.projects if p["id"] != _proj["id"]
                        ]
                        st.rerun()
            if _rs + _COLS < len(st.session_state.projects):
                st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

elif _active_doc is None:
    # ── PROJECT DASHBOARD ────────────────────────────────────────────────────
    st.markdown(
        f"<h1 style='font-size:26px; font-weight:800; letter-spacing:0.01em; margin-bottom:4px;'>"
        f"{proj_project}</h1>"
        f"<p style='font-size:13px; color:#6E6E73; margin-top:0; margin-bottom:32px;'>"
        f"{proj_ref} &nbsp;&middot;&nbsp; Rev&nbsp;{proj_rev} &nbsp;&middot;&nbsp; {proj_date}</p>",
        unsafe_allow_html=True,
    )

    for group_name, doc_ids in DOC_GROUPS:
        st.markdown(
            f"<p style='font-size:10px; letter-spacing:0.12em; text-transform:uppercase; "
            f"color:#6E6E73; font-weight:700; margin:0 0 10px;'>{group_name}</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(len(doc_ids))
        for col, doc_id in zip(cols, doc_ids):
            with col:
                doc = st.session_state.documents[doc_id]
                n_subdocs = len(doc.get("subdocs", []))
                n_blocks  = sum(len(sd.get("blocks", [])) for sd in doc.get("subdocs", [])) \
                            if n_subdocs else len(doc["blocks"])
                accent = "#E74825" if doc_id.startswith("A") else "#032E38"
                dot    = "&#9679;" if (n_blocks > 0 or n_subdocs > 0) else "&#9675;"
                if n_subdocs:
                    _stat_line = (f"{n_subdocs} sub-doc{'s' if n_subdocs != 1 else ''}"
                                  f" &nbsp;·&nbsp; {n_blocks} block{'s' if n_blocks != 1 else ''}")
                else:
                    _stat_line = f"{n_blocks} block{'s' if n_blocks != 1 else ''}"
                st.markdown(
                    f"<div style='border:1px solid #e8e8e8; border-top:3px solid {accent}; "
                    f"padding:16px 14px 10px; margin-bottom:4px; min-height:90px;'>"
                    f"<div style='font-size:24px; font-weight:800; color:#1C1C1E; "
                    f"line-height:1; margin-bottom:6px;'>{doc_id}</div>"
                    f"<div style='font-size:11px; color:#6E6E73; line-height:1.4; "
                    f"margin-bottom:10px;'>{doc['title']}</div>"
                    f"<div style='font-size:10px; color:#AEAEB2;'>"
                    f"{dot}&nbsp;{_stat_line}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )
                btn_col, tpl_col = st.columns([3, 2])
                with btn_col:
                    if st.button("Open →", key=f"open_{doc_id}", use_container_width=True):
                        _open_document(doc_id)
                with tpl_col:
                    if doc_id in DOC_TEMPLATES:
                        if st.button("Template", key=f"tpl_{doc_id}", use_container_width=True):
                            _load_template(doc_id)
        st.markdown("<div style='margin-bottom:28px'></div>", unsafe_allow_html=True)

else:
    # ── DOCUMENT EDITOR  (or sub-document dashboard) ─────────────────────────
    active_doc    = st.session_state.active_doc
    active_subdoc = st.session_state.get("active_subdoc")
    doc_title     = DOC_DEFS.get(active_doc, "")
    doc           = st.session_state.documents[active_doc]
    subdocs       = doc.get("subdocs", [])

    # ── SUBDOC DASHBOARD — shown when a document has sub-documents and none
    #    is currently open. Uses st.stop() so the block editor below is skipped.
    if subdocs and active_subdoc is None:
        accent = "#E74825" if active_doc.startswith("A") else "#032E38"
        col_back, col_h, _ = st.columns([1, 5, 1])
        with col_back:
            st.markdown("<div style='padding-top:12px'>", unsafe_allow_html=True)
            if st.button("← Back", key="back_btn"):
                _close_document()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_h:
            st.markdown(
                f"<h1 style='font-size:20px; font-weight:700; letter-spacing:0.02em; margin-bottom:2px;'>"
                f"{active_doc} — {doc_title}</h1>"
                f"<p style='font-size:12px; color:#999; margin-top:0;'>"
                f"{proj_project} &nbsp;&middot;&nbsp; {proj_ref} &nbsp;&middot;&nbsp; Rev {proj_rev}"
                f"</p>",
                unsafe_allow_html=True,
            )
        st.markdown("<div style='margin-bottom:20px'></div>", unsafe_allow_html=True)

        # Render subdoc cards — up to 4 per row
        _SDCOLS = 4
        for _sri in range(0, len(subdocs), _SDCOLS):
            _row_sdocs = subdocs[_sri: _sri + _SDCOLS]
            _sdcols = st.columns(len(_row_sdocs))
            for _sci, (_sdcol, _si) in enumerate(zip(_sdcols, range(_sri, _sri + len(_row_sdocs)))):
                _sd = subdocs[_si]
                _sd_label = f"{active_doc}.{_si + 1}"
                _sd_nblk  = len(_sd.get("blocks", []))
                _sd_dot   = "&#9679;" if _sd_nblk > 0 else "&#9675;"
                with _sdcol:
                    st.markdown(
                        f"<div style='border:1px solid #e8e8e8; border-top:3px solid {accent}; "
                        f"padding:16px 14px 10px; margin-bottom:4px; min-height:90px;'>"
                        f"<div style='font-size:22px; font-weight:800; color:#1C1C1E; "
                        f"line-height:1; margin-bottom:6px;'>{_sd_label}</div>"
                        f"<div style='font-size:12px; color:#333; font-weight:600; "
                        f"line-height:1.4; margin-bottom:6px;'>{_sd['name']}</div>"
                        f"<div style='font-size:10px; color:#AEAEB2;'>"
                        f"{_sd_dot}&nbsp;{_sd_nblk} block{'s' if _sd_nblk != 1 else ''}"
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )
                    _op_c, _del_c = st.columns([4, 1])
                    with _op_c:
                        if st.button("Open →", key=f"sd_open_{active_doc}_{_si}",
                                     use_container_width=True):
                            _open_subdoc(_si)
                    with _del_c:
                        if st.button("✕", key=f"sd_del_{active_doc}_{_si}",
                                     use_container_width=True,
                                     help=f"Delete {_sd_label} (cannot undo)"):
                            _delete_subdoc(active_doc, _si)

        # Add a new sub-document
        st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
        with st.expander("＋ Add sub-document", expanded=False):
            _sd_name_in = st.text_input(
                "Sub-document title",
                placeholder=f"e.g. Loads, Elements, Foundations…",
                key=f"sd_new_name_{active_doc}",
                label_visibility="collapsed",
            )
            if st.button("Add sub-document", key=f"sd_add_{active_doc}", type="primary"):
                if not _sd_name_in.strip():
                    st.warning("Please enter a title for the new sub-document.")
                else:
                    _add_subdoc(active_doc, _sd_name_in.strip(), adopt_blocks=False)

        st.stop()

    # ── SUBDOC EDITOR HEADER — we are inside a specific sub-document
    if active_subdoc is not None:
        _sd_label  = f"{active_doc}.{active_subdoc + 1}"
        _sd_name   = subdocs[active_subdoc]["name"] if active_subdoc < len(subdocs) else ""
        _hdr_title = f"{_sd_label} — {_sd_name}"

        col_back, col_h, col_btn = st.columns([1, 4, 1])
        with col_back:
            st.markdown("<div style='padding-top:12px'>", unsafe_allow_html=True)
            if st.button(f"← {active_doc}", key="back_btn"):
                _close_subdoc()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_h:
            st.markdown(
                f"<h1 style='font-size:20px; font-weight:700; letter-spacing:0.02em; margin-bottom:2px;'>"
                f"{_hdr_title}</h1>"
                f"<p style='font-size:12px; color:#999; margin-top:0;'>"
                f"{proj_project} &nbsp;&middot;&nbsp; {proj_ref} &nbsp;&middot;&nbsp; Rev {proj_rev}"
                f"</p>",
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='padding-top:14px'>", unsafe_allow_html=True)
            gen_btn = st.button("Generate PDF", type="primary", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # ── REGULAR DOCUMENT EDITOR HEADER (no sub-documents) ────────────────
        col_back, col_h, col_btn = st.columns([1, 4, 1])
        with col_back:
            st.markdown("<div style='padding-top:12px'>", unsafe_allow_html=True)
            if st.button("← Back", key="back_btn"):
                _close_document()
            st.markdown("</div>", unsafe_allow_html=True)
        with col_h:
            st.markdown(
                f"<h1 style='font-size:20px; font-weight:700; letter-spacing:0.02em; margin-bottom:2px;'>"
                f"{active_doc} — {doc_title}</h1>"
                f"<p style='font-size:12px; color:#999; margin-top:0;'>"
                f"{proj_project} &nbsp;&middot;&nbsp; {proj_ref} &nbsp;&middot;&nbsp; Rev {proj_rev}"
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
                    doc_project = dict(PROJECT)
                    if active_subdoc is not None and active_subdoc < len(subdocs):
                        _sd_lbl  = f"{active_doc}.{active_subdoc + 1}"
                        _sd_nm   = subdocs[active_subdoc]["name"]
                        doc_project["title"] = f"{_sd_lbl} — {_sd_nm}"
                        _fname = f"{proj_ref}_{_sd_lbl}.pdf".replace(" ", "_").replace("/", "-")
                    else:
                        doc_project["title"] = f"{active_doc} — {doc_title}"
                        _fname = f"{proj_ref}_{active_doc}.pdf".replace(" ", "_").replace("/", "-")
                    pdf_bytes = build_and_generate_pdf(doc_project, st.session_state.blocks)
                    st.session_state["_pdf_preview"] = {"bytes": pdf_bytes, "fname": _fname}
                    st.rerun()
                except Exception as exc:
                    import traceback
                    st.error(f"PDF generation failed: {exc}")
                    st.code(traceback.format_exc())

    # -- PDF inline preview ---------------------------------------------------
    _pdf = st.session_state.get("_pdf_preview")
    if _pdf:
        st.markdown("---")
        _dl_col, _cls_col, _ = st.columns([2, 1, 3])
        _dl_col.download_button(
            label     = f"Download  {_pdf['fname']}",
            data      = _pdf["bytes"],
            file_name = _pdf["fname"],
            mime      = "application/pdf",
            use_container_width = True,
        )
        if _cls_col.button("Close preview", use_container_width=True):
            st.session_state.pop("_pdf_preview", None)
            st.rerun()
        try:
            import pypdfium2 as _pdfium
            _doc = _pdfium.PdfDocument(_pdf["bytes"])
            _n_pages = len(_doc)
            st.caption(f"{_n_pages} page{'s' if _n_pages != 1 else ''}")
            for _pi in range(_n_pages):
                _page   = _doc[_pi]
                _bitmap = _page.render(scale=2.0)
                _img    = _bitmap.to_pil()
                st.image(_img, use_column_width=True)
                if _pi < _n_pages - 1:
                    st.markdown(
                        "<div style='border-top:2px solid #e8e8e8; margin:6px 0;'></div>",
                        unsafe_allow_html=True,
                    )
        except Exception as _e:
            st.warning(f"Preview unavailable: {_e}. Use the Download button above.")

    # ── Add-block toolbar (collapsible, always at the top) ───────────────────
    _show_panel = st.session_state.get("_add_panel_open", True)
    _toolbar_label = "▲ Hide  ADD BLOCK" if _show_panel else "▼  ADD BLOCK"
    if st.button(_toolbar_label, key="toggle_add_panel"):
        st.session_state._add_panel_open = not _show_panel
        st.rerun()

    if _show_panel:
        st.markdown(
            "<div style='background:#fafafa; border:1px solid #e8e8e8; "
            "border-radius:2px; padding:12px 16px 10px; margin-bottom:12px;'>",
            unsafe_allow_html=True,
        )
        # Quick-add: content blocks in one row
        _qa_c = st.columns(5)
        for _qc, _ql, _qt in zip(
            _qa_c,
            ["+ Heading", "+ Paragraph", "+ Note", "+ Figure", "+ Page break"],
            ["heading",   "text",        "note",   "figure",   "pagebreak"],
        ):
            if _qc.button(_ql, key=f"qa_{_qt}", use_container_width=True):
                st.session_state.blocks.append(_default_block(_qt))
                st.rerun()

        # Calculation block: dropdown + add, plus expanders for library/save/subdoc
        _qa_types_set = {"heading", "text", "note", "figure", "pagebreak"}
        _calc_keys = [k for k in BLOCK_MENU
                      if BLOCK_MENU[k] not in (None,) + tuple(_qa_types_set)]
        _tb_c1, _tb_c2, _tb_c3, _tb_c4, _tb_c5 = st.columns([3, 1, 1, 1, 1])
        _calc_sel = _tb_c1.selectbox(
            "Calc", _calc_keys,
            format_func=lambda k: k,
            label_visibility="collapsed",
            key="add_calc_select",
        )
        if _tb_c2.button("+ Add", key="add_calc_btn",
                         use_container_width=True, type="primary"):
            _btype = BLOCK_MENU.get(_calc_sel)
            if _btype is not None:
                st.session_state.blocks.append(_default_block(_btype))
                st.rerun()

        # Office library inline expander
        _lib_templates = _db.load_all_templates()
        with _tb_c3.expander(f"Library ({len(_lib_templates)})", expanded=False):
            if not _lib_templates:
                st.caption("No templates yet.")
            else:
                for _tpl in _lib_templates:
                    _at = _db.fmt_updated(_tpl.get("created_at", ""))
                    _nb = len(_tpl.get("blocks", []))
                    st.markdown(
                        f"**{_tpl['name']}** · {_nb} blk · {_at}",
                        unsafe_allow_html=False,
                    )
                    _ti1, _ti2 = st.columns([3, 1])
                    if _ti1.button("Insert", key=f"lib_ins_{_tpl['id']}",
                                   use_container_width=True):
                        import copy as _copy, uuid as _uuid
                        for _lb in _tpl["blocks"]:
                            _new = _copy.deepcopy(_lb)
                            _new["id"] = _uuid.uuid4().hex[:8]
                            st.session_state.blocks.append(_new)
                        st.rerun()
                    if _ti2.button("✕", key=f"lib_del_{_tpl['id']}",
                                   use_container_width=True):
                        _db.delete_template(_tpl["id"])
                        st.rerun()

        # Save to library
        with _tb_c4.expander("Save", expanded=False):
            if not st.session_state.blocks:
                st.caption("Add blocks first.")
            else:
                _lib_name = st.text_input("Name", placeholder="e.g. CLT deck",
                                          key="lib_save_name",
                                          label_visibility="collapsed")
                _lib_desc = st.text_input("Desc", placeholder="optional",
                                          key="lib_save_desc",
                                          label_visibility="collapsed")
                if st.button("Save", key="lib_save_btn", type="primary",
                             use_container_width=True):
                    if not _lib_name.strip():
                        st.warning("Enter a name.")
                    else:
                        _db.save_template(
                            name=_lib_name.strip(), description=_lib_desc.strip(),
                            blocks=st.session_state.blocks,
                            user=st.session_state.get("current_user", ""),
                        )
                        st.success(f"✓ Saved")

        # Sub-documents
        if active_subdoc is None:
            with _tb_c5.expander("Sub-docs", expanded=False):
                _sdo_first_name = st.text_input(
                    "First", placeholder="e.g. Loads",
                    key=f"sdo_first_{active_doc}", label_visibility="collapsed")
                _sdo_second_name = st.text_input(
                    "Second (opt.)", placeholder="e.g. Elements",
                    key=f"sdo_second_{active_doc}", label_visibility="collapsed")
                if st.button("Create", key=f"sdo_create_{active_doc}",
                             type="primary", use_container_width=True):
                    if not _sdo_first_name.strip():
                        st.warning("Enter a title.")
                    else:
                        _doc_ref = st.session_state.documents[active_doc]
                        _existing_blks = list(st.session_state.blocks)
                        st.session_state.blocks = []
                        _doc_ref["blocks"] = []
                        _doc_ref.setdefault("subdocs", []).append(
                            {"name": _sdo_first_name.strip(), "blocks": _existing_blks}
                        )
                        if _sdo_second_name.strip():
                            _doc_ref["subdocs"].append(
                                {"name": _sdo_second_name.strip(), "blocks": []}
                            )
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")

    # ── Block list (full-width — no outer column, avoids nesting limit) ───────
    if not st.session_state.blocks:
        st.markdown(
            "<p style='color:#bbb; font-size:13px; padding:24px 0;'>"
            "No blocks yet — use the toolbar above to start building."
            "</p>",
            unsafe_allow_html=True,
        )

    to_delete = set()
    _INLINE_TYPES = {"heading", "text", "note", "figure", "table", "pagebreak"}
    _n_blks = len(st.session_state.blocks)

    for i, block in enumerate(st.session_state.blocks):
        t = block["type"]

        if t in _INLINE_TYPES:
            # Per-block edit toggle — empty blocks start in edit mode
            _ek = f"_blk_edit_{block['id']}"
            if _ek not in st.session_state:
                _auto_edit = (
                    t in ("figure", "table")
                    or not block.get("text", "").strip()
                )
                st.session_state[_ek] = _auto_edit
            _editing = st.session_state[_ek]

            # content | edit | ↑ | ↓ | ✕
            _bc, _tc, _uc, _dnc, _dc = st.columns([14, 1, 1, 1, 1])

            with _bc:
                # ── HEADING ──────────────────────────────────────────────────
                if t == "heading":
                    if _editing:
                        block["text"] = st.text_input(
                            "", block.get("text", ""),
                            key=f"il_h_{block['id']}",
                            placeholder="Section heading…",
                            label_visibility="collapsed",
                        )
                    else:
                        _txt = block.get("text", "")
                        _h_body = _txt if _txt else "<em style='color:#ccc'>Empty heading</em>"
                        st.markdown(
                            f"<p style='font-size:16px; font-weight:700; color:#1C1C1E; "
                            f"margin:6px 0 2px; padding-bottom:4px; "
                            f"border-bottom:1.5px solid #e8e8e8;'>{_h_body}</p>",
                            unsafe_allow_html=True,
                        )

                # ── TEXT ─────────────────────────────────────────────────────
                elif t == "text":
                    if _editing:
                        _tv = block.get("text", "")
                        block["text"] = st.text_area(
                            "", _tv,
                            key=f"il_t_{block['id']}",
                            placeholder="Paragraph text…",
                            label_visibility="collapsed",
                            height=max(80, min(400, _tv.count("\n") * 22 + 80)),
                        )
                    else:
                        _txt = block.get("text", "").strip()
                        if _txt:
                            _html = _txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                            _html = _html.replace("\n\n", "</p><p style='margin:6px 0;'>").replace("\n", "<br>")
                            st.markdown(
                                f"<div style='font-size:13px; color:#1C1C1E; line-height:1.7; "
                                f"padding:4px 0;'><p style='margin:0;'>{_html}</p></div>",
                                unsafe_allow_html=True,
                            )
                        else:
                            st.caption("_Empty paragraph — click ✏ to edit_")

                # ── NOTE ─────────────────────────────────────────────────────
                elif t == "note":
                    if _editing:
                        _nv = block.get("text", "")
                        block["text"] = st.text_area(
                            "", _nv,
                            key=f"il_n_{block['id']}",
                            placeholder="Note / placeholder text…",
                            label_visibility="collapsed",
                            height=max(80, min(300, _nv.count("\n") * 20 + 80)),
                        )
                    else:
                        _txt = block.get("text", "").strip()
                        _note_empty = "<em style='color:#c0886a;'>Empty note — click to edit</em>"
                        _html = (_txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                                     .replace("\n", "<br>")
                                 if _txt else _note_empty)
                        st.markdown(
                            f"<div style='border-left:3px solid #E74825; background:#FFF8F6; "
                            f"padding:8px 12px; font-size:12px; color:#5A2800; "
                            f"line-height:1.65; font-style:italic;'>{_html}</div>",
                            unsafe_allow_html=True,
                        )

                # ── FIGURE ───────────────────────────────────────────────────
                elif t == "figure":
                    EDITORS["figure"](block)

                # ── TABLE ────────────────────────────────────────────────────
                elif t == "table":
                    _tc_val = block.get("caption", "")
                    if _editing:
                        block["caption"] = st.text_input(
                            "Caption", _tc_val,
                            key=f"il_tc_{block['id']}",
                            placeholder="Table 1.1 — …",
                            label_visibility="collapsed",
                        )
                        _hdrs = block.get("headers", ["Column 1", "Column 2"])
                        _hdrs_str = st.text_input(
                            "Columns (pipe-separated)",
                            " | ".join(_hdrs),
                            key=f"il_th_{block['id']}",
                            help="Separate column names with  |  e.g.  Name | Value | Unit",
                        )
                        _new_hdrs = [h.strip() for h in _hdrs_str.split("|") if h.strip()] or _hdrs
                        _nh = len(_new_hdrs)
                        _rows = [(list(r) + [""] * _nh)[:_nh] for r in block.get("rows", [])]
                        _df = (
                            pd.DataFrame(_rows, columns=_new_hdrs)
                            if _rows else pd.DataFrame(columns=_new_hdrs)
                        )
                        _edited = st.data_editor(
                            _df, num_rows="dynamic", use_container_width=True,
                            key=f"il_td_{block['id']}",
                        )
                        block["headers"] = list(_edited.columns)
                        block["rows"] = [
                            [str(c) if c is not None else "" for c in r]
                            for r in _edited.values.tolist()
                        ]
                    else:
                        if _tc_val:
                            st.markdown(
                                f"<p style='font-size:11px; color:#6E6E73; font-style:italic; "
                                f"margin:4px 0 4px;'>{_tc_val}</p>",
                                unsafe_allow_html=True,
                            )
                        _hdrs = block.get("headers", [])
                        _rows = block.get("rows", [])
                        if _hdrs:
                            _df_v = (pd.DataFrame(_rows, columns=_hdrs)
                                     if _rows else pd.DataFrame(columns=_hdrs))
                            st.dataframe(_df_v, use_container_width=True, hide_index=True)
                        else:
                            st.caption("_Empty table — click ✏ to edit_")

                # ── PAGE BREAK ───────────────────────────────────────────────
                elif t == "pagebreak":
                    st.markdown(
                        "<p style='color:#AEAEB2; font-size:11px; text-align:center; "
                        "border-top:1px dashed #ddd; border-bottom:1px dashed #ddd; "
                        "padding:4px 0; margin:4px 0; letter-spacing:0.1em;'>"
                        "PAGE BREAK</p>",
                        unsafe_allow_html=True,
                    )

            # Edit toggle
            with _tc:
                st.markdown("<div style='padding-top:20px;'>", unsafe_allow_html=True)
                if t not in ("pagebreak", "figure"):
                    if _editing:
                        if st.button("✓", key=f"done_{block['id']}", help="Done editing"):
                            st.session_state[_ek] = False
                            st.rerun()
                    else:
                        if st.button("✏", key=f"edit_{block['id']}", help="Edit"):
                            st.session_state[_ek] = True
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # ↑ move up
            with _uc:
                st.markdown("<div style='padding-top:20px;'>", unsafe_allow_html=True)
                if i > 0:
                    if st.button("↑", key=f"up_{block['id']}", help="Move up"):
                        _lst = st.session_state.blocks
                        _lst[i], _lst[i - 1] = _lst[i - 1], _lst[i]
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # ↓ move down
            with _dnc:
                st.markdown("<div style='padding-top:20px;'>", unsafe_allow_html=True)
                if i < _n_blks - 1:
                    if st.button("↓", key=f"dn_{block['id']}", help="Move down"):
                        _lst = st.session_state.blocks
                        _lst[i], _lst[i + 1] = _lst[i + 1], _lst[i]
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            # ✕ delete
            with _dc:
                st.markdown("<div style='padding-top:20px;'>", unsafe_allow_html=True)
                if st.button("✕", key=f"del_{block['id']}", help="Delete"):
                    to_delete.add(block["id"])
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                "<div style='border-bottom:1px solid #f0f0f0; margin:4px 0 10px;'></div>",
                unsafe_allow_html=True,
            )

        else:
            # ── Calculation block — expander, ↑/↓/Delete footer inside ───────
            label   = LABELS.get(t, t)
            summary = _block_summary(block)
            header  = f"**{label}**" + (f"  —  {summary}" if summary else "")
            with st.expander(header, expanded=(t == "custom_calc" and not summary)):
                EDITORS[t](block)
                st.markdown(
                    "<div style='margin-top:8px; padding-top:6px; "
                    "border-top:1px solid #f0f0f0;'></div>",
                    unsafe_allow_html=True,
                )
                _fc1, _fc2, _fc3, _ = st.columns([1, 1, 1, 10])
                with _fc1:
                    if i > 0:
                        if st.button("↑", key=f"up_{block['id']}", help="Move up"):
                            _lst = st.session_state.blocks
                            _lst[i], _lst[i - 1] = _lst[i - 1], _lst[i]
                            st.rerun()
                with _fc2:
                    if i < _n_blks - 1:
                        if st.button("↓", key=f"dn_{block['id']}", help="Move down"):
                            _lst = st.session_state.blocks
                            _lst[i], _lst[i + 1] = _lst[i + 1], _lst[i]
                            st.rerun()
                with _fc3:
                    if st.button("Delete", key=f"del_{block['id']}"):
                        to_delete.add(block["id"])

    if to_delete:
        st.session_state.blocks = [b for b in st.session_state.blocks
                                    if b["id"] not in to_delete]
        st.rerun()

    # Auto-save — outside columns so it always fires on every rerun
    _save_active_project()
