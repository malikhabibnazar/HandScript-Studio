# HandScript Studio — Setup Guide for Mac

This guide shows how to run HandScript Studio on a Mac. Follow the steps in order. You only need the tools in **Before you start**. Everything after **Open the app** is optional.

HandScript Studio is a local web app. It creates printable 4×6 cards and #10 envelopes from templates and handwriting styles. You use it in a browser. Nothing in this guide publishes the app to the internet.

The same steps work on Apple silicon (M1, M2, M3, M4) and on Intel Macs. Install the Apple silicon build of each program when your Mac uses an M-series chip.

## What you will open

| What | Address | Used for |
|---|---|---|
| The app | http://localhost:3000 | Cards, templates, batches, downloads |
| The API | http://127.0.0.1:8000 | The service the app talks to |
| API status | http://127.0.0.1:8000/health | A quick check that the API is running |

There are two ways to run it. Pick one.

- **On this Mac.** Best for everyday use. You start the API in one window and the website in another.
- **With Docker.** Starts the website, API, database, file storage, and background worker together. Use this when you want the full stack in one command.

Do not run both at the same time. They use the same addresses, and the second start will fail.

---

## Before you start

Install these four programs.

1. **Homebrew**, if you do not already have it — https://brew.sh/
   Homebrew is the simplest way to install Python, Node.js, and Git on a Mac.
2. **Python 3.12 or newer, Node.js 22, and Git:**

```bash
brew install python@3.12 node@22 git
```

If `node` or `python3.12` is not found after that, follow the “add to your PATH” lines Homebrew prints, then open a new Terminal window.

3. **Docker Desktop for Mac** — https://www.docker.com/products/docker-desktop/
   Choose the Apple silicon or Intel installer to match your Mac. Required only for the Docker option and for the HandFonted handwriting service. You can install it later.

Open **Terminal** and check the versions:

```bash
python3 --version
node --version
npm --version
git --version
docker --version
```

You want Python `3.12` or higher, and `v22` (or at least `v20`) for Node. On a Mac the command is `python3`, not `python`.

---

## 1. Open the project folder

If you received a zip file, double-click it to unpack it. The folder must contain `api`, `web`, and `docker-compose.yml`.

If you have a Git link, clone it, then go into the folder:

```bash
git clone <the repository link you were given>
cd HandScript-Studio
```

If the folder is already on your Mac, move into it. Example when it sits on the Desktop:

```bash
cd ~/Desktop/HandScript-Studio
```

Every later command assumes this folder is your current folder, unless a step says to enter `api` or `web`.

---

## 2. Run it on this Mac

Use two Terminal windows. Leave both open while you use the app. **Terminal → New Window** opens the second one (or press Command-N).

### Window 1 — the API

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The first `pip install` can take a few minutes. When the API is ready, the window shows:

```text
Uvicorn running on http://127.0.0.1:8000
```

Leave this window running. The line `(.venv)` at the start of the prompt means the API’s Python environment is active. After you activate it, the `python` command points at that environment.

The API stores its database and generated files in `api/data`. That folder is created on first launch. You do not need PostgreSQL, Redis, or MinIO for this option. A background worker runs inside the API and processes batches.

### Window 2 — the website

Open a second Terminal window, go to the project folder again, then:

```bash
cd web
npm install
npm run dev
```

`npm install` is only required the first time, or after the project files change. When the website is ready, the window shows a local address, normally http://localhost:3000.

### Open the app

In a browser, go to:

http://localhost:3000

The first visit is a short setup. Choose **Skip** to open the sample workspace. To produce a real PDF or PNG, open **Batch Generator** and start a batch with a CSV file.

Check the API on its own at http://127.0.0.1:8000/health. A healthy local setup reports SQLite, local disk, and an embedded worker.

### The next time you start it

You do not install again. Open two windows.

API:

```bash
cd api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Website:

```bash
cd web
npm run dev
```

### Stop it

Click each window and press **Control-C**. Closing the window also stops that part.

---

## 3. Settings file (optional)

The API runs with sensible defaults, so you can skip this until you need to change something.

From the project folder:

```bash
cd api
cp .env.example .env
```

Edit `api/.env` in a text editor. Useful values:

| Setting | What it does |
|---|---|
| `HANDWRITING_ENGINE` | `graves` uses the local handwriting model when its weights are installed. `font` uses a script font. |
| `GEMINI_API_KEY` | Required only for the HandwritingAgent profile. Leave it empty otherwise. |
| `GEMINI_MODEL` | Model name sent to Gemini. Default is `gemini-3.1-pro-preview`. |
| `ONEDM_ENABLED` | `true` shows the One-DM handwriting option. |
| `ONEDM_DEVICE` | `auto` or `cpu` on a Mac. |
| `CORS_ORIGINS` | Must include `http://localhost:3000` so the website can call the API. |

Save the file, then stop the API with **Control-C** and start it again. Settings are read when the API starts.

This file applies when you run the API yourself. The Docker stack uses the settings inside `docker-compose.yml` instead.

---

## 4. Handwriting options (optional)

