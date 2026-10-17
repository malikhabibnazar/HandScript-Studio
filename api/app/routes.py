"""HTTP routes for the studio API."""
from __future__ import annotations

import csv
import io
import json
import time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.engine import enqueue, log_activity, new_id, profile_ink, settings_dict
from app.models import (
    Activity,
    AppSetting,
    BatchJob,
    Document,
    ExportRecord,
    ImportJob,
    Profile,
    Template,
    utcnow,
)
from app.handwriting.factory import engine_status
from app.render import parse_dpi, render_pdf, render_png, stable_seed
from app.schemas import (
    BatchCreate,
    BatchOut,
    BulkIds,
    DashboardOut,
    DocumentCreate,
    DocumentDetail,
    DocumentOut,
    DocumentUpdate,
    ExportOut,
    export_filename,
    ImportIssue,
    ImportOut,
    GlyphInventoryOut,
    GlyphPreviewIn,
    ProfileCreate,
    ProfileOut,
    ProfileUpdate,
    SettingsOut,
    SettingsUpdate,
    TemplateCreate,
    TemplateOut,
    TemplateUpdate,
)
from app.storage import get_storage

router = APIRouter(prefix="/api")

SAMPLE_CODES = ("746621250", "0078901234", "82154767", "9887654321")


def _one(db: Session, model, item_id: str):
    row = db.get(model, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Not found")
    return row


def _profile_name(db: Session, profile_id: str | None) -> tuple[str, str]:
    if not profile_id:
        default = db.scalar(select(Profile).where(Profile.is_default.is_(True)))
        if default is None:
            default = db.scalar(select(Profile).limit(1))
        if default is None:
            raise HTTPException(status_code=400, detail="Create a handwriting profile first")
        return default.id, default.name
    profile = _one(db, Profile, profile_id)
    return profile.id, profile.name


def _sync_profile_names(db: Session, profile: Profile) -> None:
    docs = db.scalars(select(Document).where(Document.profile_id == profile.id)).all()
    for doc in docs:
        doc.profile_name = profile.name


# ---------------------------------------------------------------- dashboard
@router.get("/health")
def health() -> dict[str, str]:
    from app.config import get_settings

    settings = get_settings()
    handwriting = engine_status()
    return {
        "status": "ok",
        "database": "PostgreSQL" if settings.database_dialect.startswith("postgres") else "SQLite",
        "storage": "S3" if settings.uses_s3 else "Local disk",
        "worker": "Embedded" if settings.embedded_worker else "Redis worker",
        "engine": "Graves LSTM" if handwriting["active"] == "graves" else "Script font",
        "handwriting": str(handwriting["message"]),
    }


@router.get("/handwriting/status")
def handwriting_status() -> dict:
    return engine_status()


@router.get("/handwriting/templates/{name}")
def handwriting_template(name: str) -> Response:
    from app.handwriting.sheet_engine import template_pdf

    kind = {"hw2font.pdf": "hw2font", "fontmaker.pdf": "fontmaker"}.get(name)
    if kind is None:
        raise HTTPException(status_code=404, detail="Unknown template")
    try:
        data = template_pdf(kind)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Template could not be built ({exc})") from exc
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    generated = db.scalar(select(func.count()).select_from(Document).where(Document.status == "Completed")) or 0
    recent = db.scalar(select(func.count()).select_from(BatchJob)) or 0
    activity = db.scalars(select(Activity).order_by(Activity.when.desc()).limit(8)).all()
    return DashboardOut(
        counts={
            "profiles": db.scalar(select(func.count()).select_from(Profile)) or 0,
            "templates": db.scalar(select(func.count()).select_from(Template)) or 0,
            "documents_generated": generated,
            "recent_batches": recent,
        },
        activity=list(activity),
        system=health(),
    )


# ---------------------------------------------------------------- profiles
@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles(db: Session = Depends(get_db)) -> list[Profile]:
    return list(db.scalars(select(Profile).order_by(Profile.created.desc())).all())


def _style_dict(engine: str, font_family: str) -> dict:
    drawn = engine == "drawn"
    return {
        "style_id": 9,
        "bias": 0.75,
        "variation": 0.15,
        "engine": engine,
        "font_family": font_family,
        "source": "draw" if drawn else "image",
        "word_size_px": 70,
        "word_spacing_px": 15,
        "char_spacing_px": -2.5,
        "ink_color": None,
    }


def _engine_name(profile: Profile) -> str:
    style = profile.style if isinstance(profile.style, dict) else {}
    return str(style.get("engine") or "")


def _require_drawn(profile: Profile) -> None:
    if _engine_name(profile) != "drawn":
        raise HTTPException(status_code=400, detail="This profile uses an uploaded sample, not drawn letters")


def _sync_drawn_status(profile: Profile) -> None:
    from app.handwriting.glyphs import glyphs_ready

    profile.status = "Ready" if glyphs_ready(profile.id) else "Needs Review"


@router.post("/profiles", response_model=ProfileOut, status_code=201)
def create_profile(body: ProfileCreate, db: Session = Depends(get_db)) -> Profile:
    profile = Profile(
        id=new_id("pf"), name=body.name.strip(), description=body.description,
        status="Needs Review", samples=[], created=utcnow(), preview_text=body.preview_text,
        style=_style_dict(body.engine, body.font_family),
    )
    db.add(profile)
    if body.engine == "drawn":
        from app.handwriting.glyphs import restore_sample

        restore_sample(profile.id)
        _sync_drawn_status(profile)
    log_activity(db, "document", profile.name, "Handwriting profile created")
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: str, db: Session = Depends(get_db)) -> Profile:
    return _one(db, Profile, profile_id)


