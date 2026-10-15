"""Realistic mock data used by the mock services.

All timestamps are relative to "now" so the dashboard and lists always look
freshly used.  This module is pure data — no Qt, no I/O.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from models.domain import (
    ActivityItem,
    AnalysisReport,
    BatchJob,
    BatchStatus,
    Document,
    DocumentStatus,
    ElementType,
    ExportFormat,
    ExportRecord,
    HandwritingProfile,
    HandwritingSample,
    ImportSummary,
    ProfileStatus,
    Template,
    TemplateElement,
    TemplateKind,
    TemplateStatus,
)

_NOW = datetime.now()


def _ago(days: float = 0, hours: float = 0, minutes: float = 0) -> datetime:
    return _NOW - timedelta(days=days, hours=hours, minutes=minutes)


# --------------------------------------------------------------------------- #
#   Handwriting profiles                                                      #
# --------------------------------------------------------------------------- #
def _samples(prefix: str, n: int, base_quality: int) -> list[HandwritingSample]:
    out: list[HandwritingSample] = []
    for i in range(n):
        out.append(
            HandwritingSample(
                id=f"{prefix}-s{i + 1}",
                filename=f"sample_{i + 1:02d}.png",
                added=_ago(days=12 - i * 0.6),
                quality=min(99, base_quality + (i % 5) * 2),
                characters=48 + (i % 7) * 3,
            )
        )
    return out


def make_profiles() -> list[HandwritingProfile]:
    return [
        HandwritingProfile(
            id="pf-amelia",
            name="Amelia — Casual Script",
            description="Relaxed everyday cursive with light slant. Great for personal notes and cards.",
            status=ProfileStatus.READY,
            samples=_samples("pf-amelia", 12, 88),
            created=_ago(days=31),
            is_default=True,
            preview_text="Thank you so much",
            analysis=AnalysisReport(
                character_coverage=94,
                sample_quality=91,
                samples_analyzed=12,
                avg_stroke_width=0.42,
                slant_degrees=6.5,
                baseline_stability=88,
                spacing_consistency=90,
                notes=[
                    "Strong lowercase coverage across all samples.",
                    "Uppercase Q and Z under-represented — add 1–2 samples.",
                ],
            ),
        ),
        HandwritingProfile(
            id="pf-theo",
            name="Theodore — Formal Print",
            description="Clean upright print suited to envelopes and formal correspondence.",
            status=ProfileStatus.READY,
            samples=_samples("pf-theo", 10, 90),
            created=_ago(days=22),
            preview_text="Dear Mr. Harrington",
            analysis=AnalysisReport(
                character_coverage=97,
                sample_quality=93,
                samples_analyzed=10,
                avg_stroke_width=0.38,
                slant_degrees=1.2,
                baseline_stability=95,
                spacing_consistency=92,
                notes=["Excellent baseline consistency.", "Numerals fully covered."],
            ),
        ),
        HandwritingProfile(
            id="pf-mira",
            name="Mira — Quick Note",
            description="Fast, loose handwriting captured from quick notes.",
            status=ProfileStatus.PROCESSING,
            samples=_samples("pf-mira", 7, 72),
            created=_ago(days=3),
            preview_text="See you soon!",
            analysis=None,
        ),
        HandwritingProfile(
            id="pf-jonas",
            name="Jonas — Draft",
            description="Early capture — needs a few more clean samples before use.",
            status=ProfileStatus.NEEDS_REVIEW,
            samples=_samples("pf-jonas", 4, 58),
            created=_ago(days=1, hours=5),
            preview_text="Sample text",
            analysis=AnalysisReport(
                character_coverage=61,
                sample_quality=64,
                samples_analyzed=4,
                avg_stroke_width=0.55,
                slant_degrees=12.0,
                baseline_stability=66,
                spacing_consistency=59,
                notes=[
                    "Coverage below 70% — several lowercase glyphs missing.",
                    "Sample 3 is low contrast; consider replacing.",
                ],
            ),
        ),
        HandwritingProfile(
            id="pf-coral",
            name="Coral — Decorative",
            description="Looping decorative hand. Import failed during the last analysis run.",
            status=ProfileStatus.ERROR,
            samples=_samples("pf-coral", 6, 70),
            created=_ago(days=9),
            preview_text="Congratulations",
            analysis=None,
        ),
    ]


# --------------------------------------------------------------------------- #
#   Templates                                                                 #
# --------------------------------------------------------------------------- #
def _card_elements() -> list[TemplateElement]:
    return [
        TemplateElement("el-greet", ElementType.TEXT, "Greeting", 0.4, 0.5, 3.2, 0.6,
                        align="left", font_size=22, content="Dear {first_name},"),
        TemplateElement("el-body", ElementType.TEXT, "Body", 0.4, 1.4, 5.2, 2.6,
                        align="left", font_size=16,
                        content="Thank you for being part of our community this year. "
                                "We wanted to send a little note of appreciation."),
        TemplateElement("el-sign", ElementType.TEXT, "Signature", 0.4, 4.6, 3.0, 0.6,
                        align="left", font_size=18, content="Warmly, {sender}"),
        TemplateElement("el-div", ElementType.DIVIDER, "Divider", 0.4, 4.4, 5.2, 0.02),
    ]


def _envelope_elements() -> list[TemplateElement]:
    return [
        TemplateElement("el-return", ElementType.ADDRESS, "Return Address", 0.3, 0.3, 3.0, 1.0,
                        align="left", font_size=11,
                        content="{sender}\n{return_street}\n{return_city}"),
        TemplateElement("el-recipient", ElementType.ADDRESS, "Recipient", 3.6, 1.9, 4.6, 1.3,
                        align="left", font_size=14,
                        content="{first_name} {last_name}\n{street}\n{city}, {state} {zip}"),
    ]


def make_templates() -> list[Template]:
    return [
        Template(
            id="tpl-thankyou", name="Thank-You Card", kind=TemplateKind.CARD_4X6,
            width_in=6.0, height_in=4.0, status=TemplateStatus.PUBLISHED,
            modified=_ago(days=2, hours=3), elements=_card_elements(),
            description="Personal thank-you card with greeting, body and signature blocks.",
        ),
        Template(
            id="tpl-invite", name="Event Invitation", kind=TemplateKind.CARD_4X6,
            width_in=6.0, height_in=4.0, status=TemplateStatus.PUBLISHED,
            modified=_ago(days=6), elements=_card_elements(),
            description="4×6 invitation layout with data placeholders.",
        ),
        Template(
            id="tpl-env-standard", name="Standard #10 Envelope", kind=TemplateKind.ENVELOPE_10,
            width_in=9.5, height_in=4.125, status=TemplateStatus.PUBLISHED,
            modified=_ago(days=1, hours=1), elements=_envelope_elements(),
            description="Classic #10 business envelope with return and recipient address.",
        ),
        Template(
            id="tpl-env-formal", name="Formal #10 Envelope", kind=TemplateKind.ENVELOPE_10,
            width_in=9.5, height_in=4.125, status=TemplateStatus.DRAFT,
            modified=_ago(days=4), elements=_envelope_elements(),
            description="Centered formal envelope variant. Still a draft.",
        ),
    ]


# --------------------------------------------------------------------------- #
#   Documents                                                                 #
# --------------------------------------------------------------------------- #
def make_documents() -> list[Document]:
    data = [
        ("Holiday Thank-You — Batch A", "Thank-You Card", "Amelia — Casual Script",
         DocumentStatus.COMPLETED, ExportFormat.PDF, 2, 1),
        ("Q4 Donor Notes", "Thank-You Card", "Theodore — Formal Print",
         DocumentStatus.READY, ExportFormat.PDF_COMBINED, 1, 3),
        ("Spring Gala Invitations", "Event Invitation", "Amelia — Casual Script",
         DocumentStatus.GENERATING, ExportFormat.PDF, 1, 0),
        ("Welcome Letters", "Thank-You Card", "Theodore — Formal Print",
         DocumentStatus.DRAFT, ExportFormat.PNG, 1, 5),
        ("Envelope Run — Members", "Standard #10 Envelope", "Theodore — Formal Print",
         DocumentStatus.COMPLETED, ExportFormat.PDF, 1, 8),
        ("Partner Appreciation", "Thank-You Card", "Amelia — Casual Script",
         DocumentStatus.FAILED, ExportFormat.PDF, 1, 2),
        ("Reunion Save-the-Dates", "Event Invitation", "Mira — Quick Note",
         DocumentStatus.DRAFT, ExportFormat.PDF, 1, 6),
        ("Board Thank-You", "Thank-You Card", "Theodore — Formal Print",
         DocumentStatus.READY, ExportFormat.PDF, 1, 1),
        ("Formal Envelopes — VIP", "Formal #10 Envelope", "Theodore — Formal Print",
         DocumentStatus.READY, ExportFormat.PDF_COMBINED, 1, 2),
        ("Volunteer Notes", "Thank-You Card", "Amelia — Casual Script",
         DocumentStatus.COMPLETED, ExportFormat.PNG, 1, 10),
    ]
    docs: list[Document] = []
    for i, (name, tpl, prof, status, fmt, pages, days) in enumerate(data):
        docs.append(
            Document(
                id=f"doc-{i + 1:03d}", name=name, template=tpl, profile=prof,
                status=status, export_format=fmt, created=_ago(days=days + 2),
                modified=_ago(days=days), pages=pages, thumbnail_text=name,
            )
        )
    return docs


# --------------------------------------------------------------------------- #
#   Batch jobs + exports                                                      #
# --------------------------------------------------------------------------- #
def make_batches() -> list[BatchJob]:
    return [
        BatchJob(
            id="bt-001", name="Holiday Thank-You — Batch A", template="Thank-You Card",
            profile="Amelia — Casual Script", status=BatchStatus.RUNNING,
            total=1000, generated=720, failed=3, created=_ago(hours=1),
            export_format=ExportFormat.PDF, output_dir="~/HandScript/Exports/holiday-a",
            current_item="document_0721.pdf",
        ),
        BatchJob(
            id="bt-002", name="Member Envelopes — October", template="Standard #10 Envelope",
            profile="Theodore — Formal Print", status=BatchStatus.COMPLETED,
            total=480, generated=480, failed=0, created=_ago(days=1, hours=2),
            export_format=ExportFormat.PDF_COMBINED, output_dir="~/HandScript/Exports/env-oct",
        ),
        BatchJob(
            id="bt-003", name="Spring Gala Invitations", template="Event Invitation",
            profile="Amelia — Casual Script", status=BatchStatus.QUEUED,
            total=250, generated=0, failed=0, created=_ago(minutes=20),
            export_format=ExportFormat.PDF, output_dir="~/HandScript/Exports/gala",
        ),
        BatchJob(
            id="bt-004", name="Donor Notes — Q3", template="Thank-You Card",
            profile="Theodore — Formal Print", status=BatchStatus.FAILED,
            total=320, generated=118, failed=12, created=_ago(days=5),
            export_format=ExportFormat.PDF, output_dir="~/HandScript/Exports/donor-q3",
        ),
    ]


def make_exports() -> list[ExportRecord]:
    rows = [
        ("Member Envelopes — October", 0, 480, ExportFormat.PDF_COMBINED, "Completed", 128.4),
        ("Holiday Thank-You — Batch A", 1, 720, ExportFormat.PDF, "Partial", 86.1),
        ("Welcome Letters — September", 8, 210, ExportFormat.PDF, "Completed", 54.0),
        ("Volunteer Notes", 12, 64, ExportFormat.PNG, "Completed", 22.7),
        ("Donor Notes — Q3", 20, 118, ExportFormat.PDF, "Failed", 19.3),
        ("Reunion Save-the-Dates", 26, 300, ExportFormat.PDF_COMBINED, "Completed", 71.9),
    ]
    out: list[ExportRecord] = []
    for i, (name, days, count, fmt, status, size) in enumerate(rows):
        out.append(
            ExportRecord(
                id=f"ex-{i + 1:03d}", batch_name=name, date=_ago(days=days + 0.3),
                file_count=count, format=fmt, status=status,
                output_dir=f"~/HandScript/Exports/{name.lower().replace(' ', '-')[:18]}",
                size_mb=size,
            )
        )
    return out


# --------------------------------------------------------------------------- #
#   Dashboard activity                                                        #
# --------------------------------------------------------------------------- #
def make_activity() -> list[ActivityItem]:
    return [
        ActivityItem("ac-1", "batch", "Holiday Thank-You — Batch A", "720 of 1,000 generated", _ago(minutes=4)),
        ActivityItem("ac-2", "document", "Board Thank-You", "Marked ready for export", _ago(hours=2)),
        ActivityItem("ac-3", "template", "Standard #10 Envelope", "Recipient block edited", _ago(hours=5)),
        ActivityItem("ac-4", "import", "members_october.csv", "480 records imported (3 flagged)", _ago(hours=7)),
        ActivityItem("ac-5", "document", "Q4 Donor Notes", "Duplicated from Welcome Letters", _ago(days=1)),
        ActivityItem("ac-6", "error", "Donor Notes — Q3", "Batch failed at item 130", _ago(days=5)),
    ]


# --------------------------------------------------------------------------- #
#   Import preview (batch step 3)                                             #
# --------------------------------------------------------------------------- #
def make_import_summary() -> ImportSummary:
    columns = ["first_name", "last_name", "street", "city", "state", "zip"]
    sample_rows = [
        {"first_name": "Amelia", "last_name": "Hart", "street": "42 Willow Lane",
         "city": "Portland", "state": "OR", "zip": "97201"},
        {"first_name": "Theodore", "last_name": "Nguyen", "street": "1180 Maple Ave",
         "city": "Austin", "state": "TX", "zip": "78701"},
        {"first_name": "Mira", "last_name": "Patel", "street": "7 Birchwood Ct",
         "city": "Denver", "state": "CO", "zip": "80203"},
        {"first_name": "Jonas", "last_name": "Keller", "street": "920 Oak Street",
         "city": "Seattle", "state": "WA", "zip": "98101"},
        {"first_name": "Coral", "last_name": "", "street": "55 Harbor Rd",
         "city": "Boston", "state": "MA", "zip": ""},
        {"first_name": "Elena", "last_name": "Rossi", "street": "308 Pine Blvd",
         "city": "Chicago", "state": "IL", "zip": "60601"},
        {"first_name": "Marcus", "last_name": "Webb", "street": "14 Cedar Way",
         "city": "Miami", "state": "FL", "zip": "33101"},
    ]
    return ImportSummary(
        filename="members_october.csv",
        records_detected=483,
        valid_records=480,
        invalid_records=3,
        columns=columns,
        rows=sample_rows,
    )
