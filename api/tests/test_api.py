"""Generation and import tests. They use a temporary SQLite database."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="handscript-test-"))
os.environ["DATABASE_URL"] = "sqlite:///" + (_tmp / "test.db").as_posix()
os.environ["STORAGE_DIR"] = str(_tmp / "files")
os.environ["EMBEDDED_WORKER"] = "false"
os.environ["REDIS_URL"] = ""
os.environ["HANDWRITING_ENGINE"] = "font"
os.environ["GRAVES_ENABLED"] = "false"
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app import database  # noqa: E402
from app.engine import process_one_tick  # noqa: E402
from app.main import app  # noqa: E402
from app.storage import reset_storage  # noqa: E402

reset_storage()


def test_health_and_seeded_workspace() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["engine"] == "Script font"
        documents = client.get("/api/documents")
        assert documents.status_code == 200
        assert len(documents.json()) >= 8
        profiles = client.get("/api/profiles")
        assert any(item["is_default"] for item in profiles.json())


def test_code_import_keeps_text_and_duplicates() -> None:
    text = "746621250\n0078901234\n\n0078901234\n".encode()
    csv = "code\n746621250\n0078901234\n".encode()
    with TestClient(app) as client:
        sample = client.get("/api/imports/samples/codes.txt")
        assert sample.status_code == 200
        assert "0078901234" in sample.text
        imported = client.post("/api/imports", files={"file": ("codes.txt", text, "text/plain")})
        assert imported.status_code == 201
        body = imported.json()
        assert body["records_detected"] == 4
        assert body["valid_records"] == 3
        assert body["invalid_records"] == 1
        assert [row["code"] for row in body["rows"] if row["code"]] == ["746621250", "0078901234", "0078901234"]
        assert body["issues"][0]["reason"] == "Empty code"
        table = client.post("/api/imports", files={"file": ("codes.csv", csv, "text/csv")})
        assert table.status_code == 201
        assert table.json()["rows"][1]["code"] == "0078901234"


def test_batch_renders_files() -> None:
    csv = "code\n746621250\n \n".encode()
    with TestClient(app) as client:
        imported = client.post("/api/imports", files={"file": ("codes.csv", csv, "text/csv")})
        assert imported.status_code == 201
        body = imported.json()
        assert body["records_detected"] == 2
        assert body["invalid_records"] == 1
        created = client.post("/api/batches", json={
            "name": "Test notes",
            "template_id": "tpl-thankyou",
            "profile_id": "pf-amelia",
            "import_id": body["id"],
            "export_format": "PDF",
            "individual": True,
            "combined": False,
        })
        assert created.status_code == 201
        batch_id = created.json()["id"]

    database.init_db()
    assert database.SessionLocal is not None
    for _ in range(6):
        db = database.SessionLocal()
        try:
            process_one_tick(db)
        finally:
            db.close()

    with TestClient(app) as client:
        batch = client.get(f"/api/batches/{batch_id}").json()
        assert batch["status"] == "Completed"
        assert batch["generated"] == 1
        assert batch["failed"] == 1
        exports = client.get("/api/exports").json()
        match = next(item for item in exports if item["batch_id"] == batch_id)
        assert match["status"] == "Partial"
        download = client.get(f"/api/exports/{match['id']}/download")
        assert download.status_code == 200
        assert download.content[:4] == b"%PDF"


def test_page_sizes_fields_and_engine_fallback() -> None:
    import io

    from PIL import Image

    from app.config import get_settings
    from app.handwriting.factory import get_handwriting_engine, reset_handwriting_engine
    from app.render import fill_text, render_png

    card = render_png(
        {"width_in": 6, "height_in": 4},
        [{
            "id": "body", "type": "Text", "name": "Body", "x": 0.25, "y": 0.4,
            "width": 1.2, "height": 1.5, "font_size": 16,
            "content": "Zip {zip} " + ("address " * 30), "visible": True,
        }],
        {"zip": "007"},
        dpi=300, seed=3, style_id=9, bias=0.75, variation=0,
    )
    page = Image.open(io.BytesIO(card))
    assert page.size == (1800, 1200)
    envelope = render_png({"width_in": 9.5, "height_in": 4.125}, [], {}, dpi=300, seed=1)
    assert Image.open(io.BytesIO(envelope)).size == (2850, 1238)
    assert fill_text("Zip {zip}", {"zip": "007"}) == "Zip 007"

    ink = get_handwriting_engine().render_wrapped(
        "CODE007-" + ("X" * 80),
        max_width_px=90,
        max_height_px=500,
        style_id=None,
        bias=0.75,
        variation=0,
        font_size_pt=18,
        dpi=150,
        seed=2,
        line_gap_px=4,
    )
    assert ink.width <= 90

    settings = get_settings()
    settings.handwriting_engine = "graves"
    settings.graves_enabled = True
    settings.graves_weights_path = str(_tmp / "missing-weights.npz")
    reset_handwriting_engine()
    try:
        assert get_handwriting_engine().name == "font"
    finally:
        settings.handwriting_engine = "font"
        settings.graves_enabled = False
        reset_handwriting_engine()


def test_profile_chooses_handwrite_without_loading_graves() -> None:
    import io

    from PIL import Image

    from app.handwriting.factory import get_handwriting_engine
    from app.render import render_png

    page = render_png(
        {"width_in": 6, "height_in": 4},
        [{
            "id": "body", "type": "Text", "name": "Body", "x": 0.4, "y": 0.5,
            "width": 4.5, "height": 1.2, "font_size": 18,
            "content": "Dear friend, thank you.", "visible": True,
        }],
        {},
        dpi=150, seed=1, engine="handwrite",
    )
    image = Image.open(io.BytesIO(page))
    assert image.size == (900, 600)
    assert image.convert("L").getextrema()[0] < 250
    assert get_handwriting_engine().name == "font"
    assert get_handwriting_engine("handwrite").name == "handwrite"

    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Neat hand", "engine": "handwrite"})
        assert created.status_code == 201
        body = created.json()
        assert body["style"]["engine"] == "handwrite"
        switched = client.patch(f"/api/profiles/{body['id']}", json={
            "style": {"style_id": 9, "bias": 0.75, "variation": 0.15, "engine": "graves"},
        })
        assert switched.status_code == 200
        assert switched.json()["style"]["engine"] == "graves"
        rejected = client.post("/api/profiles", json={"name": "Nope", "engine": "comic"})
        assert rejected.status_code == 422


def test_pillow_hw2font_and_fontmaker_render_without_graves() -> None:
    import io

    from PIL import Image

    from app.handwriting.factory import get_handwriting_engine
    from app.render import render_png

    def ink(engine: str, **extra) -> Image.Image:
        page = render_png(
            {"width_in": 4, "height_in": 2},
            [{
                "id": "body", "type": "Text", "name": "Body", "x": 0.2, "y": 0.3,
                "width": 3.4, "height": 1.2, "font_size": 28,
                "content": "Thank you", "visible": True,
            }],
            {},
            dpi=72, seed=1, engine=engine, **extra,
        )
        return Image.open(io.BytesIO(page)).convert("L")

    caveat = ink("pillow", font_family="caveat").tobytes()
    apple = ink("pillow", font_family="homemade").tobytes()
    assert caveat != apple
    assert min(caveat) < 250
    assert ink("hw2font").size == (288, 144)
    assert ink("fontmaker").size == (288, 144)
    assert get_handwriting_engine().name == "font"
    assert get_handwriting_engine("pillow", font_family="kalam").name == "pillow"
    assert get_handwriting_engine("hw2font").name == "hw2font"
    assert get_handwriting_engine("fontmaker").name == "fontmaker"

    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Caveat cards", "engine": "pillow", "font_family": "caveat"})
        assert created.status_code == 201
        assert created.json()["style"]["engine"] == "pillow"
        assert created.json()["style"]["font_family"] == "caveat"
        sheet = client.get("/api/handwriting/templates/hw2font.pdf")
        assert sheet.status_code == 200
        assert sheet.content[:4] == b"%PDF"
        marked = client.get("/api/handwriting/templates/fontmaker.pdf")
        assert marked.status_code == 200
        assert marked.content[:4] == b"%PDF"


def test_gemini_accepts_exact_strokes_and_refuses_a_missing_sample() -> None:
    import io

    import pytest
    from PIL import Image

    from app.handwriting.factory import get_handwriting_engine
    from app.handwriting.gemini_engine import SYSTEM_PROMPT, parse_handwriting, strokes_to_image, use_samples
    from app.render import render_png

    assert "character for character" in SYSTEM_PROMPT
    xml = """<handwriting>