@router.patch("/profiles/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: str, body: ProfileUpdate, db: Session = Depends(get_db)) -> Profile:
    profile = _one(db, Profile, profile_id)
    data = body.model_dump(exclude_unset=True)
    if "style" in data and isinstance(data["style"], dict):
        current = _engine_name(profile)
        nxt = str(data["style"].get("engine") or "")
        if current == "drawn" and nxt != "drawn":
            raise HTTPException(status_code=400, detail="Draw profiles stay on the drawn-letter renderer")
        if current != "drawn" and nxt == "drawn":
            raise HTTPException(status_code=400, detail="Create a draw-based profile to use drawn letters")
        data["style"]["source"] = "draw" if nxt == "drawn" else "image"
    for key, value in data.items():
        setattr(profile, key, value)
    if "style" in data and isinstance(profile.style, dict):
        from app.handwriting.handwrite_engine import attach_personal_font

        profile.style = attach_personal_font(
            profile.id, list(profile.samples or []), profile.style, get_storage().get,
        )
    _sync_profile_names(db, profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: str, db: Session = Depends(get_db)) -> None:
    profile = _one(db, Profile, profile_id)
    if profile.is_default:
        raise HTTPException(status_code=400, detail="Choose another default before deleting this profile")
    get_storage().delete_prefix(f"glyphs/{profile.id}/")
    db.delete(profile)
    log_activity(db, "document", profile.name, "Handwriting profile deleted")
    db.commit()


@router.post("/profiles/{profile_id}/default", response_model=ProfileOut)
def set_default_profile(profile_id: str, db: Session = Depends(get_db)) -> Profile:
    profile = _one(db, Profile, profile_id)
    for row in db.scalars(select(Profile)).all():
        row.is_default = row.id == profile.id
    prefs = settings_dict(db)
    prefs["default_profile_id"] = profile.id
    stored = db.get(AppSetting, "app")
    if stored:
        stored.value = prefs
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/profiles/{profile_id}/samples", response_model=ProfileOut)
async def add_sample(profile_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)) -> Profile:
    profile = _one(db, Profile, profile_id)
    if _engine_name(profile) == "drawn":
        raise HTTPException(status_code=400, detail="Draw profiles store letters from the drawing pad")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")
    filename = file.filename or "sample.png"
    sample_id = new_id("sm")
    key = f"samples/{profile.id}/{sample_id}-{filename}"
    get_storage().put(key, raw, file.content_type or "application/octet-stream")
    samples = list(profile.samples or [])
    samples.append({
        "id": sample_id,
        "filename": filename,
        "added": utcnow().isoformat(),
        "quality": 80,
        "characters": max(20, min(90, len(raw) // 800)),
    })
    profile.samples = samples
    if isinstance(profile.style, dict) and profile.style.get("engine") in {"handwrite", "hw2font", "fontmaker"}:
        from app.handwriting.handwrite_engine import attach_personal_font

        profile.style = attach_personal_font(profile.id, samples, profile.style, get_storage().get)
    if profile.status == "Error":
        profile.status = "Needs Review"
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/profiles/{profile_id}/analyze", response_model=ProfileOut)
def analyze_profile(profile_id: str, db: Session = Depends(get_db)) -> Profile:
    profile = _one(db, Profile, profile_id)
    if _engine_name(profile) == "drawn":
        raise HTTPException(status_code=400, detail="Draw profiles do not use photo analysis")
    if not profile.samples:
        raise HTTPException(status_code=400, detail="Add at least one handwriting sample first")
    profile.status = "Processing"
    profile.analyze_requested = True
    profile.analysis = None
    db.commit()
    db.refresh(profile)
    return profile


def _glyph_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/profiles/{profile_id}/glyphs", response_model=GlyphInventoryOut)
def list_glyphs(profile_id: str, db: Session = Depends(get_db)) -> dict:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    from app.handwriting.glyphs import inventory

    return inventory(profile.id)


@router.get("/profiles/{profile_id}/glyphs/{set_name}/{key}")
def get_glyph(profile_id: str, set_name: str, key: str, db: Session = Depends(get_db)) -> Response:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    from app.handwriting.glyphs import read_glyph_png

    try:
        raw = read_glyph_png(profile.id, set_name, key)
    except ValueError as exc:
        raise _glyph_error(exc) from exc
    if raw is None:
        raise HTTPException(status_code=404, detail="That letter has not been drawn")
    return Response(content=raw, media_type="image/png")


@router.put("/profiles/{profile_id}/glyphs/{set_name}/{key}", response_model=GlyphInventoryOut)
async def put_glyph(
    profile_id: str,
    set_name: str,
    key: str,
    file: UploadFile = File(...),
    baseline_y: float = Form(...),
    pad_width: int = Form(...),
    pad_height: int = Form(...),
    crop_left: int = Form(...),
    crop_top: int = Form(...),
    db: Session = Depends(get_db),
) -> dict:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    raw = await file.read()
    from app.handwriting.glyphs import inventory, save_glyph

    try:
        save_glyph(
            profile.id, set_name, key, raw,
            baseline_y=baseline_y, pad_width=pad_width, pad_height=pad_height,
            crop_left=crop_left, crop_top=crop_top,
        )
    except ValueError as exc:
        raise _glyph_error(exc) from exc
    _sync_drawn_status(profile)
    db.commit()
    return inventory(profile.id)


@router.delete("/profiles/{profile_id}/glyphs/{set_name}/{key}", response_model=GlyphInventoryOut)
def remove_glyph(profile_id: str, set_name: str, key: str, db: Session = Depends(get_db)) -> dict:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    from app.handwriting.glyphs import delete_glyph, inventory

    try:
        delete_glyph(profile.id, set_name, key)
    except ValueError as exc:
        raise _glyph_error(exc) from exc
    _sync_drawn_status(profile)
    db.commit()
    return inventory(profile.id)


@router.post("/profiles/{profile_id}/glyphs/restore-sample", response_model=GlyphInventoryOut)
def restore_glyph_sample(profile_id: str, db: Session = Depends(get_db)) -> dict:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    from app.handwriting.glyphs import inventory, restore_sample

    restore_sample(profile.id)
    _sync_drawn_status(profile)
    db.commit()
    return inventory(profile.id)


@router.delete("/profiles/{profile_id}/glyphs", response_model=GlyphInventoryOut)
def clear_glyph_sample(profile_id: str, db: Session = Depends(get_db)) -> dict:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    from app.handwriting.glyphs import clear_glyphs, inventory

    clear_glyphs(profile.id)
    _sync_drawn_status(profile)
    db.commit()
    return inventory(profile.id)


@router.post("/profiles/{profile_id}/preview")
def preview_glyphs(profile_id: str, body: GlyphPreviewIn, db: Session = Depends(get_db)) -> Response:
    profile = _one(db, Profile, profile_id)
    _require_drawn(profile)
    from app.handwriting.glyph_engine import load_glyph_job, render_ruled_preview

    style = profile.style if isinstance(profile.style, dict) else {}
    text = (body.text or profile.preview_text or "")[:4000]
    color = style.get("ink_color")
    job = load_glyph_job(
        profile.id,
        word_size_px=float(style.get("word_size_px", 70)),
        word_spacing_px=float(style.get("word_spacing_px", 15)),
        char_spacing_px=float(style.get("char_spacing_px", -2.5)),
        ink_color=color if isinstance(color, str) else None,
    )
    png = render_ruled_preview(text, job, seed=stable_seed(profile.id, text), variation=float(style.get("variation", 0.15)))
    return Response(content=png, media_type="image/png")


# --------------------------------------------------------------- templates
@router.get("/templates", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[Template]:
    return list(db.scalars(select(Template).order_by(Template.modified.desc())).all())


def _blank_template(kind: str) -> tuple[float, float, list[dict]]:
    if kind == "#10 Envelope":
        return 9.5, 4.125, [{
            "id": new_id("el"), "type": "Address", "name": "Recipient",
            "x": 3.2, "y": 1.6, "width": 5.2, "height": 1.2,
            "align": "left", "font_size": 14,
            "content": "{first_name} {last_name}\n{street}\n{city}, {state} {zip}",
            "visible": True,
        }]
    return 6.0, 4.0, [{
        "id": new_id("el"), "type": "Text", "name": "Greeting",
        "x": 0.4, "y": 0.5, "width": 5.2, "height": 0.6,
        "align": "left", "font_size": 20, "content": "Dear {first_name},", "visible": True,
    }]


@router.post("/templates", response_model=TemplateOut, status_code=201)
def create_template(body: TemplateCreate, db: Session = Depends(get_db)) -> Template:
    width, height, elements = _blank_template(body.kind)
    template = Template(
        id=new_id("tpl"), name=body.name.strip() or "Untitled template", kind=body.kind,
        width_in=width, height_in=height, status="Draft", modified=utcnow(),
        elements=elements, description=body.description,
    )
    db.add(template)
    log_activity(db, "template", template.name, "Template created")
    db.commit()
    db.refresh(template)
    return template


@router.get("/templates/{template_id}", response_model=TemplateOut)
def get_template(template_id: str, db: Session = Depends(get_db)) -> Template:
    return _one(db, Template, template_id)


@router.patch("/templates/{template_id}", response_model=TemplateOut)
def update_template(template_id: str, body: TemplateUpdate, db: Session = Depends(get_db)) -> Template:
    template = _one(db, Template, template_id)
    data = body.model_dump(exclude_unset=True)
    if body.elements is not None:
        data["elements"] = [el.model_dump() for el in body.elements]
    for key, value in data.items():
        setattr(template, key, value)
    template.modified = utcnow()
    for doc in db.scalars(select(Document).where(Document.template_id == template.id)).all():
        doc.template_name = template.name
    db.commit()
    db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: str, db: Session = Depends(get_db)) -> None:
    template = _one(db, Template, template_id)
    db.delete(template)
    log_activity(db, "template", template.name, "Template deleted")
    db.commit()


@router.post("/templates/{template_id}/duplicate", response_model=TemplateOut, status_code=201)
def duplicate_template(template_id: str, db: Session = Depends(get_db)) -> Template:
    source = _one(db, Template, template_id)
    copy = Template(
        id=new_id("tpl"), name=f"{source.name} copy", kind=source.kind,
        width_in=source.width_in, height_in=source.height_in, status="Draft",
        modified=utcnow(), elements=list(source.elements or []),
        margin_in=source.margin_in, description=source.description,
    )
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return copy


# --------------------------------------------------------------- documents
@router.get("/documents", response_model=list[DocumentOut])
def list_documents(q: str = "", status: str = "", db: Session = Depends(get_db)) -> list[Document]:
    stmt = select(Document).order_by(Document.modified.desc())
    if q:
        stmt = stmt.where(func.lower(Document.name).contains(q.lower()))
    if status:
        stmt = stmt.where(Document.status == status)
    return list(db.scalars(stmt).all())


@router.post("/documents", response_model=DocumentDetail, status_code=201)
def create_document(body: DocumentCreate, db: Session = Depends(get_db)) -> DocumentDetail:
    template = _one(db, Template, body.template_id)
    profile_id, profile_name = _profile_name(db, body.profile_id)
    doc = Document(
        id=new_id("doc"),
        name=(body.name or f"Untitled — {template.name}").strip(),
        template_id=template.id, template_name=template.name,
        profile_id=profile_id, profile_name=profile_name,
        status="Draft", export_format="PDF", created=utcnow(), modified=utcnow(), fields={},
    )
    db.add(doc)
    log_activity(db, "document", doc.name, "Document created")
    db.commit()
    db.refresh(doc)
    return _document_detail(db, doc)


def _document_detail(db: Session, doc: Document) -> DocumentDetail:
    detail = DocumentDetail.model_validate(doc)
    template = db.get(Template, doc.template_id)
    profile = db.get(Profile, doc.profile_id)
    detail.template = TemplateOut.model_validate(template) if template else None
    detail.profile = ProfileOut.model_validate(profile) if profile else None
    return detail


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentDetail:
    return _document_detail(db, _one(db, Document, document_id))


@router.patch("/documents/{document_id}", response_model=DocumentDetail)
def update_document(document_id: str, body: DocumentUpdate, db: Session = Depends(get_db)) -> DocumentDetail:
    doc = _one(db, Document, document_id)
    data = body.model_dump(exclude_unset=True)
    if "profile_id" in data and data["profile_id"]:
        profile = _one(db, Profile, data["profile_id"])
        doc.profile_id = profile.id
        doc.profile_name = profile.name
        data.pop("profile_id")
    for key, value in data.items():
        setattr(doc, key, value)
    doc.modified = utcnow()
    db.commit()
    db.refresh(doc)
    return _document_detail(db, doc)


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str, db: Session = Depends(get_db)) -> None:
    doc = _one(db, Document, document_id)
    db.delete(doc)
    db.commit()


@router.post("/documents/bulk-delete", status_code=204)
def bulk_delete_documents(body: BulkIds, db: Session = Depends(get_db)) -> None:
    for item_id in body.ids:
        doc = db.get(Document, item_id)
        if doc:
            db.delete(doc)
    db.commit()


@router.post("/documents/{document_id}/duplicate", response_model=DocumentOut, status_code=201)
def duplicate_document(document_id: str, db: Session = Depends(get_db)) -> Document:
    source = _one(db, Document, document_id)
    copy = Document(
        id=new_id("doc"), name=f"{source.name} copy", template_id=source.template_id,
        template_name=source.template_name, profile_id=source.profile_id,
        profile_name=source.profile_name, status="Draft", export_format=source.export_format,
        created=utcnow(), modified=utcnow(), pages=source.pages, fields=dict(source.fields or {}),
    )
    db.add(copy)
    log_activity(db, "document", copy.name, f"Duplicated from {source.name}")
    db.commit()
    db.refresh(copy)
    return copy


def _merged_elements(template: Template, fields: dict) -> list[dict]:
    merged = []
    for el in template.elements or []:
        item = dict(el)
        if item.get("id") in (fields or {}):
            item["content"] = fields[item["id"]]
        merged.append(item)
    return merged


@router.get("/documents/{document_id}/preview")
def preview_document(document_id: str, db: Session = Depends(get_db)) -> Response:
    doc = _one(db, Document, document_id)
    template = _one(db, Template, doc.template_id)
    payload = {"width_in": template.width_in, "height_in": template.height_in}
    elements = _merged_elements(template, doc.fields or {})
    profile = db.get(Profile, doc.profile_id)
    dpi = parse_dpi(settings_dict(db).get("resolution"))
    ink = profile_ink(profile)
    seed = stable_seed(doc.id, "preview")
    try:
        if doc.export_format == "PNG":
            data = render_png(payload, elements, {}, dpi=dpi, seed=seed, **ink)
            media = "image/png"
        else:
            data = render_pdf(payload, elements, {}, dpi=dpi, seed=seed, **ink)
            media = "application/pdf"
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return Response(content=data, media_type=media)


# ------------------------------------------------------------------ imports
def _sample_csv() -> str:
    return "code\n" + "\n".join(SAMPLE_CODES) + "\n"


def _sample_txt() -> str:
    return "\n".join(SAMPLE_CODES) + "\n"


def _code_record(line: int, code: str, extra: dict | None = None) -> dict:
    """Keep the code as text. Repeated codes stay; only a blank value is invalid."""
    item = {"code": code, "_line": line}
    if extra:
        item.update(extra)
    if code:
        item["_valid"] = True
    else:
        item["_valid"] = False
        item["_reason"] = "Empty code"
    return item


def _finish_import(filename: str, columns: list[str], records: list[dict]) -> ImportJob:
    if not records:
        raise HTTPException(status_code=400, detail="The file has no codes")
    valid = sum(1 for row in records if row.get("_valid"))
    return ImportJob(
        id=new_id("im"), filename=filename, records=records, columns=columns,
        records_detected=len(records), valid_records=valid, invalid_records=len(records) - valid,
        created=utcnow(),
    )


def _parse_txt(filename: str, text: str) -> ImportJob:
    records = [_code_record(line_no, raw_line.strip()) for line_no, raw_line in enumerate(text.splitlines(), start=1)]
    return _finish_import(filename, ["code"], records)


def _parse_csv_codes(filename: str, text: str) -> ImportJob:
    rows = list(csv.reader(io.StringIO(text)))
    rows = [row for row in rows if any(cell.strip() for cell in row) or len(row) > 0]
    if not rows or not any(any(cell.strip() for cell in row) for row in rows):
        raise HTTPException(status_code=400, detail="The file has no codes")
    header = [cell.strip() for cell in rows[0]]
    lowered = [cell.lower() for cell in header]
    if "code" in lowered:
        index = lowered.index("code")
        records = []
        for line_no, row in enumerate(rows[1:], start=2):
            if not any(cell.strip() for cell in row):
                records.append(_code_record(line_no, ""))
                continue
            code = row[index].strip() if index < len(row) else ""
            extra = {}
            for column, cell in zip(header, row):
                key = column.strip()
                if not key or key.lower() == "code":
                    continue
                extra[key] = cell.strip()
            records.append(_code_record(line_no, code, extra))
        columns = ["code", *[name for name in header if name and name.lower() != "code"]]
        return _finish_import(filename, columns, records)
    if any(len([cell for cell in row if cell.strip()]) > 1 for row in rows):
        raise HTTPException(
            status_code=400,
            detail="CSV needs a code column. Download the example CSV to see the format.",
        )
    records = [_code_record(line_no, (row[0].strip() if row else "")) for line_no, row in enumerate(rows, start=1)]
    return _finish_import(filename, ["code"], records)


def _parse_import(filename: str, raw: bytes) -> ImportJob:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="The file must be UTF-8 text") from exc
    name = (filename or "").lower()
    if name.endswith(".txt"):
        return _parse_txt(filename or "codes.txt", text)
    if name.endswith(".csv"):
        return _parse_csv_codes(filename or "codes.csv", text)
    raise HTTPException(status_code=400, detail="Upload a .csv or .txt file of codes")


