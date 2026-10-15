"""Setup and verification tool for One-DM on HandScript Studio.

Designed for AMD Radeon RX 580 8GB (via DirectML), NVIDIA GPUs (via CUDA), and CPU.
Run with:
    cd api
    python -m app.handwriting.onedm.setup_onedm
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def ensure_sample_asset() -> Path:
    onedm_dir = Path(__file__).parent
    sample_path = onedm_dir / "default_sample.png"
    if not sample_path.exists():
        img = Image.new("RGB", (600, 160), color=(250, 248, 245))
        draw = ImageDraw.Draw(img)
        # Draw some realistic cursive-like test strokes
        draw.text((30, 50), "Hello from One-DM Handwriting", fill=(25, 25, 30))
        img.save(sample_path)
    return sample_path

def main() -> None:
    print("=" * 60)
    print("HandScript Studio: One-DM Setup & Hardware Check")
    print("Paper: ECCV 2024 - One-Shot Diffusion Mimicker")
    print("=" * 60)

    # 1. Python version
    print(f"\n[1] Python Version: {sys.version.split()[0]}")

    # 2. Check Torch & Hardware Acceleration
    print("\n[2] Checking Acceleration & GPU Compatibility...")
    torch_installed = False
    try:
        import torch
        torch_installed = True
        print(f"    PyTorch Version: {torch.__version__}")
    except ImportError:
        print("    PyTorch is NOT installed.")
        print("    Install via: pip install torch torchvision")

    # 3. Check AMD Radeon RX 580 / DirectML Support
    print("\n[3] Checking AMD Radeon RX 580 Support (DirectML)...")
    try:
        import torch_directml
        if torch_directml.is_available():
            dml_device = torch_directml.device()
            dev_name = torch_directml.device_name(0)
            print(f"    [SUCCESS] DirectML is ACTIVE!")
            print(f"    Detected GPU: {dev_name}")
            print(f"    Target Device: {dml_device}")
            print("    AMD Radeon RX 580 8GB can accelerate One-DM over DirectX 12!")
        else:
            print("    torch-directml is installed, but no DirectML device reported.")
    except ImportError:
        print("    torch-directml is NOT installed.")
        print("    To run on AMD Radeon RX 580 8GB using DirectX 12 GPU acceleration:")
        print("    --> Run: pip install torch-directml")

    # 4. Check NVIDIA CUDA
    print("\n[4] Checking NVIDIA CUDA Support...")
    if torch_installed:
        import torch
        if torch.cuda.is_available():
            print(f"    [SUCCESS] NVIDIA CUDA is ACTIVE: {torch.cuda.get_device_name(0)}")
        else:
            print("    NVIDIA CUDA is not available on this machine (standard for AMD systems).")

    # 5. Check Folders & Weights
    repo_root = Path(__file__).resolve().parents[3]
    weights_dir = repo_root / "data" / "onedm" / "weights"
    samples_dir = repo_root / "data" / "onedm" / "samples"
    weights_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)
    ensure_sample_asset()

    weights_file = weights_dir / "epoch-ckpt.pt"
    print(f"\n[5] Model Weights Status:")
    print(f"    Folder: {weights_dir}")
    if weights_file.exists():
        print(f"    [FOUND] Model weights found at: {weights_file}")
    else:
        print(f"    [INFO] Model weights file not found: {weights_file}")
        print("    You can download the pretrained ECCV 2024 One-DM weights from the official repo:")
        print("    https://github.com/dailenson/One-DM")
        print("    Place `epoch-ckpt.pt` inside: api/data/onedm/weights/")

    # 6. Test Card Render Output
    print("\n[6] Testing One-DM Card Render...")
    try:
        from app.handwriting.onedm_engine import OneDMEngine
        engine = OneDMEngine(weights_file)
        card_img = engine.render_line(
            "Thank You for your Kindness!",
            style_id=None,
            bias=0.75,
            variation=0.15,
            font_size_pt=24,
            dpi=300,
            seed=42,
            max_width_px=1200,
            max_height_px=200,
        )
        test_out = samples_dir / "test_card_render.png"
        card_img.save(test_out)
        print(f"    [SUCCESS] Test card line rendered and saved to: {test_out}")
    except Exception as exc:
        print(f"    Render check error: {exc}")

    print("\n" + "=" * 60)
    print("Setup Verification Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