The app can draw cards without any of these. If a model file is missing, it uses a bundled handwriting font and the batch still finishes.

### Graves handwriting model

In the API window, with `(.venv)` active and the API stopped:

```bash
cd api
source .venv/bin/activate
python -m app.handwriting.download
```

This downloads the published checkpoint and writes:

- `api/data/graves/weights.npz`
- style files under `api/data/graves/styles`

Start the API again. http://127.0.0.1:8000/health should report `engine: Graves LSTM`.

### One-DM (one photo of your handwriting)

On a Mac, One-DM runs on the CPU. DirectML is a Windows feature, and current Macs do not use NVIDIA CUDA.

With the API environment active:

```bash
cd api
source .venv/bin/activate
pip install torch torchvision
python -m app.handwriting.onedm.setup_onedm
```

The setup command checks Python, creates `api/data/onedm/weights` and `api/data/onedm/samples`, and writes a test image.

The pretrained checkpoint is published by the One-DM authors: https://github.com/dailenson/One-DM

Place the checkpoint file at:

```text
api/data/onedm/weights/epoch-ckpt.pt
```

In the app, open **Handwriting Profiles**, choose **One-DM (Diffusion)**, and upload one photo or one line of handwriting. Generation is slower on CPU than on a Windows GPU.

### HandwritingAgent (Gemini)

In `api/.env`, set `GEMINI_API_KEY` to your key. Restart the API. In a handwriting profile, choose **HandwritingAgent**. That profile sends the handwriting photo and the card text to Gemini and uses the returned pen strokes.

### HandFonted (separate handwriting service)

HandFonted runs in Docker so its machine-learning libraries stay out of the API. Start **Docker Desktop** and wait until it says it is running. From the project folder:

```bash
docker compose up -d --build handfonted
```

The first build downloads a large image and can take a long time. The API reaches it at http://127.0.0.1:8010. In the app, create a profile with the HandFonted option, upload one alphabet photo, correct the letters, generate the font, then preview a sentence.

Stop only that service with:

```bash
docker compose stop handfonted
```

### Personal fonts from a specimen sheet

The Handwrite, hw2font, and font-maker profiles also need Potrace and FontForge:

```bash
brew install potrace fontforge
potrace --version
fontforge --version
```

Without them, those profiles report that the tools are missing. The other handwriting options do not need them.

---

## 5. Run the full stack with Docker

This starts PostgreSQL, Redis, MinIO (file storage), the API, the batch worker, the website, and HandFonted.

1. Start **Docker Desktop** and wait until it is running.
2. Quit any local API or website windows from section 2. They use ports 3000 and 8000.
3. From the project folder:

```bash
docker compose up --build
```

The first build is slow, especially HandFonted. Later starts are faster. When the logs settle, open http://localhost:3000.

Give Docker Desktop enough memory in **Settings → Resources** if the first build is killed. 6 GB or more is a comfortable setting for this stack.

To run it in the background and get the prompt back:

```bash
docker compose up --build -d
```

Follow the logs:

```bash
docker compose logs -f
```

Press **Control-C** to stop following logs. That does not stop the containers. Stop the stack with:

```bash
docker compose down
```

That keeps the database and generated files. To stop and delete them as well:

```bash
docker compose down -v
```

Useful addresses while Docker is running:

| Address | What it is |
|---|---|
| http://localhost:3000 | The app |
| http://127.0.0.1:8000/health | API status. Expect PostgreSQL, S3, and a Redis worker. |
| http://localhost:9001 | MinIO console. User `handscript`, password `handscriptsecret`. |

These passwords are for the local Docker stack on your Mac. They are not a public deployment.

The Docker images do not include the Graves weight file. Cards still render with the script font. To use Graves inside Docker, download the weights with section 4 first, then add this line under `volumes` for both the `api` service and the `worker` service in `docker-compose.yml`:

```yaml
- ./api/data/graves:/app/data/graves
```

Save the file and start the stack again with `docker compose up --build`.

---

## 6. If something does not start

**`python3` is not recognized.** Install it with `brew install python@3.12`, then open a new Terminal window.

**`npm` is not recognized.** Install it with `brew install node@22`, then open a new Terminal window.

**`source .venv/bin/activate` says no such file.** Create the environment first with `python3 -m venv .venv` from the `api` folder.

**Port 3000 or 8000 is already in use.** Another copy is still running. Press **Control-C** in the old windows, or stop Docker with `docker compose down`. Then start again.

**The website opens but cannot reach the API.** Confirm the API window is still running and http://127.0.0.1:8000/health loads. `CORS_ORIGINS` in `api/.env` must include `http://localhost:3000`.

**`docker` is not recognized, or compose says it cannot connect.** Open Docker Desktop and wait until the engine is running. On a new Mac, finish Docker’s first-launch permission prompts.

**A handwriting model is missing.** The API logs a warning and draws with the script font. The batch still completes. Install the weights in section 4 only if you want that model.

**The first Docker build fails partway through.** Run the same `docker compose up --build` command again. Large downloads sometimes need a second attempt.
