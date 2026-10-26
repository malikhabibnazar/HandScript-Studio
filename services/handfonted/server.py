"""HandFonted service.

Loads the detector and the letter model once, then turns one handwriting
photo into reviewed glyphs and a TrueType font. The studio API calls this
over HTTP. Paddle and this copy of PyTorch stay in this process.
"""
from __future__ import annotations

import base64
import os
import sys
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
os.environ.setdefault("FLAGS_use_mkldnn", "0")

ROOT = Path(os.environ.get("HANDFONTED_ROOT", "/opt/handfonted/HandFonted"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image
from pydantic import BaseModel, Field
from torchvision import transforms

from character_classification import ResInceptionNet, assign_classes, pad_image_to_square
from character_segmentation import segment_characters
from font_creation import update_font_from_images

# 0-9 then A-Z then a-z. This is the EMNIST ByClass order the retrained head uses.
CLASSES = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz")
_WEIGHTS = Path(os.environ.get(
    "HANDFONTED_WEIGHTS",
    "/opt/handfonted/weights/resinception_byclass62.pth",
))
_lock = threading.Lock()
_detector = None
_classifier = None
_ready = False
_message = "Models are loading."

_TRANSFORM = transforms.Compose([
    transforms.Resize((28, 28)),
    transforms.ToTensor(),
    transforms.Normalize((0.1751,), (0.3332,)),
])


def _load() -> None:
    global _detector, _classifier, _ready, _message
    from paddleocr import TextDetection

    weights = _WEIGHTS
    detector_dir = ROOT / "resources" / "PP-OCRv5_mobile_det_infer"
    if not weights.is_file() or not detector_dir.is_dir():
        _message = "The digit-and-letter weights or the text detector are missing."
        return
    classifier = ResInceptionNet(num_classes=len(CLASSES))
    classifier.load_state_dict(torch.load(weights, map_location=torch.device("cpu"), weights_only=True))
    classifier.eval()
    detector = TextDetection(
        model_name="PP-OCRv5_mobile_det",
        model_dir=str(detector_dir),
        enable_mkldnn=False,
    )
    _classifier = classifier
    _detector = detector
    _ready = True
    _message = "HandFonted is ready."


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load()
    yield


app = FastAPI(title="HandFonted", version="1.0.0", lifespan=lifespan)


class FontGlyph(BaseModel):
    label: str
    image_png_base64: str


class FontRequest(BaseModel):
    font_name: str = "My Handwriting"
    thickness: int = Field(default=100, ge=20, le=220)
    characters: list[FontGlyph]


@app.get("/health")
def health():
    body = {"ready": _ready, "message": _message, "classes": "".join(CLASSES)}
    if not _ready:
        return JSONResponse(status_code=503, content=body)
    return body


@app.post("/v1/process")
async def process(image: UploadFile = File(...)) -> dict:
    if not _ready or _detector is None or _classifier is None:
        raise HTTPException(status_code=503, detail=_message)
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image")
    with _lock:
        crops = _segment(raw)
        if not crops:
            raise HTTPException(status_code=422, detail="No characters were found. Use a dark pen and keep the characters apart.")
        characters = _label_all(crops)
    return {"characters": characters}


@app.post("/v1/font")
def font(body: FontRequest) -> Response:
    if not _ready:
        raise HTTPException(status_code=503, detail=_message)
    pairs = _pairs(body.characters)
    if not pairs:
        raise HTTPException(status_code=400, detail="Keep at least one character before generating the font.")
    base = ROOT / "resources" / "Arimo-Regular.ttf"
    with tempfile.TemporaryDirectory(prefix="handfonted-") as temp:
        dest = Path(temp) / "font.ttf"
        with _lock:
            update_font_from_images(
                font_path=str(base),
                char_image_list=pairs,
                output_path=str(dest),
                desired_thickness=body.thickness,
                new_family_name=body.font_name.strip() or "My Handwriting",
                new_style_name="Regular",
            )
        if not dest.is_file() or dest.stat().st_size < 64:
            raise HTTPException(status_code=422, detail="The font was not created from these letters.")
        data = dest.read_bytes()
    return Response(content=data, media_type="font/ttf")


def _segment(raw: bytes) -> list:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        handle.write(raw)
        path = handle.name
    try:
        return segment_characters(path, det_model=_detector) or []
    finally:
        Path(path).unlink(missing_ok=True)


def _threshold(crop: np.ndarray) -> np.ndarray:
    """Ink mask. Otsu keeps the solid center of a thick stroke; adaptive keeps thin edges.

    Adaptive thresholding alone hollows a filled pen stroke, because the middle
    of the stroke is no darker than the pixels around it.
    """
    gray = crop if crop.ndim == 2 else cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    _, solid = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    edges = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 5,
    )
    return cv2.bitwise_or(solid, edges)


def _encode_png(image: np.ndarray) -> str | None:
    ok, encoded = cv2.imencode(".png", image)
    if not ok:
        return None
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def _label_all(crops: list) -> list[dict]:
    originals: list[np.ndarray] = []
    tensors = []
    for crop in crops:
        thresh = _threshold(crop)
        square = pad_image_to_square(thresh, extra_padding_amount=1)
        tensors.append(_TRANSFORM(Image.fromarray(square)))
        originals.append(thresh)
    batch = torch.stack(tensors)
    assert _classifier is not None
    with torch.inference_mode():
        probabilities = torch.softmax(_classifier(batch), dim=1).cpu()
    sample_index, confidence, class_index = assign_classes(probabilities)
    chosen: dict[int, tuple[str, float]] = {}
    for sample, score, klass in zip(sample_index.tolist(), confidence.tolist(), class_index.tolist()):
        chosen[int(sample)] = (CLASSES[int(klass)], float(score))
    characters = []
    for index, image in enumerate(originals):
        if index in chosen:
            label, score = chosen[index]
        else:
            top = int(torch.argmax(probabilities[index]).item())
            label, score = CLASSES[top], float(probabilities[index, top].item())
        encoded = _encode_png(image)
        if encoded is None:
            continue
        characters.append({
            "label": label,
            "confidence": round(score, 4),
            "image_png_base64": encoded,
        })
    return characters


@app.post("/v1/crop")
async def crop(image: UploadFile = File(...)) -> dict:
    """Segment one uploaded character and return its ink, without classifying it."""
    if not _ready or _detector is None:
        raise HTTPException(status_code=503, detail=_message)
    raw = await image.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty image")
    with _lock:
        crops = _segment(raw)
        if len(crops) != 1:
            detail = (
                "Upload an image that contains only that one character."
                if crops
                else "No character was found. Upload an image that contains only that one character."
            )
            raise HTTPException(status_code=422, detail=detail)
        encoded = _encode_png(_threshold(crops[0]))
    if not encoded:
        raise HTTPException(status_code=422, detail="The character image could not be read.")
    return {"image_png_base64": encoded}


def _pairs(characters: list[FontGlyph]) -> list[tuple[str, np.ndarray]]:
    seen: set[str] = set()
    pairs: list[tuple[str, np.ndarray]] = []
    for item in characters:
        label = (item.label or "").strip()
        if len(label) != 1 or label in seen:
            continue
        raw = base64.b64decode(item.image_png_base64)
        image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None or image.size == 0:
            continue
        seen.add(label)
        pairs.append((label, image))
    return pairs
