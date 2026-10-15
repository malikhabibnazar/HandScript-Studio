"""A tiny service locator.

Pages receive a :class:`Services` bundle rather than importing concrete service
classes directly.  Swapping ``Mock*`` for real implementations later is a
one-line change here — the UI is unaffected.
"""
from __future__ import annotations

from dataclasses import dataclass

from services.mock_services import (
    MockBatchService,
    MockDashboardService,
    MockDocumentService,
    MockExportService,
    MockHandwritingService,
    MockImportService,
    MockTemplateService,
)


@dataclass
class Services:
    handwriting: MockHandwritingService
    templates: MockTemplateService
    documents: MockDocumentService
    batches: MockBatchService
    exports: MockExportService
    imports: MockImportService
    dashboard: MockDashboardService


def build_services() -> Services:
    hw = MockHandwritingService()
    tpl = MockTemplateService()
    doc = MockDocumentService()
    batch = MockBatchService()
    return Services(
        handwriting=hw,
        templates=tpl,
        documents=doc,
        batches=batch,
        exports=MockExportService(),
        imports=MockImportService(),
        dashboard=MockDashboardService(hw, tpl, doc, batch),
    )
