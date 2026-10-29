"""
Generate a professional PDF report from brief, scored candidates, drafts, and checklist.

For CJK support, drop `NotoSansSC-Regular.ttf` into a `fonts/` folder next to this file.
Without it, the report falls back to Helvetica (Latin-only); CJK will not render.
"""

import io
from datetime import datetime
from pathlib import Path

from fpdf import FPDF


_FONT_DIR = Path(__file__).parent / "fonts"
_CJK_FONT_CANDIDATES = [
    _FONT_DIR / "NotoSansSC-Regular.ttf",
    _FONT_DIR / "NotoSansSC-Regular.otf",
    _FONT_DIR / "DejaVuSans.ttf",
]


def _pick_font_family(pdf: FPDF) -> str:
    """Try to register a CJK-capable font; fall back to Helvetica."""
    for path in _CJK_FONT_CANDIDATES:
        if path.exists():
            try:
                pdf.add_font("ReportFont", fname=str(path))
                return "ReportFont"
            except Exception:
                continue
    return "Helvetica"


class _Report(FPDF):
    def __init__(self, font_family: str):
        super().__init__()
        self.font_family = font_family
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font(self.font_family, "B", 14)
        self.cell(0, 10, "Creator Sourcing Report", ln=True, align="C")
        self.set_font(self.font_family, "", 9)
        self.cell(
            0, 6,
            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            ln=True, align="C",
        )
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def build_report(
    brief: dict,
    scored_df,
    drafts_by_candidate: dict,
    checklist: list,
) -> bytes:
    """
    Build a PDF report and return raw bytes for st.download_button.

    - brief: dict of campaign details
    - scored_df: pandas DataFrame from score_candidates()
    - drafts_by_candidate: dict {candidate_name: [draft_dict, ...]}
    - checklist: list of strings
    """
    probe = FPDF()
    font_family = _pick_font_family(probe)

    pdf = _Report(font_family)
    pdf.add_page()

    # --- 1. Brief ---
    pdf.set_font(font_family, "B", 12)
    pdf.cell(0, 8, "1. Campaign Brief", ln=True)
    pdf.set_font(font_family, "", 10)
    for key, value in brief.items():
        if value:
            pdf.multi_cell(0, 6, f"{key}: {value}")
    pdf.ln(3)

    # --- 2. Scored candidates ---
    pdf.set_font(font_family, "B", 12)
    pdf.cell(0, 8, "2. Scored Candidates", ln=True)

    cols = ["name", "platform", "followers", "total_score"]
    labels = ["Name", "Platform", "Followers", "Score"]
    widths = [70, 30, 30, 25]

    pdf.set_font(font_family, "B", 9)
    for label, w in zip(labels, widths):
        pdf.cell(w, 7, label, border=1)
    pdf.ln()

    pdf.set_font(font_family, "", 9)
    for _, row in scored_df.head(20).iterrows():
        for col, w in zip(cols, widths):
            val = str(row.get(col, ""))[:40]
            pdf.cell(w, 6, val, border=1)
        pdf.ln()
    pdf.ln(4)

    # --- 3. Outreach drafts ---
    if drafts_by_candidate:
        pdf.set_font(font_family, "B", 12)
        pdf.cell(0, 8, "3. Outreach Drafts", ln=True)
        for name, drafts in drafts_by_candidate.items():
            pdf.set_font(font_family, "B", 10)
            pdf.cell(0, 6, f"Candidate: {name}", ln=True)
            pdf.set_font(font_family, "", 9)
            for d in drafts:
                pdf.set_font(font_family, "B", 9)
                pdf.multi_cell(0, 5, f"[{d.get('style','').upper()}] {d.get('subject','')}")
                pdf.set_font(font_family, "", 9)
                pdf.multi_cell(0, 5, d.get("body", "")[:1000])
                pdf.ln(2)
        pdf.ln(3)

    # --- 4. Compliance checklist ---
    pdf.set_font(font_family, "B", 12)
    pdf.cell(0, 8, "4. Compliance Checklist", ln=True)
    pdf.set_font(font_family, "", 9)
    for item in checklist:
        pdf.multi_cell(0, 5, f"[ ] {item}")

    return bytes(pdf.output())
