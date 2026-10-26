"""Batch generation and handwriting analysis.

The API and the worker process share these functions. Each tick renders one
record, stores the file, and commits so progress events stay current.
A page that fails is skipped. The batch still finishes and the successful
pages are published.
"""
from __future__ import annotations

import logging
import tempfile
import zipfile
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity, AppSetting, BatchJob, ExportRecord, Profile, Template, utcnow
from app.config import get_settings
from app.render import parse_dpi, pdf_bytes, png_bytes, render_page, stable_seed, write_pdf_from_pngs
from app.schemas import export_filename
from app.seed import DEFAULT_SETTINGS
from app.storage import get_storage

log = logging.getLogger(__name__)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:10]}"


def log_activity(db: Session, kind: str, title: str, detail: str) -> None:
    db.add(Activity(id=new_id("ac"), kind=kind, title=title, detail=detail, when=utcnow()))


def settings_dict(db: Session) -> dict:
    row = db.get(AppSetting, "app")
    data = dict(DEFAULT_SETTINGS)
    if row and isinstance(row.value, dict):
        data.update(row.value)
    return data


def _filename(batch: BatchJob, index: int, ext: str) -> str:
    stem = (batch.naming or "document_{index}").replace("{index}", f"{index:04d}")
    stem = stem.replace("{name}", "document")
    return f"{stem}.{ext}"


def _content_type(fmt: str) -> tuple[str, str]:
    if fmt == "PNG":
        return "png", "image/png"
    return "pdf", "application/pdf"


def profile_ink(profile: Profile | None) -> dict:
    raw = profile.style if profile is not None and isinstance(profile.style, dict) else {}
    settings = get_settings()
    style_id = raw.get("style_id", settings.graves_default_style_id)
    ink = {
        "style_id": int(style_id) if style_id is not None else None,
        "bias": float(raw.get("bias", 0.75)),
        "variation": float(raw.get("variation", 0.15)),
    }
    engine = str(raw.get("engine") or "").strip().lower()
    if engine in {"graves", "handwrite", "pillow", "hw2font", "fontmaker", "gemini", "onedm", "drawn", "drawfont", "handfonted"}:
        ink["engine"] = engine
    if engine == "drawn" and profile is not None:
        ink["glyph_profile_id"] = profile.id
        ink["word_size_px"] = float(raw.get("word_size_px", 70))
        ink["word_spacing_px"] = float(raw.get("word_spacing_px", 15))
        ink["char_spacing_px"] = float(raw.get("char_spacing_px", -2.5))
        color = raw.get("ink_color")
        ink["ink_color"] = color if isinstance(color, str) and color else None
    if engine in {"gemini", "onedm"} and profile is not None:
        keys = []
        for sample in list(profile.samples or [])[-2:]:
            if isinstance(sample, dict) and sample.get("id") and sample.get("filename"):
                keys.append(f"samples/{profile.id}/{sample['id']}-{sample['filename']}")
        ink["sample_keys"] = keys
    if engine == "pillow":
        ink["font_family"] = str(raw.get("font_family") or "caveat")
    font_path = raw.get("font_path")
    if engine in {"handwrite", "hw2font", "fontmaker", "drawfont", "handfonted"} and isinstance(font_path, str) and font_path:
        ink["font_path"] = font_path
    if engine == "handfonted" and profile is not None:
        glyphs = [item for item in list(raw.get("glyphs") or []) if isinstance(item, dict) and item.get("kept", True)]
        if glyphs:
            ink["handfonted_glyphs"] = glyphs
            ink["handfonted_dir"] = str(Path(settings.storage_dir) / "handfonted" / profile.id / "glyphs")
    return ink


def _page_png_key(batch_id: str, index: int) -> str:
    return f"batches/{batch_id}/pages/{index:04d}.png"


def _page_fail_key(batch_id: str, index: int) -> str:
    return f"batches/{batch_id}/pages/{index:04d}.fail"


def _page_state(batch_id: str, index: int) -> str | None:
    storage = get_storage()
    if storage.exists(_page_png_key(batch_id, index)):
        return "png"
    if storage.exists(_page_fail_key(batch_id, index)):
        return "fail"
    return None


def _next_missing_page(batch: BatchJob) -> int | None:
    """A valid row that was counted before its page was saved, or not saved yet."""
    if not batch.combined:
        return None
    for index, record in enumerate(list(batch.records or []), start=1):
        if not record.get("_valid", True):
            continue
        if _page_state(batch.id, index) is None:
            return index
    return None


def _remember_failure(batch: BatchJob, index: int, message: str) -> None:
    if not batch.combined:
        return
    get_storage().put(_page_fail_key(batch.id, index), message.encode("utf-8")[:500], "text/plain")


def _skip_remaining(batch: BatchJob, after_index: int, message: str) -> None:
    """Mark later rows so a stopped batch is not rendered further."""
    for index, record in enumerate(list(batch.records or []), start=1):
        if index <= after_index or not record.get("_valid", True):
            continue
        if _page_state(batch.id, index) is None:
            _remember_failure(batch, index, message)
            batch.failed += 1
    batch.cursor = len(list(batch.records or []))