def _import_out(job: ImportJob) -> ImportOut:
    preview = []
    issues = []
    for row in job.records:
        if len(preview) < 8:
            preview.append({
                key: "" if value is None else str(value)
                for key, value in row.items()
                if not str(key).startswith("_")
            })
        if not row.get("_valid", True):
            issues.append(ImportIssue(line=int(row.get("_line") or 0), reason=str(row.get("_reason") or "Invalid code")))
    return ImportOut(
        id=job.id, filename=job.filename, records_detected=job.records_detected,
        valid_records=job.valid_records, invalid_records=job.invalid_records,
        columns=list(job.columns or []), rows=preview, issues=issues,
    )


@router.get("/imports/samples/{filename}")
def download_import_sample(filename: str) -> Response:
    if filename == "codes.csv":
        body, media = _sample_csv(), "text/csv"
    elif filename == "codes.txt":
        body, media = _sample_txt(), "text/plain"
    else:
        raise HTTPException(status_code=404, detail="Sample not found")
    return Response(
        content=body,
        media_type=f"{media}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/imports", response_model=ImportOut, status_code=201)
async def create_import(file: UploadFile = File(...), db: Session = Depends(get_db)) -> ImportOut:
    job = _parse_import(file.filename or "codes.csv", await file.read())
    db.add(job)
    log_activity(db, "import", job.filename, f"{job.valid_records} valid codes, {job.invalid_records} flagged")
    db.commit()
    return _import_out(job)


