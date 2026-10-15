"""In-memory mock service implementations.

These satisfy the Protocols in :mod:`services.interfaces` using the dummy data
in :mod:`data.mock_data`.  State lives in memory for the session so the UI feels
alive (deleting an item removes it from the list, setting a default updates the
others, etc.) without any database or network.
"""
from __future__ import annotations

from data import mock_data
from models.domain import (
    ActivityItem,
    BatchJob,
    Document,
    ExportRecord,
    HandwritingProfile,
    ImportSummary,
    Template,
)


class MockHandwritingService:
    def __init__(self) -> None:
        self._profiles: list[HandwritingProfile] = mock_data.make_profiles()

    def list_profiles(self) -> list[HandwritingProfile]:
        return list(self._profiles)

    def get_profile(self, profile_id: str) -> HandwritingProfile | None:
        return next((p for p in self._profiles if p.id == profile_id), None)

    def delete_profile(self, profile_id: str) -> None:
        self._profiles = [p for p in self._profiles if p.id != profile_id]

    def set_default(self, profile_id: str) -> None:
        for p in self._profiles:
            p.is_default = p.id == profile_id

    def render_preview(self, profile_id: str, text: str, variation: int) -> str:
        # The real engine will return a rendered image path; mock returns the text.
        return text


class MockTemplateService:
    def __init__(self) -> None:
        self._templates: list[Template] = mock_data.make_templates()

    def list_templates(self) -> list[Template]:
        return list(self._templates)

    def get_template(self, template_id: str) -> Template | None:
        return next((t for t in self._templates if t.id == template_id), None)

    def delete_template(self, template_id: str) -> None:
        self._templates = [t for t in self._templates if t.id != template_id]

    def duplicate_template(self, template_id: str) -> Template | None:
        src = self.get_template(template_id)
        if not src:
            return None
        import copy

        dup = copy.deepcopy(src)
        dup.id = f"{src.id}-copy"
        dup.name = f"{src.name} (Copy)"
        self._templates.append(dup)
        return dup


class MockDocumentService:
    def __init__(self) -> None:
        self._documents: list[Document] = mock_data.make_documents()

    def list_documents(self) -> list[Document]:
        return list(self._documents)

    def get_document(self, document_id: str) -> Document | None:
        return next((d for d in self._documents if d.id == document_id), None)

    def delete_document(self, document_id: str) -> None:
        self._documents = [d for d in self._documents if d.id != document_id]

    def duplicate_document(self, document_id: str) -> Document | None:
        src = self.get_document(document_id)
        if not src:
            return None
        import copy

        dup = copy.deepcopy(src)
        dup.id = f"{src.id}-copy"
        dup.name = f"{src.name} (Copy)"
        self._documents.insert(0, dup)
        return dup


class MockBatchService:
    def __init__(self) -> None:
        self._batches: list[BatchJob] = mock_data.make_batches()

    def list_batches(self) -> list[BatchJob]:
        return list(self._batches)

    def get_batch(self, batch_id: str) -> BatchJob | None:
        return next((b for b in self._batches if b.id == batch_id), None)


class MockExportService:
    def __init__(self) -> None:
        self._exports: list[ExportRecord] = mock_data.make_exports()

    def list_exports(self) -> list[ExportRecord]:
        return list(self._exports)

    def delete_export(self, export_id: str) -> None:
        self._exports = [e for e in self._exports if e.id != export_id]


class MockImportService:
    def preview(self, path: str) -> ImportSummary:
        summary = mock_data.make_import_summary()
        if path:
            name = path.replace("\\", "/").split("/")[-1]
            summary.filename = name or summary.filename
        return summary


class MockDashboardService:
    def __init__(self, hw: MockHandwritingService, tpl: MockTemplateService,
                 doc: MockDocumentService, batch: MockBatchService) -> None:
        self._hw, self._tpl, self._doc, self._batch = hw, tpl, doc, batch

    def activity(self) -> list[ActivityItem]:
        return mock_data.make_activity()

    def counts(self) -> dict[str, int]:
        docs = self._doc.list_documents()
        generated = sum(1 for d in docs if d.status.value == "Completed")
        return {
            "profiles": len(self._hw.list_profiles()),
            "templates": len(self._tpl.list_templates()),
            "documents_generated": max(generated * 214, 1836),  # realistic cumulative figure
            "recent_batches": len(self._batch.list_batches()),
        }
