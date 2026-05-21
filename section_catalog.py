"""
Steel profile catalogue — geometry + section properties.

Columns read from steel_profiles.csv:
  designation, family, h_mm, b_mm, tw_mm, tf_mm,
  Wply_cm3   (plastic section modulus, strong axis)
  Iy_cm4     (second moment of area, strong axis)
  weight_kg_per_m, source

All property values come from Euronorm tables.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path


DEFAULT_CSV = Path(__file__).resolve().parent / "steel_profiles.csv"


@lru_cache(maxsize=None)
def load_steel_profiles(csv_path: str | None = None):
    path = Path(csv_path) if csv_path else DEFAULT_CSV
    db = {}
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            key = row['designation'].strip().upper().replace(' ', '')
            db[key] = {
                'designation':     row['designation'].strip(),
                'family':          row['family'].strip(),
                'h_mm':            float(row['h_mm']),
                'b_mm':            float(row['b_mm']),
                'tw_mm':           float(row['tw_mm']),
                'tf_mm':           float(row['tf_mm']),
                'Wply_cm3':        float(row.get('Wply_cm3') or 0) or _estimate_Wply(
                                       float(row['h_mm']), float(row['b_mm']),
                                       float(row['tw_mm']), float(row['tf_mm'])),
                'Iy_cm4':          float(row.get('Iy_cm4') or 0) or _estimate_Iy(
                                       float(row['h_mm']), float(row['b_mm']),
                                       float(row['tw_mm']), float(row['tf_mm'])),
                'weight_kg_per_m': float(row.get('weight_kg_per_m') or 0),
                'source':          row.get('source', '').strip(),
            }
    return db


def _estimate_Wply(h_mm, b_mm, tw_mm, tf_mm) -> float:
    """Approximate W_pl,y [cm³] from idealised I-section (ignores fillets)."""
    hw = max(h_mm - 2.0 * tf_mm, 0.0)
    Wply_mm3 = b_mm * tf_mm * (h_mm - tf_mm) + tw_mm * hw**2 / 4.0
    return Wply_mm3 / 1e3   # mm³ → cm³


def _estimate_Iy(h_mm, b_mm, tw_mm, tf_mm) -> float:
    """Approximate I_y [cm⁴] from idealised I-section rectangles (ignores fillets)."""
    h  = h_mm  / 10.0   # mm → cm
    b  = b_mm  / 10.0
    tw = tw_mm / 10.0
    tf = tf_mm / 10.0
    hw = max(h - 2.0 * tf, 0.0)
    iy_flanges = 2.0 * ((b * tf**3) / 12.0 + b * tf * (hw / 2.0 + tf / 2.0)**2)
    iy_web     = (tw * hw**3) / 12.0
    return iy_flanges + iy_web


def get_steel_profile(designation: str, csv_path: str | None = None):
    key = designation.strip().upper().replace(' ', '')
    db = load_steel_profiles(csv_path)
    if key not in db:
        raise KeyError(
            f"Profile '{designation}' not found in steel profile catalogue. "
            "Add it to steel_profiles.csv or pass the section dimensions explicitly."
        )
    return db[key]


def all_section_names(family: str | None = None) -> list[str]:
    """Return list of all designation strings, optionally filtered by family."""
    db = load_steel_profiles()
    return [
        v['designation'] for v in db.values()
        if family is None or v['family'].upper() == family.upper()
    ]


def estimate_i_major_m4_from_i_dims(h_mm: float, b_mm: float, tw_mm: float, tf_mm: float) -> float:
    """Approximate strong-axis second moment of area [m⁴] from idealised I-section rectangles."""
    return _estimate_Iy(h_mm, b_mm, tw_mm, tf_mm) * 1e-8   # cm⁴ → m⁴
