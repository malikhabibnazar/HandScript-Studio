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
        assert match["filename"] == "Test notes.pdf"
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


def _column_runs(image) -> list[tuple[int, int]]:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    runs: list[tuple[int, int]] = []
    start = None
    for x in range(rgba.width):
        ink = False
        for y in range(rgba.height):
            red, green, blue, alpha = pixels[x, y]
            if alpha > 20 and red < 90 and green < 90 and blue < 90:
                ink = True
                break
        if ink and start is None:
            start = x
        elif not ink and start is not None:
            runs.append((start, x - 1))
            start = None
    if start is not None:
        runs.append((start, image.width - 1))
    return runs


def _gap_between(runs: list[tuple[int, int]]) -> int:
    if len(runs) < 2:
        return 0
    return min(runs[index][0] - runs[index - 1][1] - 1 for index in range(1, len(runs)))


def test_drawn_letters_stay_separate_and_image_profiles_still_upload() -> None:
    from PIL import Image

    from app.handwriting.factory import get_handwriting_engine
    from app.handwriting.glyph_engine import GlyphJob, choose_set, compose_ink
    from app.handwriting.glyphs import BY_CHAR
    from app.render import render_page

    h_key = BY_CHAR["H"].key
    e_key = BY_CHAR["e"].key
    left = Image.new("RGBA", (36, 48), (0, 0, 0, 255))
    right = Image.new("RGBA", (20, 48), (0, 0, 0, 255))
    metrics = {
        "pad_width": 280, "pad_height": 220, "baseline_y": 150,
        "crop_left": 10, "crop_top": 30, "ink_width": 36, "ink_height": 48,
    }
    other = dict(metrics)
    other["ink_width"] = 20
    job = GlyphJob(
        images={("set1", h_key): left, ("set1", e_key): left, ("set2", e_key): right},
        metrics={("set1", h_key): metrics, ("set1", e_key): metrics, ("set2", e_key): other},
        word_size_px=70, word_spacing_px=15, char_spacing_px=-8,
    )
    ink = compose_ink("He", job, target_em=70, max_width=400, max_height=200, seed=1, variation=0, line_gap_px=8)
    runs = _column_runs(ink)
    assert len(runs) == 2
    assert _gap_between(runs) >= 2

    alternate_seed = next(
        seed for seed in range(80)
        if choose_set(0, e_key, seed, True, True) != choose_set(1, e_key, seed, True, True)
    )
    varied = compose_ink("ee", job, target_em=70, max_width=400, max_height=200, seed=alternate_seed, variation=0, line_gap_px=8)
    varied_runs = _column_runs(varied)
    assert len(varied_runs) == 2
    assert _gap_between(varied_runs) >= 2
    widths = [end - start + 1 for start, end in varied_runs]
    assert widths[0] != widths[1]

    missing = compose_ink("H?H", job, target_em=70, max_width=400, max_height=200, seed=1, variation=0, line_gap_px=8)
    pair = compose_ink("HH", job, target_em=70, max_width=400, max_height=200, seed=1, variation=0, line_gap_px=8)
    assert len(_column_runs(missing)) == 2
    assert missing.getbbox()[2] > pair.getbbox()[2]

    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Print hand", "engine": "drawn", "description": "Drawn letters"})
        assert created.status_code == 201
        body = created.json()
        assert body["style"]["engine"] == "drawn"
        assert body["style"]["source"] == "draw"
        assert body["status"] == "Ready"
        profile_id = body["id"]
        inventory = client.get(f"/api/profiles/{profile_id}/glyphs")
        assert inventory.status_code == 200
        assert inventory.json()["total"] == 90
        assert inventory.json()["set1_count"] == 90
        assert inventory.json()["ready"] is True

        locked = client.patch(f"/api/profiles/{profile_id}", json={
            "style": {"style_id": 9, "bias": 0.75, "variation": 0.15, "engine": "graves"},
        })
        assert locked.status_code == 400
        uploaded = client.post(
            f"/api/profiles/{profile_id}/samples",
            files={"file": ("note.png", b"not-a-real-png", "image/png")},
        )
        assert uploaded.status_code == 400

        preview = client.post(f"/api/profiles/{profile_id}/preview", json={"text": "He"})
        assert preview.status_code == 200
        assert preview.content.startswith(b"\x89PNG")

        photo = client.post("/api/profiles", json={"name": "Photo hand", "engine": "pillow", "font_family": "caveat"})
        assert photo.status_code == 201
        assert photo.json()["style"]["engine"] == "pillow"
        assert photo.json()["style"]["source"] == "image"
        assert client.get(f"/api/profiles/{photo.json()['id']}/glyphs").status_code == 400
        sample = client.post(
            f"/api/profiles/{photo.json()['id']}/samples",
            files={"file": ("note.png", b"not-a-real-png", "image/png")},
        )
        assert sample.status_code == 200
        assert sample.json()["sample_count"] == 1

        page = render_page(
            {"width_in": 6, "height_in": 4},
            [{
                "id": "body", "type": "Text", "name": "Body", "x": 0.3, "y": 0.4,
                "width": 5.2, "height": 1.4, "font_size": 28, "content": "He", "visible": True,
            }],
            {},
            dpi=96, seed=4, engine="drawn", variation=0, glyph_profile_id=profile_id,
            word_size_px=70, word_spacing_px=15, char_spacing_px=-2.5,
        )
        page_runs = _column_runs(page)
        assert len(page_runs) >= 2
        assert _gap_between(page_runs) >= 2
        assert get_handwriting_engine("drawn").name == "drawn"

        document = client.post("/api/documents", json={
            "name": "Print card", "template_id": "tpl-thankyou", "profile_id": profile_id,
        })
        assert document.status_code == 201
        pdf = client.get(f"/api/documents/{document.json()['id']}/preview")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

        cleared = client.delete(f"/api/profiles/{profile_id}/glyphs")
        assert cleared.status_code == 200
        assert cleared.json()["set1_count"] == 0
        assert client.get(f"/api/profiles/{profile_id}").json()["status"] == "Needs Review"
        restored = client.post(f"/api/profiles/{profile_id}/glyphs/restore-sample")
        assert restored.status_code == 200
        assert restored.json()["set1_count"] == 90
        assert client.get(f"/api/profiles/{profile_id}").json()["status"] == "Ready"

        imported = client.post("/api/imports", files={"file": ("codes.csv", b"code\n746621250\n", "text/csv")})
        assert imported.status_code == 201
        batch = client.post("/api/batches", json={
            "name": "Print batch",
            "template_id": "tpl-thankyou",
            "profile_id": profile_id,
            "import_id": imported.json()["id"],
            "export_format": "PDF",
            "individual": True,
            "combined": False,
        })
        assert batch.status_code == 201
        batch_id = batch.json()["id"]

    database.init_db()
    assert database.SessionLocal is not None
    for _ in range(6):
        db = database.SessionLocal()
        try:
            process_one_tick(db)
        finally:
            db.close()

    with TestClient(app) as client:
        finished = client.get(f"/api/batches/{batch_id}").json()
        assert finished["status"] == "Completed"
        assert finished["generated"] == 1
        exports = client.get("/api/exports").json()
        match = next(item for item in exports if item["batch_id"] == batch_id)
        assert match["filename"] == "Print batch.pdf"
        download = client.get(f"/api/exports/{match['id']}/download")
        assert download.status_code == 200
        assert download.content.startswith(b"%PDF")
        assert "Print batch.pdf" in download.headers["content-disposition"]


