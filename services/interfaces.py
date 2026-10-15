"""Service interfaces (Protocols).

The UI depends on these abstractions, never on concrete implementations.  Today
they are backed by ``mock_services`` returning in-memory dummy data; later the
same interfaces can be fulfilled by services that talk to the real Python
rendering/processing engine, SQLite, the filesystem, etc. — without touching the
UI layer.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from models.domain import (
    ActivityItem,
    BatchJob,
    Document,
    ExportRecord,
    HandwritingProfile,
    ImportSummary,
    Template,
)


@runtime_checkable
class HandwritingService(Protocol):
    def list_profiles(self) -> list[HandwritingProfile]: ...
    def get_profile(self, profile_id: str) -> HandwritingProfile | None: ...
    def delete_profile(self, profile_id: str) -> None: ...
    def set_default(self, profile_id: str) -> None: ...
    def render_preview(self, profile_id: str, text: str, variation: int) -> str: ...


@runtime_checkable
class TemplateService(Protocol):
    def list_templates(self) -> list[Template]: ...
    def get_template(self, template_id: str) -> Template | None: ...
    def delete_template(self, template_id: str) -> None: ...
    def duplicate_template(self, template_id: str) -> Template | None: ...


@runtime_checkable
class DocumentService(Protocol):
    def list_documents(self) -> list[Document]: ...
    def get_document(self, document_id: str) -> Document | None: ...
    def delete_document(self, document_id: str) -> None: ...
    def duplicate_document(self, document_id: str) -> Document | None: ...


@runtime_checkable
class BatchService(Protocol):
    def list_batches(self) -> list[BatchJob]: ...
    def get_batch(self, batch_id: str) -> BatchJob | None: ...


@runtime_checkable
class ExportService(Protocol):
    def list_exports(self) -> list[ExportRecord]: ...
    def delete_export(self, export_id: str) -> None: ...


@runtime_checkable
class ImportService(Protocol):
    def preview(self, path: str) -> ImportSummary: ...


@runtime_checkable
class DashboardService(Protocol):
    def activity(self) -> list[ActivityItem]: ...
    def counts(self) -> dict[str, int]: ...
