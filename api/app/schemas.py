"""API schemas."""
from __future__ import annotations

import re
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SampleOut(BaseModel):
    id: str
    filename: str
    added: datetime
    quality: int
    characters: int


class AnalysisOut(BaseModel):
    character_coverage: int
    sample_quality: int
    samples_analyzed: int
    avg_stroke_width: float
    slant_degrees: float
    baseline_stability: int
    spacing_consistency: int
    notes: list[str] = Field(default_factory=list)


PROFILE_ENGINES = {"graves", "handwrite", "pillow", "hw2font", "fontmaker", "gemini", "onedm", "drawn", "drawfont", "handfonted"}
PILLOW_FACES = {"caveat", "homemade", "patrick", "kalam", "sacramento", "architects"}
DRAWFONT_CAPTURES = {"minimal", "spanish", "freeform"}
_INK_COLOR = re.compile(r"#[0-9a-fA-F]{6}")
_ENGINE_ERROR = "engine must be graves, handwrite, pillow, hw2font, fontmaker, gemini, onedm, drawn, drawfont, or handfonted"


class HandfontedGlyph(BaseModel):
    id: str
    label: str = ""
    confidence: float = 0
    kept: bool = True
    sample: int = 1

    @field_validator("label")
    @classmethod
    def _label(cls, value: str) -> str:
        text = (value or "").strip()
        return text[:1]

    @field_validator("sample")
    @classmethod
    def _sample(cls, value: int) -> int:
        return max(1, min(4, int(value or 1)))


class ProfileStyle(BaseModel):
    style_id: int = 9
    bias: float = 0.75
    variation: float = 0.15
    engine: str = "graves"
    font_family: str = "caveat"
    font_path: str | None = None
    source: str = "image"
    word_size_px: float = 70
    word_spacing_px: float = 15
    char_spacing_px: float = -2.5
    ink_color: str | None = None
    web_font_path: str | None = None
    capture: str = "minimal"
    chars: str = ""
    smooth: float = 1
    weight: float = 0
    font_error: str | None = None
    thickness: int = 100
    glyphs: list[HandfontedGlyph] = Field(default_factory=list)

    @field_validator("thickness")
    @classmethod
    def _thickness(cls, value: int) -> int:
        return max(20, min(220, int(value)))

    @field_validator("engine")
    @classmethod
    def _engine(cls, value: str) -> str:
        engine = (value or "graves").strip().lower()
        if engine not in PROFILE_ENGINES:
            raise ValueError(_ENGINE_ERROR)
        return engine

    @field_validator("source")
    @classmethod
    def _source(cls, value: str) -> str:
        source = (value or "image").strip().lower()
        if source not in {"image", "draw"}:
            raise ValueError("source must be image or draw")
        return source

    @field_validator("word_size_px")
    @classmethod
    def _word_size(cls, value: float) -> float:
        return min(160.0, max(24.0, float(value)))

    @field_validator("word_spacing_px")
    @classmethod
    def _word_spacing(cls, value: float) -> float:
        return min(80.0, max(0.0, float(value)))

    @field_validator("char_spacing_px")
    @classmethod
    def _char_spacing(cls, value: float) -> float:
        return min(40.0, max(-12.0, float(value)))

    @field_validator("ink_color")
    @classmethod
    def _ink(cls, value: str | None) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        color = str(value).strip()
        if not _INK_COLOR.fullmatch(color):
            raise ValueError("ink_color must be #RRGGBB or empty")
        return color.lower()

    @field_validator("capture")
    @classmethod
    def _capture(cls, value: str) -> str:
        capture = (value or "minimal").strip().lower()
        if capture not in DRAWFONT_CAPTURES:
            raise ValueError("capture must be minimal, spanish, or freeform")
        return capture

    @field_validator("chars")
    @classmethod
    def _chars(cls, value: str) -> str:
        return (value or "").strip()[:500]

    @field_validator("smooth")
    @classmethod
    def _smooth(cls, value: float) -> float:
        return max(0.0, min(2.0, float(value)))

    @field_validator("weight")
    @classmethod
    def _weight(cls, value: float) -> float:
        return max(-2.0, min(2.0, float(value)))

    @field_validator("font_family")
    @classmethod
    def _family(cls, value: str) -> str:
        family = (value or "caveat").strip().lower()
        if family not in PILLOW_FACES:
            raise ValueError("font_family must be one of the bundled handwriting faces")
        return family


class ProfileOut(ORMModel):
    id: str
    name: str
    description: str
    status: str
    samples: list[SampleOut]
    created: datetime
    is_default: bool
    analysis: AnalysisOut | None = None
    style: ProfileStyle | None = None
    preview_text: str

    @computed_field
    @property
    def sample_count(self) -> int:
        return len(self.samples)


class ProfileCreate(BaseModel):
    name: str
    description: str = ""
    preview_text: str = "The quick brown fox"
    engine: str = "handwrite"
    font_family: str = "caveat"

    @field_validator("engine")
    @classmethod
    def _engine(cls, value: str) -> str:
        engine = (value or "handwrite").strip().lower()
        if engine not in PROFILE_ENGINES:
            raise ValueError(_ENGINE_ERROR)
        return engine

    @field_validator("font_family")
    @classmethod
    def _family(cls, value: str) -> str:
        family = (value or "caveat").strip().lower()
        if family not in PILLOW_FACES:
            raise ValueError("font_family must be one of the bundled handwriting faces")
        return family


class ProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    preview_text: str | None = None
    status: str | None = None
    style: ProfileStyle | None = None