def test_drawfont_renders_and_builds_without_calling_npx(monkeypatch) -> None:
    import io

    from PIL import Image

    from app.handwriting.drawfont_engine import convert_photos
    from app.handwriting.factory import get_handwriting_engine
    from app.render import render_png

    page = render_png(
        {"width_in": 4, "height_in": 2},
        [{
            "id": "body", "type": "Text", "name": "Body", "x": 0.2, "y": 0.3,
            "width": 3.4, "height": 1.2, "font_size": 28,
            "content": "Thank you", "visible": True,
        }],
        {},
        dpi=72, seed=1, engine="drawfont",
    )
    assert Image.open(io.BytesIO(page)).size == (288, 144)
    assert get_handwriting_engine("drawfont").name == "drawfont"

    monkeypatch.setattr(
        "app.handwriting.drawfont_engine.drawfont_status",
        lambda: {"ready": True, "node": True, "npx": True, "node_version": "v22.0.0", "charsets": ["minimal", "spanish"]},
    )
    calls = {"n": 0}

    def fake_run(args: list[str], cwd: Path) -> None:
        calls["n"] += 1
        calls["args"] = args
        out = Path(args[args.index("-o") + 1])
        out.with_suffix(".ttf").write_bytes(b"T" * 80)
        out.with_suffix(".woff2").write_bytes(b"W" * 40)

    monkeypatch.setattr("app.handwriting.drawfont_engine._run", fake_run)
    missing = convert_photos([("a.png", b"\x89PNG")], _tmp / "missing.ttf", capture="freeform", chars="  ", smooth=1, weight=0)
    assert missing and "order" in missing
    assert calls["n"] == 0

    dest = _tmp / "built.ttf"
    built = convert_photos([("page.jpg", b"\xff\xd8\xff\x00")], dest, capture="spanish", chars="", smooth=1, weight=-1)
    assert built is None
    assert dest.read_bytes() == b"T" * 80
    assert dest.with_suffix(".woff2").read_bytes() == b"W" * 40
    assert calls["args"][0] == "make"
    assert calls["args"][calls["args"].index("--charset") + 1] == "spanish"
    assert "ttf,woff2" in calls["args"]
    assert "--weight=-1" in calls["args"]

    def fake_convert(images, dest_font, *, capture, chars, smooth, weight):
        assert capture == "freeform"
        assert chars == "Hello"
        assert len(images) == 1
        dest_font.parent.mkdir(parents=True, exist_ok=True)
        dest_font.write_bytes(b"F" * 90)
        dest_font.with_suffix(".woff2").write_bytes(b"W" * 50)
        return None

    monkeypatch.setattr("app.handwriting.drawfont_engine.convert_photos", fake_convert)
    monkeypatch.setattr("app.handwriting.drawfont_engine.template_pdf", lambda charset: b"%PDF-" + charset.encode())
    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Photo hand", "engine": "drawfont"})
        assert created.status_code == 201
        body = created.json()
        assert body["style"]["engine"] == "drawfont"
        assert body["style"]["capture"] == "minimal"
        profile_id = body["id"]
        patched = client.patch(f"/api/profiles/{profile_id}", json={"style": {
            "style_id": 9, "bias": 0.75, "variation": 0.15, "engine": "drawfont",
            "font_family": "kalam", "capture": "freeform", "chars": "Hello", "smooth": 1.5, "weight": 0,
        }})
        assert patched.status_code == 200
        assert patched.json()["style"]["capture"] == "freeform"
        uploaded = client.post(
            f"/api/profiles/{profile_id}/samples",
            files={"file": ("hand.png", b"\x89PNG\r\n", "image/png")},
        )
        assert uploaded.status_code == 200
        saved = uploaded.json()["style"]
        assert saved["font_error"] is None
        assert Path(saved["font_path"]).read_bytes() == b"F" * 90
        assert Path(saved["web_font_path"]).read_bytes() == b"W" * 50
        sheet = client.get("/api/handwriting/templates/drawfont-minimal.pdf")
        assert sheet.status_code == 200
        assert sheet.content == b"%PDF-minimal"
        assert client.get("/api/handwriting/templates/missing.pdf").status_code == 404
        status = client.get("/api/handwriting/status")
        assert "ready" in status.json()["drawfont"]