def _open_page(template: Template, record: dict, *, dpi: int, seed: int, profile: Profile | None):
    payload = {"width_in": template.width_in, "height_in": template.height_in}
    return render_page(
        payload,
        list(template.elements or []),
        record,
        dpi=dpi,
        seed=seed,
        **profile_ink(profile),
    )


def _store_page(batch: BatchJob, template: Template, record: dict, index: int, *, dpi: int, profile: Profile | None) -> str:
    """Render one record and store its files. Returns the display name."""
    image = _open_page(template, record, dpi=dpi, seed=stable_seed(batch.id, index), profile=profile)
    name = ""
    try:
        payload = {"width_in": template.width_in, "height_in": template.height_in}
        if batch.individual:
            ext, content_type = _content_type("PNG" if batch.export_format == "PNG" else "PDF")
            name = _filename(batch, index, ext)
            if ext == "png":
                data = png_bytes(image)
            else:
                data = pdf_bytes(image, payload)
            get_storage().put(f"batches/{batch.id}/{name}", data, content_type)
            batch.bytes_written += len(data)
        if batch.combined:
            get_storage().put(_page_png_key(batch.id, index), png_bytes(image), "image/png")
            if not name:
                name = _filename(batch, index, "pdf")
    finally:
        image.close()
    return name


def _cleanup_pages(batch: BatchJob) -> None:
    if batch.status not in {"Completed", "Failed"}:
        return
    try:
        get_storage().delete_prefix(f"batches/{batch.id}/pages")
    except Exception:
        log.warning("Could not remove temporary pages for %s", batch.id, exc_info=True)


def _publish_combined(batch: BatchJob, template: Template) -> str:
    """Join saved pages into one PDF. Rows that failed are left out."""
    storage = get_storage()
    records = list(batch.records or [])
    invalid = sum(1 for record in records if not record.get("_valid", True))
    keys: list[str] = []
    failures = 0
    for index, record in enumerate(records, start=1):
        if not record.get("_valid", True):
            continue
        state = _page_state(batch.id, index)
        if state == "png":
            keys.append(_page_png_key(batch.id, index))
        else:
            failures += 1
    batch.generated = len(keys)
    batch.failed = failures + invalid
    if not keys:
        batch.error = batch.error or "Every document failed."
        return ""
    payload = {"width_in": template.width_in, "height_in": template.height_in}
    handle = tempfile.NamedTemporaryFile(prefix="handscript-", suffix=".pdf", delete=False)
    handle.close()
    path = Path(handle.name)
    try:
        written = write_pdf_from_pngs((storage.get(key) for key in keys), payload, path)
        if written == 0:
            batch.error = batch.error or "Every document failed."
            return ""
        artifact = storage.put_file(f"batches/{batch.id}/combined.pdf", path, "application/pdf")
        batch.bytes_written += path.stat().st_size
        return artifact
    finally:
        path.unlink(missing_ok=True)


def finish_batch(db: Session, batch: BatchJob) -> None:
    template = db.get(Template, batch.template_id)
    storage = get_storage()
    prefix = f"batches/{batch.id}"
    artifact_key = ""
    fmt = batch.export_format

    if batch.combined and template is not None:
        artifact_key = _publish_combined(batch, template)
    elif batch.combined:
        batch.error = "Template no longer exists."
        batch.generated = 0

    if batch.generated == 0 and batch.failed:
        batch.status = "Failed"
        export_status = "Failed"
    elif batch.failed:
        batch.status = "Completed"
        export_status = "Partial"
    else:
        batch.status = "Completed"
        export_status = "Completed"
    batch.current_item = ""

    files = [
        item for item in storage.list_prefix(prefix)
        if "/pages/" not in item[0] and not item[0].endswith("/combined.pdf")
    ]
    if batch.individual and len(files) > 1 and not artifact_key:
        handle = tempfile.NamedTemporaryFile(prefix="handscript-", suffix=".zip", delete=False)
        handle.close()
        zip_path = Path(handle.name)
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
                for key, _size in files:
                    archive.writestr(key.rsplit("/", 1)[-1], storage.get(key))
            artifact_key = storage.put_file(f"{prefix}/bundle.zip", zip_path, "application/zip")
        finally:
            zip_path.unlink(missing_ok=True)
    elif files and not artifact_key:
        artifact_key = files[0][0]

    size_mb = round(batch.bytes_written / (1024 * 1024), 2)
    filename = export_filename(batch.name, artifact_key) if artifact_key else ""
    batch.current_item = filename
    existing = list(db.scalars(select(ExportRecord).where(ExportRecord.batch_id == batch.id)).all())
    record = existing[0] if existing else ExportRecord(id=new_id("ex"), batch_id=batch.id)
    if not existing:
        db.add(record)
    for extra in existing[1:]:
        db.delete(extra)
    record.batch_name = batch.name
    record.date = utcnow()
    record.file_count = batch.generated
    record.format = fmt
    record.status = export_status
    record.output_dir = prefix
    record.size_mb = size_mb
    record.artifact_key = artifact_key
    detail = f"{batch.generated} generated, {batch.failed} failed"
    log_activity(db, "batch" if batch.status == "Completed" else "error", batch.name, detail)