<verbatim>CODE: 007</verbatim>
<line text="CODE: 007"><stroke width="4" d="M 20 40 L 80 36 L 140 48"/></line>
</handwriting>"""
    image = strokes_to_image(parse_handwriting(xml, "CODE: 007"), 180, 60)
    assert image.getchannel("A").getextrema()[1] > 0
    with pytest.raises(ValueError, match="exactly"):
        parse_handwriting(xml.replace("CODE: 007", "CODE: 007 thanks"), "CODE: 007")
    points = """<handwriting>
<verbatim>0078901234</verbatim>
<line text="0078901234"><stroke width="3"><pt x="10" y="20"/><pt x="40" y="18"/><pt x="70" y="24"/></stroke></line>
</handwriting>"""
    assert parse_handwriting(points, "0078901234")

    with pytest.raises(RuntimeError, match="handwriting photo"):
        render_png(
            {"width_in": 4, "height_in": 2},
            [{
                "id": "body", "type": "Text", "name": "Body", "x": 0.2, "y": 0.3,
                "width": 3.4, "height": 1.2, "font_size": 28,
                "content": "CODE: 007", "visible": True,
            }],
            {},
            dpi=72, seed=1, engine="gemini",
        )
    sample = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(sample, format="PNG")
    engine = get_handwriting_engine("gemini")
    assert engine.name == "gemini"
    assert get_handwriting_engine().name == "font"
    with use_samples([sample.getvalue()]):
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            engine.render_wrapped(
                "CODE: 007",
                max_width_px=120,
                max_height_px=40,
                style_id=None,
                bias=0.75,
                variation=0.15,
                font_size_pt=14,
                dpi=72,
                seed=1,
                line_gap_px=4,
            )
    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Sample hand", "engine": "gemini"})
        assert created.status_code == 201
        assert created.json()["style"]["engine"] == "gemini"
        status = client.get("/api/handwriting/status")
        assert status.status_code == 200
        assert status.json()["gemini"]["configured"] is False