def test_handfonted_reviews_letters_then_previews_text(monkeypatch) -> None:
    import io

    from PIL import Image

    from app.handwriting.factory import get_handwriting_engine

    kalam = Path(__file__).resolve().parents[1] / "app" / "handwriting" / "fonts" / "Kalam-Regular.ttf"
    png = b"\x89PNG\r\n\x1a\n" + b"glyph"

    def fake_process(raw: bytes, filename: str) -> list[dict]:
        assert raw.startswith(b"\x89PNG")
        assert filename == "alphabet.png"
        return [
            {"label": "A", "confidence": 0.91, "png": png},
            {"label": "A", "confidence": 0.42, "png": png},
            {"label": "b", "confidence": 0.8, "png": png},
        ]

    def fake_build(glyphs: list[dict], dest: Path, *, font_name: str, thickness: int) -> None:
        assert font_name == "Jane Hand"
        assert thickness == 80
        assert [item["label"] for item in glyphs] == ["A", "b"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(kalam.read_bytes())

    monkeypatch.setattr("app.handwriting.handfonted_client.process_image", fake_process)
    monkeypatch.setattr("app.handwriting.handfonted_client.build_font", fake_build)
    assert get_handwriting_engine("handfonted").name == "handfonted"

    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Jane Hand", "engine": "handfonted"})
        assert created.status_code == 201
        profile_id = created.json()["id"]
        assert created.json()["style"]["engine"] == "handfonted"
        processed = client.post(
            f"/api/profiles/{profile_id}/handfonted/process",
            files={"file": ("alphabet.png", b"\x89PNG\r\nphoto", "image/png")},
        )
        assert processed.status_code == 200
        glyphs = processed.json()["style"]["glyphs"]
        assert [item["label"] for item in glyphs] == ["A", "A", "b"]
        assert [item["sample"] for item in glyphs] == [1, 1, 1]
        image = client.get(f"/api/profiles/{profile_id}/handfonted/glyphs/{glyphs[0]['id']}")
        assert image.status_code == 200
        assert image.content == png
        glyphs[1]["kept"] = False
        generated = client.post(
            f"/api/profiles/{profile_id}/handfonted/generate",
            json={"glyphs": glyphs, "thickness": 80},
        )
        assert generated.status_code == 200
        assert generated.json()["status"] == "Ready"
        assert Path(generated.json()["style"]["font_path"]).is_file()
        preview = client.post(
            f"/api/profiles/{profile_id}/handfonted/preview",
            json={"text": "Ab"},
        )
        assert preview.status_code == 200
        assert preview.headers["content-type"] == "image/png"
        assert Image.open(io.BytesIO(preview.content)).size[0] > 0


def test_handfonted_keeps_four_samples(monkeypatch) -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"glyph"

    def fake_process(raw: bytes, filename: str) -> list[dict]:
        return [{"label": "e", "confidence": 0.9, "png": png}]

    monkeypatch.setattr("app.handwriting.handfonted_client.process_image", fake_process)
    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Four Hands", "engine": "handfonted"})
        profile_id = created.json()["id"]
        for index in range(4):
            processed = client.post(
                f"/api/profiles/{profile_id}/handfonted/process",
                files={"file": (f"sample-{index}.png", b"\x89PNG\r\nphoto", "image/png")},
            )
            assert processed.status_code == 200
            glyphs = processed.json()["style"]["glyphs"]
            assert len(glyphs) == index + 1
            assert glyphs[-1]["sample"] == index + 1
        blocked = client.post(
            f"/api/profiles/{profile_id}/handfonted/process",
            files={"file": ("sample-5.png", b"\x89PNG\r\nphoto", "image/png")},
        )
        assert blocked.status_code == 400
        assert "4 samples" in blocked.json()["detail"]


def test_handfonted_alphabet_is_62_letters_and_digits() -> None:
    from app.handwriting.handfonted_client import ALPHABET

    assert ALPHABET == set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
    assert len(ALPHABET) == 62


def test_handfonted_fills_a_missing_character_and_replaces_a_crop(monkeypatch) -> None:
    from app.handwriting.handfonted_client import HandfontedError

    recognized = b"\x89PNG\r\n\x1a\n" + b"recognized"
    single = b"\x89PNG\r\n\x1a\n" + b"single"
    crops = {"calls": 0}

    def fake_process(raw: bytes, filename: str) -> list[dict]:
        assert raw.startswith(b"\x89PNG")
        return [{"label": "A", "confidence": 0.91, "png": recognized}]

    def fake_crop(raw: bytes, filename: str) -> bytes:
        crops["calls"] += 1
        assert filename
        if raw == b"many":
            raise HandfontedError("Upload an image that contains only that one character.")
        if raw == b"down":
            raise HandfontedError("The HandFonted container is not running.")
        return single

    def fake_build(glyphs: list[dict], dest: Path, *, font_name: str, thickness: int) -> None:
        assert font_name == "Patched Hand"
        assert thickness == 100
        assert [item["label"] for item in glyphs] == ["Q"]
        assert glyphs[0]["png"] == single
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"font-from-uploaded-q")

    monkeypatch.setattr("app.handwriting.handfonted_client.process_image", fake_process)
    monkeypatch.setattr("app.handwriting.handfonted_client.crop_character", fake_crop)
    monkeypatch.setattr("app.handwriting.handfonted_client.build_font", fake_build)

    def upload(client: TestClient, profile_id: str, raw: bytes, label: str, sample: str):
        return client.post(
            f"/api/profiles/{profile_id}/handfonted/glyphs",
            files={"file": (f"{label}.png", raw, "image/png")},
            data={"label": label, "sample": sample},
        )

    with TestClient(app) as client:
        created = client.post("/api/profiles", json={"name": "Patched Hand", "engine": "handfonted"})
        assert created.status_code == 201
        profile_id = created.json()["id"]
        processed = client.post(
            f"/api/profiles/{profile_id}/handfonted/process",
            files={"file": ("alphabet.png", b"\x89PNG\r\nphoto", "image/png")},
        )
        assert processed.status_code == 200
        glyphs = processed.json()["style"]["glyphs"]
        assert [item["label"] for item in glyphs] == ["A"]
        assert glyphs[0]["manual"] is False
        assert len(processed.json()["samples"]) == 1
        letter = glyphs[0]
        letter["kept"] = False
        saved = client.put(
            f"/api/profiles/{profile_id}/handfonted/glyphs",
            json={"glyphs": [letter], "thickness": 100},
        )
        assert saved.status_code == 200

        replaced = client.post(
            f"/api/profiles/{profile_id}/handfonted/glyphs/{letter['id']}/image",
            files={"file": ("a.png", b"\x89PNG\r\nreplacement", "image/png")},
        )
        assert replaced.status_code == 200
        replaced_glyph = replaced.json()["style"]["glyphs"][0]
        assert replaced_glyph["id"] == letter["id"]
        assert replaced_glyph["label"] == "A"
        assert replaced_glyph["sample"] == 1
        assert replaced_glyph["kept"] is False
        assert replaced_glyph["manual"] is True
        assert replaced_glyph["confidence"] == 1
        assert replaced.json()["status"] == "Needs Review"
        image = client.get(f"/api/profiles/{profile_id}/handfonted/glyphs/{letter['id']}")
        assert image.content == single

        duplicate = upload(client, profile_id, b"\x89PNG\r\nanother-a", "A", "1")
        assert duplicate.status_code == 400
        assert "already has that character" in duplicate.json()["detail"]
        assert crops["calls"] == 1

        missing_sample = upload(client, profile_id, b"\x89PNG\r\nq", "Q", "2")
        assert missing_sample.status_code == 400
        assert "full sample" in missing_sample.json()["detail"]
        rejected = upload(client, profile_id, b"\x89PNG\r\nbang", "!", "1")
        assert rejected.status_code == 400
        too_long = upload(client, profile_id, b"\x89PNG\r\naa", "AA", "1")
        assert too_long.status_code == 400
        empty = upload(client, profile_id, b"", "Q", "1")
        assert empty.status_code == 400
        many = upload(client, profile_id, b"many", "Q", "1")
        assert many.status_code == 422
        assert "only that one character" in many.json()["detail"]
        offline = upload(client, profile_id, b"down", "Q", "1")
        assert offline.status_code == 503

        added = upload(client, profile_id, b"\x89PNG\r\nq", " Q ", "1")
        assert added.status_code == 200
        body = added.json()
        assert body["status"] == "Needs Review"
        assert len(body["samples"]) == 1
        added_glyphs = body["style"]["glyphs"]
        assert [item["label"] for item in added_glyphs] == ["A", "Q"]
        uploaded = added_glyphs[1]
        assert uploaded["manual"] is True
        assert uploaded["kept"] is True
        assert uploaded["sample"] == 1
        assert client.get(f"/api/profiles/{profile_id}/handfonted/glyphs/{uploaded['id']}").content == single

        again = upload(client, profile_id, b"\x89PNG\r\nq2", "Q", "1")
        assert again.status_code == 400
        lower = upload(client, profile_id, b"\x89PNG\r\nlower", "a", "1")
        assert lower.status_code == 200
        assert [item["label"] for item in lower.json()["style"]["glyphs"]] == ["A", "Q", "a"]
        assert len(lower.json()["samples"]) == 1

        for index in range(3):
            nxt = client.post(
                f"/api/profiles/{profile_id}/handfonted/process",
                files={"file": (f"sample-{index}.png", b"\x89PNG\r\nphoto", "image/png")},
            )
            assert nxt.status_code == 200
        assert len(client.get(f"/api/profiles/{profile_id}").json()["samples"]) == 4
        blocked = client.post(
            f"/api/profiles/{profile_id}/handfonted/process",
            files={"file": ("sample-5.png", b"\x89PNG\r\nphoto", "image/png")},
        )
        assert blocked.status_code == 400
        extra = upload(client, profile_id, b"\x89PNG\r\nb", "b", "4")
        assert extra.status_code == 200
        assert len(extra.json()["samples"]) == 4
        assert extra.json()["style"]["glyphs"][-1]["label"] == "b"
        assert extra.json()["style"]["glyphs"][-1]["sample"] == 4

        generated = client.post(
            f"/api/profiles/{profile_id}/handfonted/generate",
            json={"glyphs": added_glyphs, "thickness": 100},
        )
        assert generated.status_code == 200
        assert generated.json()["status"] == "Ready"
        stored = {item["label"]: item for item in generated.json()["style"]["glyphs"]}
        assert stored["Q"]["manual"] is True
        assert stored["A"]["kept"] is False

        unknown = client.post(
            f"/api/profiles/{profile_id}/handfonted/glyphs/gl-0123456789/image",
            files={"file": ("x.png", b"\x89PNG\r\nx", "image/png")},
        )
        assert unknown.status_code == 404
        escaped = client.post(
            f"/api/profiles/{profile_id}/handfonted/glyphs/..%2Fsecret/image",
            files={"file": ("x.png", b"\x89PNG\r\nx", "image/png")},
        )
        assert escaped.status_code == 404