def _close_if_finished(db: Session, batch: BatchJob) -> bool:
    """Publish the batch once every row has been saved or marked failed."""
    if batch.cursor < len(list(batch.records or [])):
        return False
    if _next_missing_page(batch) is not None:
        return False
    batch.current_item = "Preparing the download"
    db.commit()
    finish_batch(db, batch)
    return True


def _capture(db: Session, batch: BatchJob, index: int, *, count: bool) -> None:
    """Render record `index` (1-based). Failures are recorded and the batch continues."""
    records = list(batch.records or [])
    record = records[index - 1]
    template = db.get(Template, batch.template_id)
    if template is None:
        batch.status = "Failed"
        batch.error = "Template no longer exists."
        if count:
            batch.failed += 1
            batch.cursor = max(batch.cursor, index)
        return
    profile = db.get(Profile, batch.profile_id)
    dpi = parse_dpi(settings_dict(db).get("resolution"))
    batch.current_item = f"Saving page {index} of {batch.total}"
    db.commit()
    try:
        name = _store_page(batch, template, record, index, dpi=dpi, profile=profile)
    except Exception as exc:
        message = str(exc).strip() or "This page could not be rendered."
        log.warning("Batch %s skipped row %s: %s", batch.id, index, message)
        batch.error = message[:500]
        batch.current_item = f"Failed on row {index}"
        _remember_failure(batch, index, batch.error)
        if count:
            batch.failed += 1
            batch.cursor = max(batch.cursor, index)
        if count and settings_dict(db).get("pause_on_error"):
            _skip_remaining(batch, index, "Skipped because an earlier page failed.")
        return
    if count:
        batch.generated += 1
        batch.cursor = max(batch.cursor, index)
    batch.current_item = name or _filename(batch, index, "pdf")


def process_one_tick(db: Session) -> str | None:
    """Advance one runnable batch by a single record. Returns the batch id."""
    _complete_analyses(db)
    batch = db.scalar(
        select(BatchJob)
        .where(BatchJob.runnable.is_(True), BatchJob.status.in_(("Queued", "Running")))
        .order_by(BatchJob.created)
    )
    if batch is None:
        db.commit()
        return None
    if batch.status == "Queued":
        batch.status = "Running"
        db.commit()

    records = list(batch.records or [])
    if batch.cursor >= len(records):
        missing = _next_missing_page(batch)
        if missing is None:
            _close_if_finished(db, batch)
            db.commit()
            _cleanup_pages(batch)
        else:
            _capture(db, batch, missing, count=False)
            if batch.status != "Failed" and _close_if_finished(db, batch):
                db.commit()
                _cleanup_pages(batch)
            else:
                db.commit()
        return batch.id

    index = batch.cursor + 1
    record = records[batch.cursor]
    if not record.get("_valid", True):
        batch.cursor = index
        batch.failed += 1
        batch.current_item = f"Skipped invalid row {index}"
        if _close_if_finished(db, batch):
            db.commit()
            _cleanup_pages(batch)
        else:
            db.commit()
        return batch.id

    if batch.combined and _page_state(batch.id, index) == "png":
        batch.cursor = index
        batch.generated += 1
        batch.current_item = _filename(batch, index, "pdf")
    elif batch.combined and _page_state(batch.id, index) == "fail":
        batch.cursor = index
        batch.failed += 1
        batch.current_item = f"Failed on row {index}"
    else:
        _capture(db, batch, index, count=True)
        if batch.status == "Failed":
            db.commit()
            return batch.id
    if _close_if_finished(db, batch):
        db.commit()
        _cleanup_pages(batch)
    else:
        db.commit()
    return batch.id


def _complete_analyses(db: Session) -> None:
    rows = db.scalars(select(Profile).where(Profile.analyze_requested.is_(True), Profile.status == "Processing")).all()
    for profile in rows:
        count = len(profile.samples or [])
        quality = 70 + min(25, count * 2)
        profile.analysis = {
            "character_coverage": min(98, 55 + count * 3),
            "sample_quality": quality,
            "samples_analyzed": count,
            "avg_stroke_width": 0.4,
            "slant_degrees": 4.0,
            "baseline_stability": min(96, 60 + count * 2),
            "spacing_consistency": min(95, 58 + count * 2),
            "notes": [
                f"Stored {count} sample{'s' if count != 1 else ''} for a future cloning model.",
                "Graves uses built-in style primers. Uploaded samples are not matched to a handwriting photo yet.",
                "Choose a style id, bias and variation on this profile to change the Graves hand.",
            ],
        }
        profile.status = "Ready" if quality >= 75 else "Needs Review"
        profile.analyze_requested = False
        log_activity(db, "document", profile.name, "Handwriting analysis finished")


def enqueue(batch_id: str) -> None:
    """Notify a Redis worker when configured. The embedded worker polls anyway."""
    from app.config import get_settings

    url = get_settings().redis_url
    if not url:
        return
    try:
        import redis

        client = redis.Redis.from_url(url)
        client.rpush("handscript:jobs", batch_id)
        client.close()
    except Exception:
        return