# ------------------------------------------------------------------ batches
@router.get("/batches", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db)) -> list[BatchJob]:
    return list(db.scalars(select(BatchJob).order_by(BatchJob.created.desc())).all())


@router.post("/batches", response_model=BatchOut, status_code=201)
def create_batch(body: BatchCreate, db: Session = Depends(get_db)) -> BatchJob:
    template = _one(db, Template, body.template_id)
    profile = _one(db, Profile, body.profile_id)
    if profile.status != "Ready":
        raise HTTPException(status_code=400, detail="Choose a handwriting profile that is ready")
    imported = _one(db, ImportJob, body.import_id)
    if imported.records_detected == 0:
        raise HTTPException(status_code=400, detail="The import has no records")
    if not body.individual and not body.combined:
        raise HTTPException(status_code=400, detail="Choose individual files, a combined PDF, or both")
    prefs = settings_dict(db)
    records = []
    for row in imported.records:
        item = dict(row)
        item.setdefault("sender", prefs.get("workspace") or "HandScript")
        records.append(item)
    batch = BatchJob(
        id=new_id("bt"), name=body.name.strip() or imported.filename, template_id=template.id,
        template_name=template.name, profile_id=profile.id, profile_name=profile.name,
        status="Queued", total=len(records), generated=0, failed=0, cursor=0, created=utcnow(),
        export_format=body.export_format, output_dir=f"batches/{new_id('out')}",
        naming=body.naming or "document_{index}", individual=body.individual, combined=body.combined,
        records=records, runnable=True,
    )
    batch.output_dir = f"batches/{batch.id}"
    db.add(batch)
    log_activity(db, "batch", batch.name, f"Queued {batch.total} records")
    db.commit()
    db.refresh(batch)
    enqueue(batch.id)
    return batch


