# HandScript Studio

Web application for generating printable 4×6 cards and #10 envelopes from editable templates and handwriting profiles.

The interface is **Next.js**. The API, database, file storage and batch worker are **Python / FastAPI**. Pages are drawn at the template's real physical size. Handwriting is a local Graves LSTM when its weights are installed, and a script font otherwise. PDF and PNG use the same pixels.

## Stack

| Layer | Local development | Full stack (Docker) |
|---|---|---|
| UI | Next.js, React, Konva | same |
| API | FastAPI | same |
| Database | SQLite | PostgreSQL |
| Files | Local folder | S3-compatible (MinIO) |
| Batch worker | In-process thread | Separate worker + Redis |

The service boundaries match the original studio: profiles, templates, documents, imports, batches, exports and settings.

## Run locally

Two terminals.

```bash
cd api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

```bash
cd web
npm install
npm run dev
```

Open http://localhost:3000. The API is http://127.0.0.1:8000.

The first launch shows a short setup. Skip it to open the sample workspace. Start a batch from **Batch Generator** with a CSV to render real PDF or PNG files.

## Handwriting engine

`HANDWRITING_ENGINE=graves` (the default) draws text with a local Graves LSTM + mixture density network, the same architecture as [sjvasquez/handwriting-synthesis](https://github.com/sjvasquez/handwriting-synthesis). That path stays on this machine. `HANDWRITING_ENGINE=font` keeps the script-font renderer.

Each handwriting profile chooses its own renderer:
- **One-DM (Diffusion)**: Implements [dailenson/One-DM](https://github.com/dailenson/One-DM) (*One-Shot Diffusion Mimicker*, ECCV 2024). It needs only a single reference photo or line of your handwriting, extracting high-frequency style features and synthesizing text cards using diffusion. Supports **AMD Radeon RX 580 8GB** via PyTorch DirectML (`torch-directml`), NVIDIA GPUs via CUDA, and CPU fallback. Setup guide: [docs/ONE_DM_SETUP.md](file:///c:/Users/Malik%20Abdullah/Desktop/HandScript-Studio/docs/ONE_DM_SETUP.md). Run `python -m app.handwriting.onedm.setup_onedm` to verify.
- **HandwritingAgent**: Sends the profile’s handwriting photo and the exact card text to Gemini. It asks for `GEMINI_MODEL` first (default `gemini-3.1-pro-preview`) and accepts replies only when pen strokes are returned.
- **Graves AI**: Uses a local Graves LSTM with built-in style primers (`style_id`), `bias`, and `variation`.
- **Handwriting font**: Draws locally with bundled handwriting faces (Caveat, Homemade Apple, Patrick Hand, Kalam, Sacramento, or Architects Daughter).
- **Handwrite / hw2font / Font maker**: Turn filled specimen sheets into personal fonts using Potrace and FontForge.

Install the pretrained weights once. The download converts the published checkpoint to a NumPy file. TensorFlow is not required.

```bash
cd api
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.handwriting.download
```

That writes `api/data/graves/weights.npz` and the style primers. Restart the API. Health should report `engine: Graves LSTM`.

Generate one 4×6 card: open a document such as the thank-you card, use **Preview**, or run a one-row CSV batch and download the PDF. A 4×6 page is 6 by 4 inches (1800×1200 px at 300 dpi). A #10 envelope is 9.5 by 4.125 inches.

If the weight file is missing, the API logs a warning and renders with the script font so batches still finish.

## Run the full stack

```bash
docker compose up --build
```

That starts PostgreSQL, Redis, MinIO, the API, the worker and the web app. The image does not contain the Graves checkpoint. Mount `api/data/graves` into the API and worker at `/app/data/graves`, or leave it out and both processes use the script font.

## Tests

```bash
cd api
python -m pytest
```

## Desktop UI

The earlier PySide6 interface is still in this repository (`app.py`, `ui/`, `services/`). It is a separate frontend over mock data. The supported product is the web studio above.
