from __future__ import annotations

import os
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units     import cm
from reportlab.lib           import colors
from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums     import TA_CENTER, TA_LEFT
from reportlab.platypus      import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

W, H = A4


def _get_styles():
    base = getSampleStyleSheet()
    return {
        "title":   base["Title"],
        "heading": base["Heading2"],
        "normal":  base["Normal"],
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
            fontSize=8, textColor=colors.grey,
        ),
        "center": ParagraphStyle(
            "center", parent=base["Normal"],
            alignment=TA_CENTER,
        ),
        "bold_center": ParagraphStyle(
            "bold_center", parent=base["Normal"],
            fontName="Helvetica-Bold", alignment=TA_CENTER,
        ),
        "stego": ParagraphStyle(
            "stego", parent=base["Normal"],
            fontName="Helvetica-Bold",
            textColor=colors.red, alignment=TA_CENTER,
        ),
        "suspicious": ParagraphStyle(
            "suspicious", parent=base["Normal"],
            fontName="Helvetica-Bold",
            textColor=colors.darkorange, alignment=TA_CENTER,
        ),
        "clean": ParagraphStyle(
            "clean", parent=base["Normal"],
            fontName="Helvetica-Bold",
            textColor=colors.green, alignment=TA_CENTER,
        ),
    }


def _label_para(label: str, S: dict) -> Paragraph:
    style = S.get(label.lower(), S["center"])
    return Paragraph(label, style)


def _tbl_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.lightgrey),
        ("FONTNAME",       (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("ALIGN",          (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",          (0, 1), (0, -1),  "LEFT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.grey)
    canvas.drawString(
        2 * cm, 1 * cm,
        f"Image LSB Tool — Forensic Report  |  "
        f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    canvas.drawRightString(W - 2 * cm, 1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _count_labels(results):
    c = {"STEGO": 0, "SUSPICIOUS": 0, "CLEAN": 0}
    for r in results:
        if r["label"] in c:
            c[r["label"]] += 1
    return c


def build_report(results: list[dict], output_path: str, scan_folder: str = "") -> None:
    if not results:
        raise ValueError("No results to report")

    S   = _get_styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm,
        title="LSB Steganalysis Report",
    )

    story = []

    # ── Title + scan info ─────────────────────────────────────────────
    story.append(Paragraph("LSB Steganalysis — Forensic Report", S["title"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceAfter=8))

    counts = _count_labels(results)
    n      = len(results)
    now    = datetime.datetime.now()

    meta = [
        ["Scan Path",      scan_folder or "—"],
        ["Date / Time",    now.strftime("%d %B %Y  %H:%M:%S")],
        ["Total Images",   str(n)],
        ["Stego Detected", str(counts["STEGO"])],
        ["Suspicious",     str(counts["SUSPICIOUS"])],
        ["Clean",          str(counts["CLEAN"])],
    ]
    meta_tbl = Table(meta, colWidths=[4*cm, 13*cm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",       (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",       (0, 0), (-1,-1), 9),
        ("TOPPADDING",     (0, 0), (-1,-1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1,-1), 3),
        ("GRID",           (0, 0), (-1,-1), 0.3, colors.lightgrey),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 16))

    # ── Results table ─────────────────────────────────────────────────
    story.append(Paragraph("Scan Results", S["heading"]))

    col_w = [0.7*cm, 5*cm, 1.8*cm, 1.5*cm, 1.8*cm,
             1.5*cm, 1.5*cm, 1.8*cm, 1.5*cm, 2*cm]
    hdr   = ["#", "Filename", "Label", "Score", "Payload",
             "Entropy", "Contrast", "Correlation", "Energy", "Homogeneity"]

    rows = [hdr]
    for i, r in enumerate(results, 1):
        glcm  = r.get("glcm", [0, 0, 0, 0])
        label = r["label"]
        rows.append([
            str(i),
            os.path.basename(r["file"])[:30],
            _label_para(label, S),
            f"{r['probability']:.4f}",
            f"{r.get('estimated_payload','—')} bpp",
            f"{r.get('entropy', 0):.4f}",
            f"{glcm[0]:.3f}",
            f"{glcm[1]:.4f}",
            f"{glcm[2]:.4f}",
            f"{glcm[3]:.4f}",
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(_tbl_style())
    story.append(tbl)
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Score thresholds:  >= 0.65 → STEGO  |  0.45–0.65 → SUSPICIOUS  |  < 0.45 → CLEAN",
        S["small"],
    ))

    # ── Flagged image details ─────────────────────────────────────────
    flagged = [r for r in results if r["label"] in ("STEGO", "SUSPICIOUS")]
    if flagged:
        story.append(PageBreak())
        story.append(Paragraph("Flagged Image Details", S["heading"]))
        story.append(Paragraph(
            "Per-model detection probabilities for all STEGO and SUSPICIOUS images.",
            S["normal"],
        ))
        story.append(Spacer(1, 10))

        for r in flagged:
            label = r["label"]
            mp    = r.get("model_probabilities", {})

            story.append(Paragraph(
                f"{os.path.basename(r['file'])}  —  {label}  ({r['probability']:.4f})",
                S["bold_center"],
            ))
            story.append(Spacer(1, 4))

            detail = [["Model", "Probability"]]
            for bpp in sorted(mp.keys()):
                detail.append([f"{bpp} bpp", f"{mp[bpp]:.4f}"])
            detail.append(["FINAL (ensemble)", f"{r['probability']:.4f}"])

            dt = Table(detail, colWidths=[5*cm, 5*cm], hAlign="CENTER")
            dt.setStyle(_tbl_style())
            story.append(dt)
            story.append(Spacer(1, 14))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)