class GlyphMetricsOut(BaseModel):
    pad_width: int
    pad_height: int
    baseline_y: float
    crop_left: int
    crop_top: int
    ink_width: int
    ink_height: int


class GlyphSlotOut(BaseModel):
    key: str
    char: str
    group: str
    set1: GlyphMetricsOut | None = None
    set2: GlyphMetricsOut | None = None


class GlyphInventoryOut(BaseModel):
    total: int
    set1_count: int
    set2_count: int
    ready: bool
    pad_width: int
    pad_height: int
    baseline_y: int
    slots: list[GlyphSlotOut]


class GlyphPreviewIn(BaseModel):
    text: str = ""


class HandfontedGlyphUpdate(BaseModel):
    glyphs: list[HandfontedGlyph]
    thickness: int | None = None

    @field_validator("thickness")
    @classmethod
    def _thickness(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return max(20, min(220, int(value)))


class HandfontedPreview(BaseModel):
    text: str = "The quick brown fox"


class ElementOut(BaseModel):
    id: str
    type: str
    name: str
    x: float
    y: float
    width: float
    height: float
    align: str = "left"
    font_size: int = 14
    content: str = ""
    visible: bool = True


class TemplateOut(ORMModel):
    id: str
    name: str
    kind: str
    width_in: float
    height_in: float
    status: str
    modified: datetime
    elements: list[ElementOut]
    margin_in: float
    description: str


class TemplateCreate(BaseModel):
    name: str
    kind: str = "4×6 Card"
    description: str = ""


class TemplateUpdate(BaseModel):
    name: str | None = None
    status: str | None = None
    description: str | None = None
    margin_in: float | None = None
    elements: list[ElementOut] | None = None


class DocumentOut(ORMModel):
    id: str
    name: str
    template_id: str
    template_name: str
    profile_id: str
    profile_name: str
    status: str
    export_format: str
    created: datetime
    modified: datetime
    pages: int
    fields: dict[str, str] = Field(default_factory=dict)


class DocumentDetail(DocumentOut):
    template: TemplateOut | None = None
    profile: ProfileOut | None = None


class DocumentCreate(BaseModel):
    name: str | None = None
    template_id: str
    profile_id: str | None = None


class DocumentUpdate(BaseModel):
    name: str | None = None
    profile_id: str | None = None
    status: str | None = None
    export_format: str | None = None
    fields: dict[str, str] | None = None


class BulkIds(BaseModel):
    ids: list[str]


class ImportIssue(BaseModel):
    line: int
    reason: str


class ImportOut(BaseModel):
    id: str
    filename: str
    records_detected: int
    valid_records: int
    invalid_records: int
    columns: list[str]
    rows: list[dict[str, str]]
    issues: list[ImportIssue] = Field(default_factory=list)


class BatchCreate(BaseModel):
    name: str
    template_id: str
    profile_id: str
    import_id: str
    export_format: str = "PDF"
    naming: str = "document_{index}"
    individual: bool = True
    combined: bool = False


class BatchOut(ORMModel):
    id: str
    name: str
    template_id: str
    template_name: str
    profile_id: str
    profile_name: str
    status: str
    total: int
    generated: int
    failed: int
    created: datetime
    export_format: str
    output_dir: str
    current_item: str
    naming: str
    individual: bool
    combined: bool
    runnable: bool = False
    error: str = ""

    @computed_field
    @property
    def progress(self) -> float:
        if self.total == 0:
            return 0.0
        return round((self.generated + self.failed) / self.total, 4)


def export_filename(batch_name: str, artifact_key: str) -> str:
    stored = artifact_key.rsplit("/", 1)[-1] if artifact_key else ""
    ext = stored.rsplit(".", 1)[-1] if "." in stored else ""
    stem = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ._-]+", " ", batch_name)).strip(" .-") or "export"
    return f"{stem}.{ext}" if ext else stem


class ExportOut(ORMModel):
    id: str
    batch_id: str
    batch_name: str
    date: datetime
    file_count: int
    format: str
    status: str
    output_dir: str
    size_mb: float
    artifact_key: str = Field(default="", exclude=True)

    @computed_field
    @property
    def has_file(self) -> bool:
        return bool(self.artifact_key)

    @computed_field
    @property
    def filename(self) -> str:
        if not self.artifact_key:
            return ""
        return export_filename(self.batch_name, self.artifact_key)


class ActivityOut(ORMModel):
    id: str
    kind: str
    title: str
    detail: str
    when: datetime


class DashboardOut(BaseModel):
    counts: dict[str, int]
    activity: list[ActivityOut]
    system: dict[str, str]


class SettingsOut(BaseModel):
    workspace: str
    output_dir: str
    default_template_id: str
    default_profile_id: str
    theme: str
    ui_scale: int
    reduce_motion: bool
    export_format: str
    resolution: str
    pause_on_error: bool
    notify_on_complete: bool
    printer: str
    page_scaling: str
    print_margins: str
    onboarding_complete: bool
    cache_bytes: int = 0


class SettingsUpdate(BaseModel):
    workspace: str | None = None
    output_dir: str | None = None
    default_template_id: str | None = None
    default_profile_id: str | None = None
    theme: str | None = None
    ui_scale: int | None = None
    reduce_motion: bool | None = None
    export_format: str | None = None
    resolution: str | None = None
    pause_on_error: bool | None = None
    notify_on_complete: bool | None = None
    printer: str | None = None
    page_scaling: str | None = None
    print_margins: str | None = None
    onboarding_complete: bool | None = None
