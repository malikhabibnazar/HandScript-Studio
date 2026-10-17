"""Batch generation and handwriting analysis.

The API and the worker process share these functions. Each tick renders one
record, stores the file, and commits so progress events stay current.
"""
from __future__ import annotations

import io
import zipfile
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Activity, AppSetting, BatchJob, ExportRecord, Profile, Template, utcnow
from app.config import get_settings
from app.render import parse_dpi, render_combined_pdf, render_pdf, render_png, stable_seed
from app.schemas import export_filename
from app.seed import DEFAULT_SETTINGS
from app.storage import get_storage


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
    if engine in {"graves", "handwrite", "pillow", "hw2font", "fontmaker", "gemini", "onedm", "drawn"}:
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
    if engine in {"handwrite", "hw2font", "fontmaker"} and isinstance(font_path, str) and font_path:
        ink["font_path"] = font_path
    return ink


def _render_one(fmt: str, template: Template, record: dict, *, dpi: int, seed: int, profile: Profile | None) -> bytes:
    payload = {
        "width_in": template.width_in,
        "height_in": template.height_in,
    }
    elements = list(template.elements or [])
    ink = profile_ink(profile)
    if fmt == "PNG":
        return render_png(payload, elements, record, dpi=dpi, seed=seed, **ink)
    return render_pdf(payload, elements, record, dpi=dpi, seed=seed, **ink)


def finish_batch(db: Session, batch: BatchJob) -> None:
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

    template = db.get(Template, batch.template_id)
    storage = get_storage()
    prefix = f"batches/{batch.id}"
    artifact_key = ""
    fmt = batch.export_format

    if batch.combined and template is not None:
        valid = [r for r in (batch.records or []) if r.get("_valid", True)]
        profile = db.get(Profile, batch.profile_id)
        dpi = parse_dpi(settings_dict(db).get("resolution"))
        data = render_combined_pdf(
            {"width_in": template.width_in, "height_in": template.height_in},
            list(template.elements or []),
            valid,
            dpi=dpi,
            seeds=[stable_seed(batch.id, index + 1) for index in range(len(valid))],
            **profile_ink(profile),
        )
        artifact_key = storage.put(f"{prefix}/combined.pdf", data, "application/pdf")
        batch.bytes_written += len(data)

    files = storage.list_prefix(prefix)
    if batch.individual and len(files) > 1 and not artifact_key:
        blob = io.BytesIO()
        with zipfile.ZipFile(blob, "w", zipfile.ZIP_DEFLATED) as archive:
            for key, _size in files:
                archive.writestr(key.rsplit("/", 1)[-1], storage.get(key))
        artifact_key = storage.put(f"{prefix}/bundle.zip", blob.getvalue(), "application/zip")
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

    records = list(batch.records or [])
    if batch.cursor >= len(records):
        finish_batch(db, batch)
        db.commit()
        return batch.id

    record = records[batch.cursor]
    batch.cursor += 1
    index = batch.cursor
    if not record.get("_valid", True):
        batch.failed += 1
        batch.current_item = f"Skipped invalid row {index}"
        if batch.cursor >= len(records):
            finish_batch(db, batch)
        db.commit()
        return batch.id

    template = db.get(Template, batch.template_id)
    if template is None:
        batch.status = "Failed"
        batch.error = "Template no longer exists."
        batch.failed += 1
        db.commit()
        return batch.id

    fmt = "PNG" if batch.export_format == "PNG" else "PDF"
    profile = db.get(Profile, batch.profile_id)
    dpi = parse_dpi(settings_dict(db).get("resolution"))
    try:
        data = _render_one(fmt, template, record, dpi=dpi, seed=stable_seed(batch.id, index), profile=profile)
    except Exception as exc:  # rendering failure should not kill the worker
        batch.failed += 1
        batch.error = str(exc)
        batch.current_item = f"Failed on row {index}"
        prefs = settings_dict(db)
        if prefs.get("pause_on_error"):
            batch.status = "Failed"
        elif batch.cursor >= len(records):
            finish_batch(db, batch)
        db.commit()
        return batch.id

    if batch.individual:
        ext, content_type = _content_type(fmt)
        name = _filename(batch, index, ext)
        key = f"batches/{batch.id}/{name}"
        get_storage().put(key, data, content_type)
        batch.bytes_written += len(data)
        batch.current_item = name
    else:
        batch.current_item = _filename(batch, index, "pdf")
    batch.generated += 1
    if batch.cursor >= len(records):
        finish_batch(db, batch)
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
