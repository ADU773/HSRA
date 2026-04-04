"""
pdf_report.py — Server-side PDF generation using ReportLab.

Produces a clean, paginated, structured PDF with:
  - Cover page (metadata + summary stats)
  - Littering/throwing events table (with CLIP verification)
  - VLM scene description timeline
  - Object track registry (with duration on screen)
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable

# ── Colour palette ────────────────────────────────────────────────────────────
C_PRIMARY   = colors.HexColor("#006978")   # teal
C_ERROR     = colors.HexColor("#B3261E")   # red
C_WARN      = colors.HexColor("#7D5260")   # muted purple
C_INDIGO    = colors.HexColor("#4F46E5")   # clip colour
C_SURFACE   = colors.HexColor("#F8FAFC")   # near-white bg
C_ROW_ALT   = colors.HexColor("#EFF6FF")   # alternate table row
C_BORDER    = colors.HexColor("#CBD5E1")
C_TEXT      = colors.HexColor("#1E293B")
C_MUTED     = colors.HexColor("#64748B")
C_WHITE     = colors.white


def _fmt_ts(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def _duration_str(sec: float) -> str:
    if sec < 60:
        return f"{sec:.2f}s"
    m = int(sec // 60)
    return f"{m}m {sec - m*60:.1f}s"


def _truncate(text: str, max_len: int = 120) -> str:
    return text if len(text) <= max_len else text[:max_len] + "…"


# ── Style helpers ─────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontSize=22, textColor=C_PRIMARY,
                                 fontName="Helvetica-Bold", spaceAfter=4,
                                 alignment=TA_LEFT),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, textColor=C_MUTED,
                                    fontName="Helvetica", spaceAfter=2),
        "section": ParagraphStyle("section", fontSize=13, textColor=C_PRIMARY,
                                   fontName="Helvetica-Bold", spaceBefore=14,
                                   spaceAfter=6, borderPad=2),
        "body": ParagraphStyle("body", fontSize=8.5, textColor=C_TEXT,
                                fontName="Helvetica", leading=13),
        "mono": ParagraphStyle("mono", fontSize=7.5, textColor=C_TEXT,
                                fontName="Courier", leading=12),
        "label": ParagraphStyle("label", fontSize=7, textColor=C_MUTED,
                                 fontName="Helvetica-Bold"),
        "clip_ok": ParagraphStyle("clip_ok", fontSize=7.5, textColor=colors.HexColor("#16A34A"),
                                   fontName="Helvetica-Bold"),
        "clip_err": ParagraphStyle("clip_err", fontSize=7.5, textColor=C_ERROR,
                                    fontName="Helvetica-Bold"),
    }


def _section_header(title: str, styles: dict):
    return [
        HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=4),
        Paragraph(title, styles["section"]),
    ]


def _stat_table(stats: list, styles: dict):
    """Render a horizontal key-value row of summary stats."""
    data = [[Paragraph(v, ParagraphStyle("sv", fontSize=16,
                        fontName="Helvetica-Bold", textColor=C_PRIMARY,
                        alignment=TA_CENTER))
             for _, v in stats],
            [Paragraph(k, ParagraphStyle("sk", fontSize=7,
                        fontName="Helvetica-Bold", textColor=C_MUTED,
                        alignment=TA_CENTER))
             for k, _ in stats]]
    col_w = 170 / len(stats) * mm
    t = Table(data, colWidths=[col_w] * len(stats))
    t.setStyle(TableStyle([
        ("BOX",        (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, C_BORDER),
        ("BACKGROUND", (0, 0), (-1, 0), C_SURFACE),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


# ── Main generator ────────────────────────────────────────────────────────────
def generate_pdf(report_data: dict) -> bytes:
    """
    Generate a full PDF report from the JSON report dict.
    Returns PDF bytes.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="TrashGuard Incident Report",
        author="TrashGuard Analytics",
    )

    st = _styles()
    W = A4[0] - 40 * mm   # usable width
    story = []

    # ── COVER ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("TrashGuard", ParagraphStyle(
        "logo", fontSize=28, textColor=C_PRIMARY, fontName="Helvetica-Bold")))
    story.append(Paragraph("Incident Semantic Analysis Report", ParagraphStyle(
        "cov", fontSize=13, textColor=C_MUTED, fontName="Helvetica", spaceAfter=6)))
    story.append(HRFlowable(width="100%", thickness=2, color=C_PRIMARY, spaceAfter=10))

    generated_at = report_data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    fps          = report_data.get("fps", 0)
    dur          = report_data.get("duration_sec", 0)
    resolution   = f"{report_data.get('width','?')}×{report_data.get('height','?')}"
    total_frames = report_data.get("total_frames", "?")

    story.append(Paragraph(f"Generated: {generated_at}", st["subtitle"]))
    story.append(Paragraph(f"Video: {report_data.get('video_path', 'N/A')}", st["subtitle"]))
    story.append(Paragraph(
        f"Duration: {_fmt_ts(dur)}   FPS: {fps:.1f}   Resolution: {resolution}   Frames: {total_frames}",
        st["subtitle"]
    ))
    story.append(Spacer(1, 8 * mm))

    # Summary stat grid
    events       = report_data.get("throwing_events", [])
    vlm_tl       = report_data.get("vlm_timeline", report_data.get("vlm_descriptions", []))
    tracks       = report_data.get("track_timeline", [])
    clip_conf    = report_data.get("clip_confirmed_count",
                    sum(1 for e in events if e.get("clip_is_littering")))

    stats = [
        ("Persons",         str(report_data.get("unique_persons", 0))),
        ("Trash Items",     str(report_data.get("unique_trash", 0))),
        ("Events",          str(report_data.get("total_events", len(events)))),
        ("CLIP Confirmed",  str(clip_conf)),
        ("VLM Snapshots",   str(len(vlm_tl))),
        ("Tracked Objects", str(len(tracks))),
    ]
    story.append(_stat_table(stats, st))
    story.append(PageBreak())

    # ── SECTION 1: LITTERING EVENTS ───────────────────────────────────────────
    story += _section_header("1.  Littering / Throwing Events", st)

    if not events:
        story.append(Paragraph("No littering events detected.", st["body"]))
    else:
        hdr = ["#", "Time", "Frame", "Person\nTrack", "Trash\nTrack",
               "CLIP Label", "Conf.", "Verified", "Description"]
        col_w = [8*mm, 18*mm, 13*mm, 12*mm, 12*mm, 36*mm, 12*mm, 14*mm, None]
        # last col fills remaining
        used = sum(w for w in col_w[:-1])
        col_w[-1] = W - used

        rows = [hdr]
        for i, evt in enumerate(events, 1):
            clip_label = evt.get("clip_label", "")
            clip_conf_val = evt.get("clip_confidence", 0.0)
            clip_lit  = evt.get("clip_is_littering", False)
            rows.append([
                str(i),
                evt.get("time_formatted", _fmt_ts(evt.get("timestamp", 0))),
                str(evt.get("frame_idx", "")),
                str(evt.get("person_track_id", "")),
                str(evt.get("trash_track_id", "")),
                _truncate(clip_label, 40),
                f"{clip_conf_val*100:.0f}%" if clip_label else "—",
                "YES ⚠" if clip_lit else ("NO" if clip_label else "—"),
                _truncate(evt.get("description", ""), 80),
            ])

        t = Table(rows, colWidths=col_w, repeatRows=1)
        ts = TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), C_PRIMARY),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 7),
            ("INNERGRID",    (0, 0), (-1, -1), 0.25, C_BORDER),
            ("BOX",          (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ])
        # Highlight CLIP confirmed rows red
        for i, evt in enumerate(events, 1):
            if evt.get("clip_is_littering"):
                ts.add("TEXTCOLOR", (7, i), (7, i), C_ERROR)
                ts.add("FONTNAME",  (7, i), (7, i), "Helvetica-Bold")
        t.setStyle(ts)
        story.append(t)

    story.append(PageBreak())

    # ── SECTION 2: VLM SCENE TIMELINE ─────────────────────────────────────────
    story += _section_header("2.  VLM Scene Description Timeline", st)

    if not vlm_tl:
        story.append(Paragraph("No VLM descriptions generated.", st["body"]))
    else:
        for vd in vlm_tl:
            ts_str   = vd.get("time_formatted", _fmt_ts(vd.get("timestamp", 0)))
            frame_n  = vd.get("frame_idx", "")
            desc     = vd.get("description", "")
            active   = vd.get("active_objects", [])
            near_evt = vd.get("nearest_event")

            # Active object summary
            obj_groups: dict = {}
            for o in active:
                cls = o.get("class_name", "?")
                obj_groups[cls] = obj_groups.get(cls, 0) + 1
            obj_str = "  |  ".join(f"{cnt}× {cls}" for cls, cnt in obj_groups.items()) or "No objects"

            header_text = f"⏱  {ts_str}   Frame #{frame_n}   —   {obj_str}"
            if near_evt:
                near_ts = near_evt.get("time_formatted", _fmt_ts(near_evt.get("timestamp", 0)))
                header_text += f"   ⚠ Event @ {near_ts}"

            block = [
                Paragraph(header_text, ParagraphStyle(
                    "tsh", fontSize=7.5, fontName="Helvetica-Bold",
                    textColor=C_PRIMARY, spaceBefore=8, spaceAfter=2)),
                Paragraph(desc, st["mono"]),
            ]

            # CLIP line from nearest event
            if near_evt and near_evt.get("clip_label"):
                clip_pct = round(near_evt.get("clip_confidence", 0) * 100)
                clip_lit = near_evt.get("clip_is_littering", False)
                clip_style = st["clip_err"] if clip_lit else st["clip_ok"]
                verdict = "⚠ Littering Confirmed" if clip_lit else "✓ No Littering"
                block.append(Paragraph(
                    f"CLIP: {near_evt['clip_label']}  ({clip_pct}%)  —  {verdict}",
                    clip_style))

            story.append(KeepTogether(block))

    story.append(PageBreak())

    # ── SECTION 3: OBJECT TRACK REGISTRY ──────────────────────────────────────
    story += _section_header("3.  Tracked Objects Registry", st)

    if not tracks:
        story.append(Paragraph("No tracking data available.", st["body"]))
    else:
        hdr = ["Track ID", "Class", "Model", "First Seen", "Last Seen", "Duration", "Detections"]
        col_w2 = [18*mm, 22*mm, 22*mm, 22*mm, 22*mm, 22*mm, 20*mm]
        used2 = sum(col_w2)
        # distribute leftover
        diff = W - used2
        col_w2[1] += diff

        rows2 = [hdr]
        for tr in tracks:
            dur_s = tr.get("duration_str") or _duration_str(tr.get("duration_sec", 0))
            rows2.append([
                f"#{tr.get('track_id', '')}",
                tr.get("class_name", ""),
                tr.get("source_model", ""),
                tr.get("first_seen_fmt", _fmt_ts(tr.get("first_seen", 0))),
                tr.get("last_seen_fmt",  _fmt_ts(tr.get("last_seen", 0))),
                dur_s,
                str(tr.get("detections", "")),
            ])

        t2 = Table(rows2, colWidths=col_w2, repeatRows=1)
        t2.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), C_PRIMARY),
            ("TEXTCOLOR",    (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0), 7.5),
            ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",     (0, 1), (-1, -1), 7.5),
            ("INNERGRID",    (0, 0), (-1, -1), 0.25, C_BORDER),
            ("BOX",          (0, 0), (-1, -1), 0.5, C_BORDER),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ]))
        story.append(t2)

    # ── Footer note ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER))
    story.append(Paragraph(
        f"TrashGuard Analytics  ·  Generated {generated_at}  ·  CLIP model: openai/clip-vit-base-patch32",
        ParagraphStyle("foot", fontSize=7, textColor=C_MUTED, alignment=TA_CENTER,
                       spaceBefore=4, fontName="Helvetica"),
    ))

    doc.build(story)
    return buf.getvalue()