@router.get("/batches/{batch_id}", response_model=BatchOut)
def get_batch(batch_id: str, db: Session = Depends(get_db)) -> BatchJob:
    return _one(db, BatchJob, batch_id)


@router.post("/batches/{batch_id}/pause", response_model=BatchOut)
def pause_batch(batch_id: str, db: Session = Depends(get_db)) -> BatchJob:
    batch = _one(db, BatchJob, batch_id)
    if not batch.runnable:
        raise HTTPException(status_code=400, detail="This batch is a history record")
    if batch.status in ("Queued", "Running"):
        batch.status = "Paused"
        db.commit()
        db.refresh(batch)
    return batch


@router.post("/batches/{batch_id}/resume", response_model=BatchOut)
def resume_batch(batch_id: str, db: Session = Depends(get_db)) -> BatchJob:
    batch = _one(db, BatchJob, batch_id)
    if not batch.runnable:
        raise HTTPException(status_code=400, detail="This batch is a history record")
    if batch.status in ("Paused", "Queued"):
        batch.status = "Queued"
        batch.runnable = True
        db.commit()
        db.refresh(batch)
        enqueue(batch.id)
    return batch


@router.post("/batches/{batch_id}/cancel", response_model=BatchOut)
def cancel_batch(batch_id: str, db: Session = Depends(get_db)) -> BatchJob:
    batch = _one(db, BatchJob, batch_id)
    if not batch.runnable:
        raise HTTPException(status_code=400, detail="This batch is a history record")
    if batch.status not in ("Completed", "Cancelled"):
        batch.status = "Cancelled"
        batch.current_item = ""
        db.commit()
        db.refresh(batch)
    return batch


