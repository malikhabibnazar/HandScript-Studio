"""Persistence models. Nested documents (samples, elements, records) are JSON."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="Ready")
    samples: Mapped[list] = mapped_column(JSON, default=list)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    style: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    preview_text: Mapped[str] = mapped_column(String(400), default="The quick brown fox")
    analyze_requested: Mapped[bool] = mapped_column(Boolean, default=False)


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(40))
    width_in: Mapped[float] = mapped_column(Float)
    height_in: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    elements: Mapped[list] = mapped_column(JSON, default=list)
    margin_in: Mapped[float] = mapped_column(Float, default=0.2)
    description: Mapped[str] = mapped_column(Text, default="")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    template_id: Mapped[str] = mapped_column(String(40))
    template_name: Mapped[str] = mapped_column(String(200))
    profile_id: Mapped[str] = mapped_column(String(40))
    profile_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), default="Draft")
    export_format: Mapped[str] = mapped_column(String(40), default="PDF")
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    modified: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    pages: Mapped[int] = mapped_column(Integer, default=1)
    fields: Mapped[dict] = mapped_column(JSON, default=dict)


class ImportJob(Base):
    __tablename__ = "imports"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    filename: Mapped[str] = mapped_column(String(300))
    records: Mapped[list] = mapped_column(JSON, default=list)
    columns: Mapped[list] = mapped_column(JSON, default=list)
    records_detected: Mapped[int] = mapped_column(Integer, default=0)
    valid_records: Mapped[int] = mapped_column(Integer, default=0)
    invalid_records: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BatchJob(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    template_id: Mapped[str] = mapped_column(String(40), default="")
    template_name: Mapped[str] = mapped_column(String(200), default="")
    profile_id: Mapped[str] = mapped_column(String(40), default="")
    profile_name: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(40), default="Queued")
    total: Mapped[int] = mapped_column(Integer, default=0)
    generated: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    export_format: Mapped[str] = mapped_column(String(40), default="PDF")
    output_dir: Mapped[str] = mapped_column(String(400), default="")
    current_item: Mapped[str] = mapped_column(String(300), default="")
    naming: Mapped[str] = mapped_column(String(200), default="document_{index}")
    individual: Mapped[bool] = mapped_column(Boolean, default=True)
    combined: Mapped[bool] = mapped_column(Boolean, default=False)
    records: Mapped[list | None] = mapped_column(JSON, nullable=True)
    runnable: Mapped[bool] = mapped_column(Boolean, default=False)
    bytes_written: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")


class ExportRecord(Base):
    __tablename__ = "exports"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(40), default="")
    batch_name: Mapped[str] = mapped_column(String(200))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    format: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40))
    output_dir: Mapped[str] = mapped_column(String(400), default="")
    size_mb: Mapped[float] = mapped_column(Float, default=0)
    artifact_key: Mapped[str] = mapped_column(String(500), default="")


class Activity(Base):
    __tablename__ = "activity"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(String(400), default="")
    when: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
