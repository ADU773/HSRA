"""
pdf_report.py — Server-side PDF report generation using ReportLab.

Produces a professional, paginated report with embedded annotated frame images:
  - Cover page with video metadata and summary statistics
  - Executive summary paragraph
  - Section 1: Incident Summary Table (all events at a glance)
  - Section 2: Detailed Incident Reports (per-event with frame image + VLM description)
  - Section 3: VLM Scene Description Gallery (frame images + descriptions)
  - Section 4: Tracked Objects Registry
  - Section 5: Detection Class Breakdown
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)

# ── Colour palette ─────────────────────────────────────────────────────────────
C_PRIMARY       = colors.HexColor("#006978")
C_PRIMARY_LIGHT = colors.HexColor("#E0F4F7")
C_ERROR         = colors.HexColor("#B3261E")
C_ERROR_LIGHT   = colors.HexColor("#FDE8E8")
C_ORANGE        = colors.HexColor("#C25400")
C_ORANGE_LIGHT  = colors.HexColor("#FFF0E5")
C_GREEN         = colors.HexColor("#16A34A")
C_INDIGO        = colors.HexColor("#4338CA")
C_INDIGO_LIGHT  = colors.HexColor("#EEF2FF")
C_SURFACE       = colors.HexColor("#F8FAFC")
C_ROW_ALT       = colors.HexColor("#F0F9FA")
C_BORDER        = colors.HexColor("#CBD5E1")
C_BORDER_DARK   = colors.HexColor("#94A3B8")
C_TEXT          = colors.HexColor("#1E293B")
C_MUTED         = colors.HexColor("#64748B")
C_WHITE         = colors.white
C_DARK_BG       = colors.HexColor("#0A1628")
C_VLM_BG        = colors.HexColor("#0D1F1A")


# ── Format helpers ─────────────────────────────────────────────────────────────

def _fmt_ts(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m:02d}:{s:06.3f}"


def _duration_str(sec: float) -> str:
    if sec < 60:
        return f"{sec:.2f}s"
    m = int(sec // 60)
    return f"{m}m {sec - m * 60:.1f}s"


def _trunc(text: str, n: int = 120) -> str:
    return text if len(text) <= n else text[:n] + "\u2026"


def _pct(val: float) -> str:
    return f"{round(val * 100, 1)}%"


# ── Image helpers ──────────────────────────────────────────────────────────────

def _arr_to_rl_image(arr, max_w_mm: float, max_h_mm: float):
    """Convert a BGR numpy array to a ReportLab Image scaled to fit max_w × max_h."""
    if arr is None:
        return None
    try:
        from PIL import Image as PILImage
        rgb = arr[:, :, ::-1].copy()          # BGR → RGB
        pil = PILImage.fromarray(rgb.astype("uint8"))
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=88)
        buf.seek(0)
        iw, ih = pil.size
        scale  = min((max_w_mm * mm) / iw, (max_h_mm * mm) / ih)
        from reportlab.platypus import Image as RLImage
        return RLImage(buf, width=iw * scale, height=ih * scale)
    except Exception:
        return None


def _nearest_frame(frame_idx, frames: dict):
    """Return the numpy array of the nearest annotated frame to frame_idx."""
    if not frames:
        return None
    # frames keys may be int; normalise
    int_frames = {int(k): v for k, v in frames.items()}
    idx = int(frame_idx) if isinstance(frame_idx, (int, float)) else 0
    if idx in int_frames:
        return int_frames[idx]
    return int_frames[min(int_frames.keys(), key=lambda k: abs(k - idx))]


def _frame_image_block(frame_arr, W, max_h_mm, caption_text, sev_color=None):
    """Build a centred image wrapper + caption list."""
    frame_img = _arr_to_rl_image(frame_arr, W / mm, max_h_mm)
    if frame_img is None:
        return []
    border_color = sev_color if sev_color else C_BORDER
    img_wrapper = Table([[frame_img]], colWidths=[W])
    img_wrapper.setStyle(TableStyle([
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOX",           (0, 0), (-1, -1), 1.5, border_color),
        ("BACKGROUND",    (0, 0), (-1, -1), C_DARK_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    caption = Paragraph(
        caption_text,
        ParagraphStyle("cap", fontSize=7, textColor=C_MUTED,
                       fontName="Helvetica", alignment=TA_CENTER, spaceBefore=3),
    )
    return [Spacer(1, 3 * mm), img_wrapper, caption, Spacer(1, 3 * mm)]


# ── Style builder ──────────────────────────────────────────────────────────────

def _styles():
    return {
        # Cover
        "logo":       ParagraphStyle("logo",      fontSize=34, textColor=C_PRIMARY,
                                      fontName="Helvetica-Bold", spaceAfter=2),
        "tagline":    ParagraphStyle("tagline",   fontSize=13, textColor=C_MUTED,
                                      fontName="Helvetica", spaceAfter=4),
        "doc_title":  ParagraphStyle("doc_title", fontSize=16, textColor=C_TEXT,
                                      fontName="Helvetica-Bold", spaceAfter=2),
        # Section headings
        "h1":         ParagraphStyle("h1",        fontSize=14, textColor=C_PRIMARY,
                                      fontName="Helvetica-Bold",
                                      spaceBefore=18, spaceAfter=6),
        "h2":         ParagraphStyle("h2",        fontSize=11, textColor=C_TEXT,
                                      fontName="Helvetica-Bold",
                                      spaceBefore=12, spaceAfter=4),
        "h3":         ParagraphStyle("h3",        fontSize=9,  textColor=C_MUTED,
                                      fontName="Helvetica-Bold",
                                      spaceBefore=6, spaceAfter=3),
        # Body text
        "body":       ParagraphStyle("body",      fontSize=9,  textColor=C_TEXT,
                                      fontName="Helvetica",   leading=14,
                                      alignment=TA_JUSTIFY),
        "body_l":     ParagraphStyle("body_l",    fontSize=9,  textColor=C_TEXT,
                                      fontName="Helvetica",   leading=14),
        "body_b":     ParagraphStyle("body_b",    fontSize=9,  textColor=C_TEXT,
                                      fontName="Helvetica-Bold", leading=14),
        # Monospace / code
        "mono":       ParagraphStyle("mono",      fontSize=8,  textColor=C_TEXT,
                                      fontName="Courier",     leading=12),
        "mono_vlm":   ParagraphStyle("mono_vlm",  fontSize=8,  textColor=C_TEXT,
                                      fontName="Courier",     leading=13,
                                      alignment=TA_JUSTIFY),
        # Table cell styles
        "cell":       ParagraphStyle("cell",      fontSize=8,  textColor=C_TEXT,
                                      fontName="Helvetica",   leading=12),
        "cell_b":     ParagraphStyle("cell_b",    fontSize=8,  textColor=C_TEXT,
                                      fontName="Helvetica-Bold", leading=12),
        "cell_muted": ParagraphStyle("cell_muted",fontSize=7.5,textColor=C_MUTED,
                                      fontName="Helvetica",   leading=11),
        "cell_err":   ParagraphStyle("cell_err",  fontSize=8,  textColor=C_ERROR,
                                      fontName="Helvetica-Bold", leading=12),
        "cell_ok":    ParagraphStyle("cell_ok",   fontSize=8,  textColor=C_GREEN,
                                      fontName="Helvetica-Bold", leading=12),
        "cell_ind":   ParagraphStyle("cell_ind",  fontSize=8,  textColor=C_INDIGO,
                                      fontName="Helvetica-Bold", leading=12),
        # Table header (white on dark)
        "th":         ParagraphStyle("th",        fontSize=7.5,textColor=C_WHITE,
                                      fontName="Helvetica-Bold",
                                      alignment=TA_CENTER, leading=11),
        # Badges / labels
        "badge_err":  ParagraphStyle("badge_err", fontSize=8,  textColor=C_ERROR,
                                      fontName="Helvetica-Bold"),
        "badge_ok":   ParagraphStyle("badge_ok",  fontSize=8,  textColor=C_GREEN,
                                      fontName="Helvetica-Bold"),
        "badge_ind":  ParagraphStyle("badge_ind", fontSize=8,  textColor=C_INDIGO,
                                      fontName="Helvetica-Bold"),
        # VLM description body
        "vlm_desc":   ParagraphStyle("vlm_desc",  fontSize=8.5, textColor=C_TEXT,
                                      fontName="Helvetica",   leading=13,
                                      alignment=TA_JUSTIFY),
        # Footer
        "foot":       ParagraphStyle("foot",      fontSize=7,  textColor=C_MUTED,
                                      fontName="Helvetica",
                                      alignment=TA_CENTER, spaceBefore=4),
    }


# ── Layout helpers ─────────────────────────────────────────────────────────────

def _rule():
    return HRFlowable(width="100%", thickness=1, color=C_PRIMARY, spaceAfter=6)


def _thin_rule():
    return HRFlowable(width="100%", thickness=0.4, color=C_BORDER, spaceAfter=4)


def _section(title: str, st: dict):
    return [_rule(), Paragraph(title, st["h1"])]


def _stat_strip(stats: list, W: float):
    """Horizontal strip of large-number stat tiles."""
    n  = len(stats)
    cw = W / n
    nums = [Paragraph(v, ParagraphStyle("sn", fontSize=20, fontName="Helvetica-Bold",
                                         textColor=C_PRIMARY, alignment=TA_CENTER))
            for _, v in stats]
    lbls = [Paragraph(k, ParagraphStyle("sl", fontSize=6.5, fontName="Helvetica-Bold",
                                         textColor=C_MUTED, alignment=TA_CENTER))
            for k, _ in stats]
    t = Table([nums, lbls], colWidths=[cw] * n)
    t.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 0.8, C_PRIMARY),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, C_BORDER),
        ("BACKGROUND",    (0, 0), (-1, -1), C_PRIMARY_LIGHT),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _base_table_style(header_bg=None):
    bg = header_bg or C_PRIMARY
    return [
        ("BACKGROUND",    (0, 0), (-1, 0), bg),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 7.5),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 7.5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_ROW_ALT]),
        ("INNERGRID",     (0, 0), (-1, -1), 0.25, C_BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5,  C_BORDER_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]


# ── Main PDF builder ───────────────────────────────────────────────────────────

def generate_pdf(report_data: dict, annotated_frames: dict = None) -> bytes:
    """
    Build a professional PDF report combining text analysis with annotated frame images.

    Args:
        report_data:      Enriched JSON dict from generate_report_json().
        annotated_frames: dict[frame_idx → np.ndarray (BGR)] from the analysis job.

    Returns: PDF bytes.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=22 * mm, leftMargin=22 * mm,
        topMargin=24 * mm,   bottomMargin=22 * mm,
        title="TrashGuard — Incident Semantic Analysis Report",
        author="TrashGuard Analytics",
    )

    st    = _styles()
    W     = A4[0] - 44 * mm      # usable width ≈ 167 mm
    frames_dict = annotated_frames or {}
    story = []

    # Pull data
    events    = report_data.get("throwing_events", [])
    vlm_tl    = report_data.get("vlm_timeline", report_data.get("vlm_descriptions", []))
    tracks    = report_data.get("track_timeline", [])
    class_cts = report_data.get("class_counts", {})
    gen_at    = report_data.get("generated_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    fps       = report_data.get("fps", 0)
    dur       = report_data.get("duration_sec", 0)
    res       = f"{report_data.get('width','?')} × {report_data.get('height','?')}"
    video_p   = report_data.get("video_path", "N/A")
    u_persons = report_data.get("unique_persons", 0)
    u_trash   = report_data.get("unique_trash", 0)
    t_events  = report_data.get("total_events", len(events))
    clip_cnt  = report_data.get("clip_confirmed_count",
                                sum(1 for e in events if e.get("clip_is_littering")))
    LIT_LABELS = {
        "a person throwing or littering trash in public",
        "a person dropping garbage or waste on the ground",
    }

    # Pre-build VLM lookup: for each event, find the nearest VLM description
    def _nearest_vlm_desc(event_ts: float) -> str:
        if not vlm_tl:
            return ""
        nearest = min(vlm_tl, key=lambda v: abs(v.get("timestamp", 0) - event_ts))
        if abs(nearest.get("timestamp", 0) - event_ts) <= 15:  # within 15 seconds
            return nearest.get("description", "")
        return ""

    # ═══════════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("TrashGuard", st["logo"]))
    story.append(Paragraph("AI-Powered Urban Littering Detection System", st["tagline"]))
    story.append(HRFlowable(width="100%", thickness=3, color=C_PRIMARY, spaceAfter=10))

    story.append(Paragraph("Incident Semantic Analysis Report", st["doc_title"]))
    story.append(Spacer(1, 4 * mm))

    # Metadata table
    meta_rows = [
        ["Report Generated",  gen_at],
        ["Video File",        _trunc(str(video_p), 75)],
        ["Video Duration",    f"{_fmt_ts(dur)}"
                              f"  ({dur:.1f} seconds)"],
        ["Frame Rate",        f"{fps:.1f} fps"],
        ["Resolution",        res],
        ["Total Frames Analysed", str(report_data.get("total_frames", "—"))],
        ["Analysis Mode",     "YOLO + BoT-SORT + CLIP + VLM"],
    ]
    mt = Table(meta_rows, colWidths=[50 * mm, W - 50 * mm])
    mt.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",     (0, 0), (0, -1), C_MUTED),
        ("TEXTCOLOR",     (1, 0), (1, -1), C_TEXT),
        ("BACKGROUND",    (0, 0), (-1, -1), C_SURFACE),
        ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
        ("INNERGRID",     (0, 0), (-1, -1), 0.2, C_BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    story.append(mt)
    story.append(Spacer(1, 8 * mm))

    # Summary stat strip
    story.append(_stat_strip([
        ("Persons Detected",   str(u_persons)),
        ("Trash Items",        str(u_trash)),
        ("Events Flagged",     str(t_events)),
        ("CLIP Confirmed",     str(clip_cnt)),
        ("VLM Snapshots",      str(len(vlm_tl))),
        ("Tracked Objects",    str(len(tracks))),
    ], W))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ═══════════════════════════════════════════════════════════════════
    story += _section("Executive Summary", st)

    clip_rate = f"{round(clip_cnt / t_events * 100)}%" if t_events > 0 else "N/A"
    summary_text = (
        f"This report presents the results of an automated littering-detection analysis "
        f"performed on the submitted video footage. The video runs for "
        f"<b>{_fmt_ts(dur)}</b> ({dur:.1f} seconds) at <b>{fps:.1f} frames per second</b> "
        f"with a resolution of <b>{res}</b> pixels. "
        f"The analysis pipeline combines YOLOv11 object detection with BoT-SORT multi-object "
        f"tracking, CLIP zero-shot scene classification, and a Vision-Language Model (VLM) "
        f"for rich scene descriptions. "
        f"A total of <b>{u_persons} unique person(s)</b> and "
        f"<b>{u_trash} unique waste item(s)</b> were tracked across the footage. "
        f"The system flagged <b>{t_events} littering or throwing event(s)</b>, "
        f"of which <b>{clip_cnt} event(s)</b> were independently confirmed as littering "
        f"behaviour by the CLIP classifier (confirmation rate: {clip_rate}). "
        f"Each incident below includes an annotated detection frame and the nearest "
        f"VLM scene description for full context."
    )
    story.append(Paragraph(summary_text, st["body"]))
    story.append(Spacer(1, 4 * mm))

    if t_events > 0:
        severity = "HIGH" if clip_cnt > 0 else "MEDIUM"
        sev_color = C_ERROR if clip_cnt > 0 else C_ORANGE
        story.append(Paragraph(
            f"• Incident Severity: <b>{severity}</b>  "
            f"({'Littering confirmed by CLIP AI' if clip_cnt > 0 else 'Events detected; confirmation below CLIP threshold'})",
            ParagraphStyle("sev", fontSize=9, textColor=sev_color,
                           fontName="Helvetica-Bold", leading=14,
                           borderColor=sev_color, borderWidth=0.5,
                           borderPad=6, borderRadius=3,
                           backColor=C_ERROR_LIGHT if clip_cnt > 0 else C_ORANGE_LIGHT),
        ))
        story.append(Spacer(1, 4 * mm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 1: INCIDENT SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════════════
    story += _section("Section 1 — Incident Summary", st)
    story.append(Paragraph(
        "The table below lists every detected littering or throwing event "
        "with its timestamp, involved person and waste track IDs, "
        "and the CLIP AI verification result.",
        st["body"]
    ))
    story.append(Spacer(1, 4 * mm))

    if not events:
        story.append(Paragraph(
            "No littering events were detected in this video.", st["body"]))
    else:
        hdr1 = [
            Paragraph("#",              st["th"]),
            Paragraph("Timestamp",      st["th"]),
            Paragraph("Frame",          st["th"]),
            Paragraph("Person\nTrack",  st["th"]),
            Paragraph("Waste\nTrack",   st["th"]),
            Paragraph("CLIP Confidence",st["th"]),
            Paragraph("Littering\nConfirmed", st["th"]),
        ]
        cw1 = [8*mm, 26*mm, 16*mm, 18*mm, 18*mm, 32*mm, 30*mm]

        rows1 = [hdr1]
        for i, evt in enumerate(events, 1):
            ts_fmt = evt.get("time_formatted", _fmt_ts(evt.get("timestamp", 0)))
            fnum   = evt.get("frame_idx", "—")
            pid    = evt.get("person_track_id", "—")
            tid    = evt.get("trash_track_id",  "—")
            c_lbl  = evt.get("clip_label", "")
            c_pct  = round(evt.get("clip_confidence", 0) * 100, 1)
            c_lit  = evt.get("clip_is_littering", False)

            conf_txt   = f"{c_lbl[:22]}… ({c_pct}%)" if c_lbl else "—"
            verdict    = "YES  ⚠" if c_lit else ("NO" if c_lbl else "—")
            vstyle     = st["cell_err"] if c_lit else (st["cell_ok"] if c_lbl else st["cell"])

            rows1.append([
                Paragraph(str(i),    st["cell_b"]),
                Paragraph(ts_fmt,    st["cell_b"]),
                Paragraph(str(fnum), st["cell"]),
                Paragraph(f"#{pid}", st["cell_b"]),
                Paragraph(f"#{tid}", st["cell_b"]),
                Paragraph(conf_txt,  st["cell_muted"]),
                Paragraph(verdict,   vstyle),
            ])

        t1 = Table(rows1, colWidths=cw1, repeatRows=1)
        ts1 = _base_table_style()
        for ri, evt in enumerate(events, 1):
            if evt.get("clip_is_littering"):
                ts1.append(("BACKGROUND", (0, ri), (-1, ri), C_ERROR_LIGHT))
        t1.setStyle(TableStyle(ts1))
        story.append(t1)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 2: DETAILED INCIDENT REPORTS WITH FRAME IMAGES
    # ═══════════════════════════════════════════════════════════════════
    story += _section("Section 2 — Detailed Incident Reports", st)
    story.append(Paragraph(
        "Each entry below provides the full analysis for one detected incident, "
        "including the annotated detection frame image showing exact object positions, "
        "the nearest VLM scene description, CLIP zero-shot classification scores, "
        "and all tracking identifiers.",
        st["body"]
    ))
    story.append(Spacer(1, 4 * mm))

    if not events:
        story.append(Paragraph("No littering events detected.", st["body"]))
    else:
        for i, evt in enumerate(events, 1):
            ts_s   = evt.get("timestamp", 0)
            ts_fmt = evt.get("time_formatted", _fmt_ts(ts_s))
            fnum   = evt.get("frame_idx", "—")
            pid    = evt.get("person_track_id", "—")
            tid    = evt.get("trash_track_id",  "—")
            desc   = evt.get("description", "")
            c_lbl  = evt.get("clip_label", "")
            c_pct  = round(evt.get("clip_confidence", 0) * 100, 1)
            c_lit  = evt.get("clip_is_littering", False)
            c_scrs = evt.get("clip_all_scores", {})

            # Find nearest VLM description for this event
            vlm_desc = _nearest_vlm_desc(ts_s)

            # Incident heading
            sev_bg  = C_ERROR_LIGHT if c_lit else (C_ORANGE_LIGHT if c_lbl else C_PRIMARY_LIGHT)
            sev_clr = C_ERROR if c_lit else (C_ORANGE if c_lbl else C_PRIMARY)
            verdict = ("LITTERING CONFIRMED  ⚠" if c_lit
                       else ("FLAGGED — BELOW THRESHOLD" if c_lbl else "DETECTED"))

            hdr_data = [[
                Paragraph(f"Incident #{i}", ParagraphStyle(
                    f"ih{i}", fontSize=11, fontName="Helvetica-Bold",
                    textColor=sev_clr)),
                Paragraph(f"Timestamp: {ts_fmt}    {verdict}",
                          ParagraphStyle(f"ihd{i}", fontSize=9,
                                         fontName="Helvetica-Bold",
                                         textColor=sev_clr,
                                         alignment=TA_RIGHT)),
            ]]
            ihdr = Table(hdr_data, colWidths=[W * 0.45, W * 0.55])
            ihdr.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), sev_bg),
                ("BOX",           (0, 0), (-1, -1), 0.8, sev_clr),
                ("TOPPADDING",    (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING",   (0, 0), (-1, -1), 10),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ]))

            # Detail attributes table
            attr_rows = [
                ["Timestamp",           ts_fmt],
                ["Frame Number",        str(fnum)],
                ["Person Track ID",     f"#{pid}"],
                ["Waste / Trash Track ID", f"#{tid}"],
                ["Seconds into video",  f"{ts_s:.2f} s   ({ts_s / dur * 100:.1f}% of video)" if dur > 0 else f"{ts_s:.2f}s"],
            ]
            if c_lbl:
                attr_rows += [
                    ["CLIP Best Label",      _trunc(c_lbl, 65)],
                    ["CLIP Confidence",      f"{c_pct}%"],
                    ["Littering Verdict",    "YES — Littering behaviour confirmed" if c_lit
                                             else "NO — Below littering confidence threshold"],
                ]

            at = Table(attr_rows, colWidths=[45 * mm, W - 45 * mm])
            at_sty = [
                ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR",     (0, 0), (0, -1), C_MUTED),
                ("TEXTCOLOR",     (1, 0), (1, -1), C_TEXT),
                ("INNERGRID",     (0, 0), (-1, -1), 0.2, C_BORDER),
                ("BOX",           (0, 0), (-1, -1), 0.5, C_BORDER),
                ("BACKGROUND",    (0, 0), (-1, -1), C_WHITE),
                ("ROWBACKGROUNDS",(0, 0), (-1, -1), [C_WHITE, C_SURFACE]),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ]
            if c_lbl:
                lit_r = len(attr_rows) - 1
                at_sty.append(("TEXTCOLOR",  (1, lit_r), (1, lit_r),
                                C_ERROR if c_lit else C_GREEN))
                at_sty.append(("FONTNAME",   (1, lit_r), (1, lit_r), "Helvetica-Bold"))
            at.setStyle(TableStyle(at_sty))

            # ── Annotated frame image ──────────────────────────────────────────
            frame_arr  = _nearest_frame(fnum, frames_dict)
            caption    = (
                f"Detection Frame #{fnum}  ·  {ts_fmt}  ·  "
                f"Person #{pid} / Waste #{tid}  ·  "
                f"{'⚠ LITTERING CONFIRMED' if c_lit else 'Flagged event'}"
            )
            frame_block = _frame_image_block(frame_arr, W, 95, caption, sev_clr)

            # ── VLM description (nearest snapshot) ────────────────────────────
            scene_block = []
            if vlm_desc:
                scene_block = [
                    Paragraph("VLM Scene Description (nearest snapshot)", st["h3"]),
                    Paragraph(vlm_desc, st["vlm_desc"]),
                    Spacer(1, 3 * mm),
                ]
            elif desc:
                # Fall back to the auto-generated event description
                scene_block = [
                    Paragraph("Scene Description", st["h3"]),
                    Paragraph(desc, st["body"]),
                    Spacer(1, 3 * mm),
                ]

            # ── CLIP / VLM score breakdown ───────────────────────────────────
            clip_block = []
            if c_scrs:
                # Determine whether scores are numeric (CLIP) or text (VLM)
                # Use try/except so numpy types, strings, etc. never crash this
                try:
                    _numeric_scores = {k: float(v) for k, v in c_scrs.items()}
                    _all_numeric = True
                except (TypeError, ValueError):
                    _all_numeric = False

                if _all_numeric:
                    score_rows = sorted(c_scrs.items(), key=lambda x: -float(x[1]))
                    clip_hdr   = [
                        Paragraph("Classification Label", st["th"]),
                        Paragraph("Score",  st["th"]),
                        Paragraph("Result", st["th"]),
                    ]
                    clip_data  = [clip_hdr]
                    for lbl, scr in score_rows:
                        pct_v   = round(float(scr) * 100, 1)
                        is_lit  = lbl in LIT_LABELS
                        l_style = st["cell_err"] if (is_lit and pct_v > 30) else st["cell_muted"]
                        r_style = st["cell_err"] if (is_lit and pct_v > 30) else st["cell_ok"]
                        result  = "Littering" if is_lit else "Non-littering"
                        clip_data.append([
                            Paragraph(_trunc(lbl, 60), l_style),
                            Paragraph(f"{pct_v}%",     l_style),
                            Paragraph(result,           r_style),
                        ])
                    ct = Table(clip_data, colWidths=[W - 42 * mm, 18 * mm, 24 * mm],
                               repeatRows=1)
                    ct_sty = _base_table_style(C_INDIGO)
                    for ri, (lbl, scr) in enumerate(score_rows, 1):
                        if lbl in LIT_LABELS:
                            ct_sty.append(("BACKGROUND", (0, ri), (-1, ri), C_ERROR_LIGHT))
                    ct.setStyle(TableStyle(ct_sty))
                    clip_block = [
                        Paragraph("CLIP Zero-Shot Classification Scores", st["h3"]),
                        Paragraph(
                            "The following scores represent the model's confidence across "
                            "all candidate scene labels:",
                            st["body_l"]),
                        Spacer(1, 2 * mm),
                        ct,
                        Spacer(1, 3 * mm),
                    ]
                else:
                    # VLM returns text answers — display as labelled paragraphs
                    vlm_score_items = [
                        Paragraph("VLM Verification Output", st["h3"]),
                    ]
                    for lbl, val in c_scrs.items():
                        vlm_score_items.append(
                            Paragraph(f"<b>{_trunc(lbl, 40)}:</b> {_trunc(str(val), 200)}",
                                      st["vlm_desc"])
                        )
                    vlm_score_items.append(Spacer(1, 3 * mm))
                    clip_block = vlm_score_items

            story.append(KeepTogether([ihdr, Spacer(1, 3 * mm), at]))
            story.extend(frame_block)
            story.extend(scene_block + clip_block)
            story.append(_thin_rule())
            story.append(Spacer(1, 6 * mm))

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 3: VLM SCENE DESCRIPTION GALLERY
    # ═══════════════════════════════════════════════════════════════════
    story += _section("Section 3 — VLM Scene Description Gallery", st)
    story.append(Paragraph(
        "The Vision-Language Model (VLM) was sampled at regular intervals throughout "
        "the video to produce natural-language descriptions of the scene. "
        "Each entry below shows the annotated detection frame image at that moment "
        "alongside the VLM's description and any active objects.",
        st["body"]
    ))
    story.append(Spacer(1, 4 * mm))

    if not vlm_tl:
        story.append(Paragraph("No VLM descriptions were generated.", st["body"]))
    else:
        for vi, vd in enumerate(vlm_tl, 1):
            ts_str    = vd.get("time_formatted", _fmt_ts(vd.get("timestamp", 0)))
            vfnum     = vd.get("frame_idx", 0)
            desc_v    = vd.get("description", "—")
            active    = vd.get("active_objects", [])
            near_evt  = vd.get("nearest_event")

            # Object summary
            obj_grp: dict = {}
            for o in active:
                cls = o.get("class_name", "?")
                obj_grp[cls] = obj_grp.get(cls, 0) + 1
            obj_str = "  |  ".join(f"{n}× {c}" for c, n in sorted(obj_grp.items())) or "No objects detected"

            # Near event badge text
            near_txt = ""
            if near_evt:
                ne_ts  = near_evt.get("time_formatted", _fmt_ts(near_evt.get("timestamp", 0)))
                ne_lit = near_evt.get("clip_is_littering", False)
                near_txt = f"  ⚠ NEAREST EVENT: {ne_ts}{'  — LITTERING CONFIRMED' if ne_lit else ''}"

            # VLM snapshot header
            snap_hdr_color = C_ERROR if (near_evt and near_evt.get("clip_is_littering")) else C_PRIMARY
            snap_hdr_bg    = C_ERROR_LIGHT if (near_evt and near_evt.get("clip_is_littering")) else C_PRIMARY_LIGHT

            snap_hdr_data = [[
                Paragraph(
                    f"Snapshot #{vi}  ·  {ts_str}  ·  Frame #{vfnum}",
                    ParagraphStyle(f"sh{vi}", fontSize=9, fontName="Helvetica-Bold",
                                   textColor=snap_hdr_color)),
                Paragraph(
                    near_txt if near_txt else f"Active: {obj_str}",
                    ParagraphStyle(f"shd{vi}", fontSize=7.5, fontName="Helvetica",
                                   textColor=snap_hdr_color, alignment=TA_RIGHT)),
            ]]
            snap_hdr = Table(snap_hdr_data, colWidths=[W * 0.5, W * 0.5])
            snap_hdr.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), snap_hdr_bg),
                ("BOX",           (0, 0), (-1, -1), 0.5, snap_hdr_color),
                ("TOPPADDING",    (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ]))

            # Annotated frame for this VLM snapshot
            vfram_arr  = _nearest_frame(vfnum, frames_dict)
            vcaption   = (
                f"Frame #{vfnum}  ·  {ts_str}  ·  "
                f"Objects: {obj_str}"
                + (f"  ·  {near_txt.strip()}" if near_txt else "")
            )
            vframe_block = _frame_image_block(vfram_arr, W, 80, vcaption, snap_hdr_color)

            # Description text
            desc_block = [
                Paragraph("Scene Description", st["h3"]),
                Paragraph(desc_v, st["vlm_desc"]),
            ]

            # Active objects table (compact)
            obj_block = []
            if obj_grp:
                obj_rows = [[
                    Paragraph("Object Class", st["th"]),
                    Paragraph("Count",        st["th"]),
                    Paragraph("Track IDs",    st["th"]),
                ]]
                cls_track_map: dict = {}
                for o in active:
                    cls = o.get("class_name", "?")
                    tid = o.get("track_id", "?")
                    cls_track_map.setdefault(cls, []).append(f"#{tid}")
                for cls, ids in sorted(cls_track_map.items()):
                    is_trash = cls not in {"person","car","truck","bus","bicycle","motorcycle"}
                    cls_style = st["cell_err"] if is_trash else (st["cell_ind"] if cls == "person" else st["cell"])
                    obj_rows.append([
                        Paragraph(cls, cls_style),
                        Paragraph(str(len(ids)), st["cell_b"]),
                        Paragraph(", ".join(ids[:8]) + ("…" if len(ids) > 8 else ""), st["cell_muted"]),
                    ])
                ot = Table(obj_rows, colWidths=[40*mm, 16*mm, W-56*mm], repeatRows=1)
                ot.setStyle(TableStyle(_base_table_style(C_PRIMARY)))
                obj_block = [
                    Spacer(1, 2 * mm),
                    Paragraph("Active Objects at This Timestamp", st["h3"]),
                    ot,
                ]

            story.append(KeepTogether([snap_hdr]))
            story.extend(vframe_block)
            story.extend(desc_block)
            story.extend(obj_block)
            story.append(Spacer(1, 6 * mm))
            story.append(_thin_rule())

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 4: TRACKED OBJECTS REGISTRY
    # ═══════════════════════════════════════════════════════════════════
    story += _section("Section 4 — Tracked Objects Registry", st)
    story.append(Paragraph(
        "All unique objects tracked throughout the video, with first appearance, "
        "last appearance, duration on screen, and total detection count.",
        st["body"]
    ))
    story.append(Spacer(1, 4 * mm))

    if not tracks:
        story.append(Paragraph("No tracking data available.", st["body"]))
    else:
        tr_hdr = [
            Paragraph("Track ID",   st["th"]),
            Paragraph("Class",      st["th"]),
            Paragraph("Model",      st["th"]),
            Paragraph("First Seen", st["th"]),
            Paragraph("Last Seen",  st["th"]),
            Paragraph("Duration",   st["th"]),
            Paragraph("Detections", st["th"]),
        ]
        tr_cw = [16*mm, 22*mm, 22*mm, 24*mm, 24*mm, 22*mm, None]
        tr_cw[-1] = W - sum(c for c in tr_cw if c)

        tr_rows = [tr_hdr]
        for tr in tracks:
            dur_s = tr.get("duration_str") or _duration_str(tr.get("duration_sec", 0))
            cls   = tr.get("class_name", "")
            src   = tr.get("source_model", "")
            is_trash  = src == "custom"
            cls_style = st["cell_err"] if is_trash else st["cell_ind"] if cls == "person" else st["cell"]
            tr_rows.append([
                Paragraph(f"#{tr.get('track_id', '')}",          st["cell_b"]),
                Paragraph(cls,                                    cls_style),
                Paragraph(src,                                    st["cell_muted"]),
                Paragraph(tr.get("first_seen_fmt", _fmt_ts(tr.get("first_seen", 0))),
                          st["cell"]),
                Paragraph(tr.get("last_seen_fmt",  _fmt_ts(tr.get("last_seen",  0))),
                          st["cell"]),
                Paragraph(dur_s,                                  st["cell_b"]),
                Paragraph(str(tr.get("detections", "")),          st["cell_b"]),
            ])

        tt = Table(tr_rows, colWidths=tr_cw, repeatRows=1)
        tt.setStyle(TableStyle(_base_table_style()))
        story.append(tt)

    story.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════
    # SECTION 5: DETECTION CLASS BREAKDOWN
    # ═══════════════════════════════════════════════════════════════════
    story += _section("Section 5 — Detection Class Breakdown", st)
    story.append(Paragraph(
        "Total number of individual frame-level detections per object class "
        "across the entire video.",
        st["body"]
    ))
    story.append(Spacer(1, 4 * mm))

    if not class_cts:
        story.append(Paragraph("No detection data available.", st["body"]))
    else:
        total_dets = sum(class_cts.values())
        cb_hdr = [
            Paragraph("Object Class",  st["th"]),
            Paragraph("Detections",    st["th"]),
            Paragraph("% of Total",    st["th"]),
            Paragraph("Type",          st["th"]),
        ]
        cb_cw = [50 * mm, 30 * mm, 30 * mm, None]
        cb_cw[-1] = W - sum(c for c in cb_cw if c)
        cb_rows = [cb_hdr]
        for cls, cnt in sorted(class_cts.items(), key=lambda x: -float(x[1])):
            pct_v  = round(cnt / total_dets * 100, 1) if total_dets else 0
            is_tr  = cls not in {"person","car","truck","bus","bicycle","motorcycle"}
            ctype  = "Waste / Trash" if is_tr else "Person/Vehicle"
            cstyle = st["cell_err"] if is_tr else st["cell_ind"] if cls == "person" else st["cell"]
            cb_rows.append([
                Paragraph(cls,         cstyle),
                Paragraph(str(cnt),    st["cell_b"]),
                Paragraph(f"{pct_v}%", st["cell"]),
                Paragraph(ctype,       st["cell_err"] if is_tr else st["cell_muted"]),
            ])

        tc = Table(cb_rows, colWidths=cb_cw, repeatRows=1)
        tc.setStyle(TableStyle(_base_table_style()))
        story.append(tc)

    # ═══════════════════════════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_BORDER, spaceAfter=6))
    story.append(Paragraph(
        f"TrashGuard Analytics  ·  Report generated: {gen_at}  ·  "
        "Detection models: YOLOv11 (yolo11n.pt) + custom (best.pt)  ·  "
        "Verification: openai/clip-vit-base-patch32",
        st["foot"]
    ))

    doc.build(story)
    return buf.getvalue()