@router.get("/batches/{batch_id}/events")
def batch_events(batch_id: str) -> StreamingResponse:
    def stream():
        while True:
            db = SessionLocal()
            try:
                batch = db.get(BatchJob, batch_id)
                if batch is None:
                    yield "event: error\ndata: {\"detail\":\"Not found\"}\n\n"
                    break
                payload = BatchOut.model_validate(batch).model_dump(mode="json")
                yield f"data: {json.dumps(payload)}\n\n"
                if batch.status in ("Completed", "Failed", "Cancelled") or not batch.runnable:
                    break
            finally:
                db.close()
            time.sleep(0.4)

    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database is not ready")
    return StreamingResponse(stream(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    })


# ------------------------------------------------------------------ exports
@router.get("/exports", response_model=list[ExportOut])
def list_exports(db: Session = Depends(get_db)) -> list[ExportRecord]:
    return list(db.scalars(select(ExportRecord).order_by(ExportRecord.date.desc())).all())


@router.delete("/exports/{export_id}", status_code=204)
def delete_export(export_id: str, db: Session = Depends(get_db)) -> None:
    row = _one(db, ExportRecord, export_id)
    if row.output_dir:
        get_storage().delete_prefix(row.output_dir)
    db.delete(row)
    db.commit()


@router.get("/exports/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db)) -> Response:
    row = _one(db, ExportRecord, export_id)
    if not row.artifact_key:
        raise HTTPException(status_code=404, detail="This export has no downloadable file")
    try:
        data = get_storage().get(row.artifact_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="File is no longer in storage") from exc
    filename = export_filename(row.batch_name, row.artifact_key)
    media = "application/zip" if filename.endswith(".zip") else "application/pdf" if filename.endswith(".pdf") else "image/png"
    return Response(content=data, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="{filename}"',
    })


# ----------------------------------------------------------------- settings
@router.get("/settings", response_model=SettingsOut)
def get_settings_route(db: Session = Depends(get_db)) -> SettingsOut:
    data = settings_dict(db)
    cache = sum(size for _key, size in get_storage().list_prefix("cache"))
    data["cache_bytes"] = cache
    return SettingsOut(**data)


@router.put("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsOut:
    current = settings_dict(db)
    current.update(body.model_dump(exclude_unset=True))
    row = db.get(AppSetting, "app")
    if row is None:
        db.add(AppSetting(key="app", value=current))
    else:
        row.value = current
    db.commit()
    current["cache_bytes"] = sum(size for _key, size in get_storage().list_prefix("cache"))
    return SettingsOut(**current)


@router.post("/settings/clear-cache")
def clear_cache() -> dict[str, int]:
    freed = get_storage().delete_prefix("cache")
    return {"freed_bytes": freed}
