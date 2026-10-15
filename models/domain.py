"""Domain models for HandScript Studio.

Plain ``dataclasses`` describing the entities the UI works with.  They are
intentionally free of any Qt or persistence concerns so they can be shared by
mock services today and real services later, and are trivial to construct in
tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# --------------------------------------------------------------------------- #
#   Enums                                                                     #
# --------------------------------------------------------------------------- #
class DocumentStatus(str, Enum):
    DRAFT = "Draft"
    READY = "Ready"
    GENERATING = "Generating"
    COMPLETED = "Completed"
    FAILED = "Failed"


class ProfileStatus(str, Enum):
    READY = "Ready"
    PROCESSING = "Processing"
    NEEDS_REVIEW = "Needs Review"
    ERROR = "Error"


class TemplateKind(str, Enum):
    CARD_4X6 = "4×6 Card"
    ENVELOPE_10 = "#10 Envelope"


class TemplateStatus(str, Enum):
    PUBLISHED = "Published"
    DRAFT = "Draft"


class ExportFormat(str, Enum):
    PDF = "PDF"
    PNG = "PNG"
    PDF_COMBINED = "Combined PDF"


class BatchStatus(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


class ElementType(str, Enum):
    TEXT = "Text"
    ADDRESS = "Address"
    DATA_FIELD = "Data Field"
    DIVIDER = "Divider"
    IMAGE = "Image"


# --------------------------------------------------------------------------- #
#   Entities                                                                  #
# --------------------------------------------------------------------------- #
@dataclass
class HandwritingSample:
    id: str
    filename: str
    added: datetime
    quality: int          # 0-100
    characters: int       # distinct glyphs detected


@dataclass
class AnalysisReport:
    character_coverage: int      # %
    sample_quality: int          # %
    samples_analyzed: int
    avg_stroke_width: float      # mm
    slant_degrees: float
    baseline_stability: int      # %
    spacing_consistency: int     # %
    notes: list[str] = field(default_factory=list)


@dataclass
class HandwritingProfile:
    id: str
    name: str
    description: str
    status: ProfileStatus
    samples: list[HandwritingSample] = field(default_factory=list)
    created: datetime = field(default_factory=datetime.now)
    is_default: bool = False
    analysis: AnalysisReport | None = None
    preview_text: str = "The quick brown fox"

    @property
    def sample_count(self) -> int:
        return len(self.samples)


@dataclass
class TemplateElement:
    id: str
    type: ElementType
    name: str
    x: float          # inches
    y: float
    width: float
    height: float
    align: str = "left"
    font_size: int = 14
    content: str = ""
    visible: bool = True


@dataclass
class Template:
    id: str
    name: str
    kind: TemplateKind
    width_in: float
    height_in: float
    status: TemplateStatus
    modified: datetime
    elements: list[TemplateElement] = field(default_factory=list)
    margin_in: float = 0.2
    description: str = ""

    @property
    def dimensions_label(self) -> str:
        return f'{self.width_in:g} × {self.height_in:g} in'

    @property
    def aspect(self) -> float:
        return self.width_in / self.height_in


@dataclass
class Document:
    id: str
    name: str
    template: str
    profile: str
    status: DocumentStatus
    export_format: ExportFormat
    created: datetime
    modified: datetime
    pages: int = 1
    thumbnail_text: str = ""


@dataclass
class ImportSummary:
    filename: str
    records_detected: int
    valid_records: int
    invalid_records: int
    columns: list[str]
    rows: list[dict[str, str]]


@dataclass
class BatchJob:
    id: str
    name: str
    template: str
    profile: str
    status: BatchStatus
    total: int
    generated: int
    failed: int
    created: datetime
    export_format: ExportFormat
    output_dir: str
    current_item: str = ""

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.generated - self.failed)

    @property
    def progress(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.generated + self.failed) / self.total


@dataclass
class ExportRecord:
    id: str
    batch_name: str
    date: datetime
    file_count: int
    format: ExportFormat
    status: str          # "Completed" / "Partial" / "Failed"
    output_dir: str
    size_mb: float


@dataclass
class ActivityItem:
    id: str
    kind: str            # "document" | "template" | "import" | "batch" | "error"
    title: str
    detail: str
    when: datetime
