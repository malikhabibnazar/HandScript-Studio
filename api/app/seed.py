"""Seed data so a fresh database matches the studio's sample workspace."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Activity,
    AppSetting,
    BatchJob,
    Document,
    ExportRecord,
    Profile,
    Template,
    utcnow,
)

DEFAULT_SETTINGS = {
    "workspace": "HandScript",
    "output_dir": "exports",
    "default_template_id": "tpl-thankyou",
    "default_profile_id": "pf-amelia",
    "theme": "light",
    "ui_scale": 100,
    "reduce_motion": False,
    "export_format": "PDF",
    "resolution": "300 dpi",
    "pause_on_error": False,
    "notify_on_complete": True,
    "printer": "System Default",
    "page_scaling": "Actual size",
    "print_margins": "Minimal",
    "onboarding_complete": False,
}


def _ago(**kwargs):
    return utcnow() - timedelta(**kwargs)


def _samples(prefix: str, n: int, base_quality: int) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append({
            "id": f"{prefix}-s{i + 1}",
            "filename": f"sample_{i + 1:02d}.png",
            "added": _ago(days=max(0, 12 - i)).isoformat(),
            "quality": min(99, base_quality + (i % 5) * 2),
            "characters": 48 + (i % 7) * 3,
        })
    return rows


def _card_elements() -> list[dict]:
    return [
        {"id": "el-greet", "type": "Text", "name": "Greeting", "x": 0.4, "y": 0.35,
         "width": 5.2, "height": 0.5, "align": "left", "font_size": 22,
         "content": "Dear friend,", "visible": True},
        {"id": "el-code", "type": "Data Field", "name": "Code", "x": 0.4, "y": 0.95,
         "width": 5.2, "height": 0.4, "align": "left", "font_size": 16,
         "content": "CODE: {code}", "visible": True},
        {"id": "el-body", "type": "Text", "name": "Body", "x": 0.4, "y": 1.5,
         "width": 5.2, "height": 1.9, "align": "left", "font_size": 14,
         "content": "Thank you for being part of our community this year. "
                    "We wanted to send a little note of appreciation.",
         "visible": True},
        {"id": "el-div", "type": "Divider", "name": "Divider", "x": 0.4, "y": 3.55,
         "width": 5.2, "height": 0.04, "align": "left", "font_size": 12,
         "content": "", "visible": True},
        {"id": "el-sign", "type": "Text", "name": "Signature", "x": 0.4, "y": 3.7,
         "width": 3.4, "height": 0.5, "align": "left", "font_size": 16,
         "content": "Warmly, {sender}", "visible": True},
    ]


def _envelope_elements() -> list[dict]:
    return [
        {"id": "el-return", "type": "Address", "name": "Return Address", "x": 0.35, "y": 0.3,
         "width": 3.2, "height": 0.9, "align": "left", "font_size": 11,
         "content": "{sender}\n{return_street}\n{return_city}", "visible": True},
        {"id": "el-recipient", "type": "Address", "name": "Recipient", "x": 3.4, "y": 1.7,
         "width": 5.4, "height": 1.3, "align": "left", "font_size": 14,
         "content": "{first_name} {last_name}\n{street}\n{city}, {state} {zip}", "visible": True},
    ]


def _ensure_code_field(db: Session) -> None:
    """Give existing card templates a CODE line so imported codes have somewhere to print."""
    for template in db.scalars(select(Template)).all():
        if "Card" not in (template.kind or ""):
            continue
        elements = [dict(item) for item in (template.elements or [])]
        changed = False
        for item in elements:
            if item.get("content") == "Dear {first_name},":
                item["content"] = "Dear friend,"
                changed = True
        if any("{code}" in str(item.get("content") or "") for item in elements):
            if changed:
                template.elements = elements
            continue
        changed = True
        elements.append({
            "id": f"el-code-{template.id[-6:]}",
            "type": "Data Field",
            "name": "Code",
            "x": 0.4,
            "y": 0.95,
            "width": max(1.0, float(template.width_in) - 0.8),
            "height": 0.4,
            "align": "left",
            "font_size": 16,
            "content": "CODE: {code}",
            "visible": True,
        })
        if changed:
            template.elements = elements


def seed_if_empty(db: Session) -> None:
    existing = db.scalar(select(func.count()).select_from(Profile))
    if existing:
        if db.get(AppSetting, "app") is None:
            db.add(AppSetting(key="app", value=DEFAULT_SETTINGS))
        for profile in db.scalars(select(Profile)).all():
            if not isinstance(profile.style, dict):
                profile.style = {"style_id": 9, "bias": 0.75, "variation": 0.15}
        _ensure_code_field(db)
        return

    db.add_all([
        Profile(
            id="pf-amelia", name="Amelia — Casual Script",
            description="Relaxed everyday cursive with light slant. Great for personal notes and cards.",
            status="Ready", samples=_samples("pf-amelia", 12, 88), created=_ago(days=31),
            is_default=True, preview_text="Thank you so much",
            analysis={
                "character_coverage": 94, "sample_quality": 91, "samples_analyzed": 12,
                "avg_stroke_width": 0.42, "slant_degrees": 6.5, "baseline_stability": 88,
                "spacing_consistency": 90,
                "notes": [
                    "Graves uses built-in style primers. Uploaded samples are stored for a future model.",
                    "This profile is primed with Graves style 9.",
                ],
            },
            style={"style_id": 9, "bias": 0.75, "variation": 0.15},
        ),
        Profile(
            id="pf-theo", name="Theodore — Formal Print",
            description="Clean upright print suited to envelopes and formal correspondence.",
            status="Ready", samples=_samples("pf-theo", 10, 90), created=_ago(days=22),
            preview_text="Dear Mr. Harrington",
            analysis={
                "character_coverage": 97, "sample_quality": 93, "samples_analyzed": 10,
                "avg_stroke_width": 0.38, "slant_degrees": 1.2, "baseline_stability": 95,
                "spacing_consistency": 92,
                "notes": [
                    "Graves uses built-in style primers. Uploaded samples are stored for a future model.",
                    "This profile is primed with Graves style 12.",
                ],
            },
            style={"style_id": 12, "bias": 0.9, "variation": 0.05},
        ),
        Profile(
            id="pf-mira", name="Mira — Quick Note",
            description="Fast, loose handwriting captured from quick notes.",
            status="Processing", samples=_samples("pf-mira", 7, 72), created=_ago(days=3),
            preview_text="See you soon!", analysis=None,
            style={"style_id": 7, "bias": 0.4, "variation": 0.2},
        ),
        Profile(
            id="pf-jonas", name="Jonas — Draft",
            description="Early capture — needs a few more clean samples before use.",
            status="Needs Review", samples=_samples("pf-jonas", 4, 58), created=_ago(days=1),
            preview_text="Sample text",
            analysis={
                "character_coverage": 61, "sample_quality": 64, "samples_analyzed": 4,
                "avg_stroke_width": 0.55, "slant_degrees": 12.0, "baseline_stability": 66,
                "spacing_consistency": 59,
                "notes": [
                    "Graves uses built-in style primers. Uploaded samples are stored for a future model.",
                    "Sample measurements below are placeholders, not a photo match.",
                ],
            },
            style={"style_id": 9, "bias": 0.75, "variation": 0.15},
        ),
        Profile(
            id="pf-coral", name="Coral — Decorative",
            description="Looping decorative hand. The last analysis run did not finish.",
            status="Error", samples=_samples("pf-coral", 6, 70), created=_ago(days=9),
            preview_text="Congratulations", analysis=None,
            style={"style_id": 9, "bias": 0.5, "variation": 0.25},
        ),
    ])

    db.add_all([
        Template(
            id="tpl-thankyou", name="Thank-You Card", kind="4×6 Card",
            width_in=6, height_in=4, status="Published", modified=_ago(days=2),
            elements=_card_elements(), margin_in=0.25,
            description="Personal thank-you card with greeting, body and signature blocks.",
        ),
        Template(
            id="tpl-invite", name="Event Invitation", kind="4×6 Card",
            width_in=6, height_in=4, status="Published", modified=_ago(days=6),
            elements=_card_elements(), margin_in=0.25,
            description="4×6 invitation layout with data placeholders.",
        ),
        Template(
            id="tpl-env-standard", name="Standard #10 Envelope", kind="#10 Envelope",
            width_in=9.5, height_in=4.125, status="Published", modified=_ago(days=1),
            elements=_envelope_elements(), margin_in=0.25,
            description="Classic #10 business envelope with return and recipient address.",
        ),
        Template(
            id="tpl-env-formal", name="Formal #10 Envelope", kind="#10 Envelope",
            width_in=9.5, height_in=4.125, status="Draft", modified=_ago(days=4),
            elements=_envelope_elements(), margin_in=0.3,
            description="Centered formal envelope variant. Still a draft.",
        ),
    ])

    docs = [
        ("doc-001", "Holiday Thank-You — Batch A", "tpl-thankyou", "Thank-You Card", "pf-amelia", "Amelia — Casual Script", "Completed", "PDF", 2, 1),
        ("doc-002", "Q4 Donor Notes", "tpl-thankyou", "Thank-You Card", "pf-theo", "Theodore — Formal Print", "Ready", "Combined PDF", 1, 3),
        ("doc-003", "Spring Gala Invitations", "tpl-invite", "Event Invitation", "pf-amelia", "Amelia — Casual Script", "Generating", "PDF", 1, 0),
        ("doc-004", "Welcome Letters", "tpl-thankyou", "Thank-You Card", "pf-theo", "Theodore — Formal Print", "Draft", "PNG", 1, 5),
        ("doc-005", "Envelope Run — Members", "tpl-env-standard", "Standard #10 Envelope", "pf-theo", "Theodore — Formal Print", "Completed", "PDF", 1, 8),
        ("doc-006", "Partner Appreciation", "tpl-thankyou", "Thank-You Card", "pf-amelia", "Amelia — Casual Script", "Failed", "PDF", 1, 2),
        ("doc-007", "Reunion Save-the-Dates", "tpl-invite", "Event Invitation", "pf-mira", "Mira — Quick Note", "Draft", "PDF", 1, 6),
        ("doc-008", "Board Thank-You", "tpl-thankyou", "Thank-You Card", "pf-theo", "Theodore — Formal Print", "Ready", "PDF", 1, 1),
        ("doc-009", "Formal Envelopes — VIP", "tpl-env-formal", "Formal #10 Envelope", "pf-theo", "Theodore — Formal Print", "Ready", "Combined PDF", 1, 2),
        ("doc-010", "Volunteer Notes", "tpl-thankyou", "Thank-You Card", "pf-amelia", "Amelia — Casual Script", "Completed", "PNG", 1, 10),
    ]
    for doc_id, name, tid, tname, pid, pname, status, fmt, pages, days in docs:
        db.add(Document(
            id=doc_id, name=name, template_id=tid, template_name=tname,
            profile_id=pid, profile_name=pname, status=status, export_format=fmt,
            created=_ago(days=days + 2), modified=_ago(days=days), pages=pages, fields={},
        ))

    db.add_all([
        BatchJob(
            id="bt-001", name="Holiday Thank-You — Batch A", template_id="tpl-thankyou",
            template_name="Thank-You Card", profile_id="pf-amelia", profile_name="Amelia — Casual Script",
            status="Running", total=1000, generated=720, failed=3, cursor=723, created=_ago(hours=1),
            export_format="PDF", output_dir="exports/holiday-a", current_item="document_0721.pdf",
            runnable=False,
        ),
        BatchJob(
            id="bt-002", name="Member Envelopes — October", template_id="tpl-env-standard",
            template_name="Standard #10 Envelope", profile_id="pf-theo", profile_name="Theodore — Formal Print",
            status="Completed", total=480, generated=480, failed=0, cursor=480, created=_ago(days=1),
            export_format="Combined PDF", output_dir="exports/env-oct", runnable=False,
        ),
        BatchJob(
            id="bt-003", name="Spring Gala Invitations", template_id="tpl-invite",
            template_name="Event Invitation", profile_id="pf-amelia", profile_name="Amelia — Casual Script",
            status="Queued", total=250, generated=0, failed=0, created=_ago(minutes=20),
            export_format="PDF", output_dir="exports/gala", runnable=False,
        ),
        BatchJob(
            id="bt-004", name="Donor Notes — Q3", template_id="tpl-thankyou",
            template_name="Thank-You Card", profile_id="pf-theo", profile_name="Theodore — Formal Print",
            status="Failed", total=320, generated=118, failed=12, cursor=130, created=_ago(days=5),
            export_format="PDF", output_dir="exports/donor-q3", runnable=False,
            error="Generation stopped at item 130.",
        ),
    ])

    exports = [
        ("ex-001", "bt-002", "Member Envelopes — October", 0, 480, "Combined PDF", "Completed", 128.4),
        ("ex-002", "bt-001", "Holiday Thank-You — Batch A", 1, 720, "PDF", "Partial", 86.1),
        ("ex-003", "", "Welcome Letters — September", 8, 210, "PDF", "Completed", 54.0),
        ("ex-004", "", "Volunteer Notes", 12, 64, "PNG", "Completed", 22.7),
        ("ex-005", "bt-004", "Donor Notes — Q3", 20, 118, "PDF", "Failed", 19.3),
        ("ex-006", "", "Reunion Save-the-Dates", 26, 300, "Combined PDF", "Completed", 71.9),
    ]
    for eid, bid, name, days, count, fmt, status, size in exports:
        db.add(ExportRecord(
            id=eid, batch_id=bid, batch_name=name, date=_ago(days=days),
            file_count=count, format=fmt, status=status,
            output_dir=f"exports/{name.lower().replace(' ', '-')[:24]}", size_mb=size,
        ))

    activity = [
        ("ac-1", "batch", "Holiday Thank-You — Batch A", "720 of 1,000 generated", {"minutes": 4}),
        ("ac-2", "document", "Board Thank-You", "Marked ready for export", {"hours": 2}),
        ("ac-3", "template", "Standard #10 Envelope", "Recipient block edited", {"hours": 5}),
        ("ac-4", "import", "members_october.csv", "480 records imported (3 flagged)", {"hours": 7}),
        ("ac-5", "document", "Q4 Donor Notes", "Duplicated from Welcome Letters", {"days": 1}),
        ("ac-6", "error", "Donor Notes — Q3", "Batch failed at item 130", {"days": 5}),
    ]
    for aid, kind, title, detail, when in activity:
        db.add(Activity(id=aid, kind=kind, title=title, detail=detail, when=_ago(**when)))

    db.add(AppSetting(key="app", value=DEFAULT_SETTINGS))
