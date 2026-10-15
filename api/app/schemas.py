"""API schemas."""
from __future__ import annotations

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


PROFILE_ENGINES = {"graves", "handwrite", "pillow", "hw2font", "fontmaker", "gemini", "onedm"}
PILLOW_FACES = {"caveat", "homemade", "patrick", "kalam", "sacramento", "architects"}


class ProfileStyle(BaseModel):
    style_id: int = 9
    bias: float = 0.75
    variation: float = 0.15
    engine: str = "graves"
    font_family: str = "caveat"
    font_path: str | None = None

    @field_validator("engine")
    @classmethod
    def _engine(cls, value: str) -> str:
        engine = (value or "graves").strip().lower()
        if engine not in PROFILE_ENGINES:
            raise ValueError("engine must be graves, handwrite, pillow, hw2font, fontmaker, gemini, or onedm")
        return engine

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
            raise ValueError("engine must be graves, handwrite, pillow, hw2font, fontmaker, gemini, or onedm")
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
