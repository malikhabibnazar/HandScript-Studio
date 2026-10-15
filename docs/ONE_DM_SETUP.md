# One-DM Diffusion Engine Setup Guide (AMD RX 580 & Windows)

This guide provides instructions for setting up and running **One-DM** (*One-Shot Diffusion Mimicker for Handwritten Text Generation*, ECCV 2024) in **HandScript Studio**.

---

## 1. Hardware Compatibility: AMD Radeon RX 580 8GB

### Can it run on AMD Radeon RX 580 8GB?
**YES.** 
* **VRAM:** The RX 580 has **8 GB GDDR5 VRAM**, which is sufficient to hold the One-DM diffusion generator and ResNet-18 style encoder in memory for single-card and batch generation.
* **Acceleration on Windows:** AMD GPUs do not use NVIDIA CUDA. Instead, PyTorch accelerates on the RX 580 using **DirectML (`torch-directml`)**, Microsoft’s DirectX 12 hardware acceleration backend for Windows.
* **Fallback:** If DirectML is not installed, the engine automatically falls back to **CPU execution**, ensuring it runs reliably on any machine.

---

## 2. Quickstart for AI Agents & Developers

When you clone this repository, run the following commands in PowerShell or terminal:

### Step 1: Activate API Environment
```powershell
cd api
# Activate existing virtual environment, or create one:
# python -m venv .venv
.venv\Scripts\activate
```

### Step 2: Install PyTorch & DirectML (for AMD RX 580)
```powershell
# Install PyTorch and DirectML for AMD GPU acceleration on Windows:
pip install torch torchvision torch-directml
```
*(If running on an NVIDIA GPU machine instead, install standard CUDA PyTorch: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118`)*

### Step 3: Run the Automated Setup & Test Script
```powershell
python -m app.handwriting.onedm.setup_onedm
```
This automated command will:
1. Verify Python & PyTorch versions.
2. Detect your **AMD Radeon RX 580 (DirectML)** or NVIDIA CUDA device.
3. Create necessary folders (`api/data/onedm/weights/` and `api/data/onedm/samples/`).
4. Generate a test handwriting render (`test_card_render.png`) to confirm end-to-end rendering pipeline works.

---

## 3. Pretrained Model Weights

The ECCV 2024 One-DM weights are published by the authors at:
- **Repository:** [https://github.com/dailenson/One-DM](https://github.com/dailenson/One-DM)
- **Checkpoints:** IAM / English finetuned weights (`epoch-ckpt.pt` or `iam64.pt`)

### Where to place weights:
Place the checkpoint file here:
```
api/data/onedm/weights/epoch-ckpt.pt
```

*(If the weight file is not yet downloaded, HandScript Studio gracefully falls back to high-fidelity cursive synthesis so you can still create cards, test UI layouts, and preview templates without server crashes).*

---

## 4. How to Generate Cards with One-DM

1. **Start the API:**
   ```powershell
   cd api
   .venv\Scripts\activate
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start the Web App:**
   ```powershell
   cd web
   npm run dev
   ```

3. **In the Web Interface (http://localhost:3000):**
   * Go to **Handwriting Profiles** (`/handwriting`).
   * Select or create a profile, and choose the renderer: **One-DM (Diffusion)**.
   * Upload **a single photo or scan of your handwriting** (one word or one line is enough!).
   * Open any template (e.g., 4×6 Thank You Card), click **Preview** or run a **Batch**, and the card will be drawn matching your uploaded handwriting style!

---

## 5. Configuration Options (`api/.env`)

| Variable | Default | Description |
|---|---|---|
| `ONEDM_ENABLED` | `true` | Enables the One-DM diffusion engine option. |
| `ONEDM_WEIGHTS_PATH` | `./data/onedm/weights/epoch-ckpt.pt` | Path to downloaded checkpoint. |
| `ONEDM_DEVICE` | `auto` | `auto` (auto-detects DirectML for RX 580, CUDA, or CPU), or explicitly `directml`, `cuda`, `cpu`. |
