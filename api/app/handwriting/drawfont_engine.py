"""draw-your-font renderer.

The npm CLI at https://drawyourfont.com turns a photo of handwriting into
TTF and WOFF2 on this machine. Node.js 18+ is the only dependency: there is
no upload and no FontForge binary. Until a photo converts, cards use a
bundled handwriting face.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

PACKAGE = "draw-your-font@0.1.0"
CAPTURES = ("minimal", "spanish", "freeform")
IMAGE_MAGIC = (
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG", ".png"),
    (b"RIFF", ".webp"),
)


def drawfont_status() -> dict:
    version = _node_version()
    npx = _which("npx")
    ready = _major(version) >= 18 and npx is not None
    return {
        "node": version is not None,
        "node_version": version,
        "npx": npx is not None,
        "ready": ready,
        "charsets": ["minimal", "spanish"],
    }


def template_pdf(charset: str) -> bytes:
    choice = (charset or "minimal").strip().lower()
    if choice not in {"minimal", "spanish"}:
        raise ValueError(choice)
    if not drawfont_status()["ready"]:
        raise RuntimeError("Node.js 18 or newer is required for draw-your-font.")
    with tempfile.TemporaryDirectory(prefix="drawfont-template-") as temp:
        dest = Path(temp) / "template.pdf"
        _run(["template", "-o", str(dest), "--charset", choice], Path(temp))
        if not dest.is_file() or dest.stat().st_size < 64:
            raise RuntimeError("draw-your-font did not write a template.")
        return dest.read_bytes()


def convert_photos(
    images: list[tuple[str, bytes]],
    dest: Path,
    *,
    capture: str,
    chars: str,
    smooth: float,
    weight: float,
) -> str | None:
    """Build TTF and WOFF2. Returns an error string, or None on success."""
    status = drawfont_status()
    if not status["ready"]:
        return "Node.js 18 or newer is required. draw-your-font runs locally and does not upload the photo."
    mode = (capture or "minimal").strip().lower()
    if mode not in CAPTURES:
        mode = "minimal"
    letters = "".join((chars or "").split())
    if mode == "freeform" and not letters:
        return "Type the letters in the order they were written, then upload the photo again."
    if not images:
        return "Add a handwriting photo first."

    smooth_value = max(0.0, min(2.0, float(smooth)))
    weight_value = max(-2.0, min(2.0, float(weight)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="drawfont-") as temp:
        root = Path(temp)
        photos: list[str] = []
        for index, (filename, raw) in enumerate(images, start=1):
            if not raw:
                continue
            path = root / f"page-{index:02d}{_suffix(filename, raw)}"
            path.write_bytes(raw)
            photos.append(str(path))
        if not photos:
            return "Add a handwriting photo first."
        work = root / "work"
        out_base = root / "ProfileHand"
        args = [
            "make",
            *photos,
            "--name",
            "Profile Hand",
            "--formats",
            "ttf,woff2",
            "--smooth",
            f"{smooth_value:g}",
            f"--weight={weight_value:g}",
            "-d",
            str(work),
            "-o",
            str(out_base),
        ]
        if mode == "freeform":
            args.extend(["--chars", letters])
        else:
            args.extend(["--charset", mode])
        try:
            _run(args, root)
        except Exception as exc:
            log.warning("draw-your-font conversion failed: %s", exc)
            return f"The photo was not converted ({exc})."
        built = out_base.with_suffix(".ttf")
        if not built.is_file() or built.stat().st_size < 64:
            return "draw-your-font finished without a font file."
        dest.write_bytes(built.read_bytes())
        web = out_base.with_suffix(".woff2")
        if web.is_file():
            dest.with_suffix(".woff2").write_bytes(web.read_bytes())
    return None


def _run(args: list[str], cwd: Path) -> None:
    npx = _which("npx")
    if npx is None:
        raise RuntimeError("npx was not found. Install Node.js 18 or newer.")
    command = [npx, "--yes", PACKAGE, *args]
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
            shell=os.name == "nt",
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("draw-your-font took too long and was stopped.") from exc
    except OSError as exc:
        raise RuntimeError(f"draw-your-font could not be started ({exc}).") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip()
        lines = [line.strip() for line in detail.splitlines() if line.strip()]
        message = " ".join(lines[-4:])[:400] or "draw-your-font failed."
        raise RuntimeError(message)


def _node_version() -> str | None:
    node = _which("node")
    if node is None:
        return None
    try:
        completed = subprocess.run(
            [node, "--version"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (completed.stdout or completed.stderr or "").strip().split()
    return text[0] if text else None


def _major(version: str | None) -> int:
    if not version:
        return 0
    digits = "".join(ch if ch.isdigit() else " " for ch in version).split()
    return int(digits[0]) if digits else 0


def _which(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        return shutil.which(f"{name}.cmd") or shutil.which(f"{name}.exe")
    return None


def _suffix(filename: str, raw: bytes) -> str:
    for magic, ext in IMAGE_MAGIC:
        if raw.startswith(magic):
            return ext
    ext = Path(filename).suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        return ".jpg" if ext == ".jpeg" else ext
    return ".png"
