"""Retrain ResInceptionNet so the same photo pipeline can label digits.

The shipped checkpoint has 52 letter outputs. This copies that backbone, adds
0-9, and fine-tunes on EMNIST ByClass. Images are turned upright before
training so they match the white-ink crops the service sends to the model.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import transforms
from torchvision.datasets import EMNIST

from character_classification import ResInceptionNet

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
FALLBACK_CLASSES = "0123456789" + LETTERS
MIRRORS = (
    "https://biometrics.nist.gov/cs_links/EMNIST/gzip.zip",
    "http://www.itl.nist.gov/iaui/vip/cs_links/EMNIST/gzip.zip",
)


def _apply_orient(img: Image.Image, mode: str) -> Image.Image:
    if mode == "as_is":
        return img
    if mode == "transpose":
        return img.transpose(Image.TRANSPOSE)
    if mode == "rot90":
        return img.transpose(Image.ROTATE_90)
    if mode == "rot270":
        return img.transpose(Image.ROTATE_270)
    if mode == "rot90_hflip":
        return img.transpose(Image.ROTATE_90).transpose(Image.FLIP_LEFT_RIGHT)
    if mode == "rot270_hflip":
        return img.transpose(Image.ROTATE_270).transpose(Image.FLIP_LEFT_RIGHT)
    if mode == "hflip":
        return img.transpose(Image.FLIP_LEFT_RIGHT)
    if mode == "vflip":
        return img.transpose(Image.FLIP_TOP_BOTTOM)
    raise ValueError(mode)


class Orient:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def __call__(self, img: Image.Image) -> Image.Image:
        return _apply_orient(img, self.mode)


def ensure_emnist(root: Path) -> None:
    marker = root / "EMNIST" / "raw" / "emnist-byclass-train-images-idx3-ubyte"
    if marker.is_file():
        return
    last_error: Exception | None = None
    for url in MIRRORS:
        EMNIST.url = url
        print(f"downloading EMNIST from {url}")
        try:
            EMNIST(str(root), split="byclass", train=True, download=True)
            return
        except Exception as exc:
            last_error = exc
            print(f"download failed: {exc}")
    raise SystemExit(f"Could not download EMNIST. Last error: {last_error}")


def balanced_indices(
    targets: torch.Tensor,
    per_class: int,
    seed: int,
    digit_per_class: int | None = None,
) -> list[int]:
    buckets: list[list[int]] = [[] for _ in range(62)]
    for index, label in enumerate(targets.tolist()):
        buckets[int(label)].append(index)
    rng = random.Random(seed)
    chosen: list[int] = []
    caps: list[int] = []
    for label, bucket in enumerate(buckets):
        wanted = digit_per_class if digit_per_class and label < 10 else per_class
        cap = min(wanted, len(bucket))
        caps.append(cap)
        rng.shuffle(bucket)
        chosen.extend(bucket[:cap])
    print(
        f"using {min(caps[:10])}–{max(caps[:10])} digit images and "
        f"{min(caps[10:])}–{max(caps[10:])} letter images per class",
        flush=True,
    )
    rng.shuffle(chosen)
    return chosen


def build_model(init_path: Path) -> ResInceptionNet:
    old = ResInceptionNet(num_classes=52)
    old.load_state_dict(torch.load(init_path, map_location="cpu", weights_only=True))
    model = ResInceptionNet(num_classes=62)
    copied = model.state_dict()
    source = old.state_dict()
    for key, value in source.items():
        if key.startswith("fc."):
            continue
        copied[key] = value
    # Old head is A-Z then a-z. New head is 0-9, then A-Z, then a-z.
    copied["fc.weight"][10:36] = source["fc.weight"][:26]
    copied["fc.weight"][36:62] = source["fc.weight"][26:]
    copied["fc.bias"][10:36] = source["fc.bias"][:26]
    copied["fc.bias"][36:62] = source["fc.bias"][26:]
    model.load_state_dict(copied)
    return model


def accuracy(model: nn.Module, loader: DataLoader) -> dict[str, float]:
    model.eval()
    correct = torch.zeros(62)
    total = torch.zeros(62)
    with torch.inference_mode():
        for images, labels in loader:
            predicted = model(images).argmax(dim=1)
            for label in range(62):
                mask = labels == label
                total[label] += int(mask.sum())
                correct[label] += int((predicted[mask] == label).sum())
    per = correct / total.clamp(min=1)
    return {
        "all": float((correct.sum() / total.sum()).item()),
        "zero": float(per[0]),
        "one": float(per[1]),
        "digits": float(per[:10].mean()),
        "upper": float(per[10:36].mean()),
        "lower": float(per[36:].mean()),
    }


def run(args: argparse.Namespace) -> None:
    torch.set_num_threads(args.threads)
    if args.resume:
        model = ResInceptionNet(num_classes=62)
        model.load_state_dict(torch.load(args.resume, map_location="cpu", weights_only=True))
        print(f"resumed {args.resume}", flush=True)
    else:
        model = build_model(Path(args.init))
    root = Path(args.data)
    root.mkdir(parents=True, exist_ok=True)
    ensure_emnist(root)
    # EMNIST stores each glyph rotated and mirrored. This is the upright form
    # (checked on 3, y, and g from the training split).
    mode = "rot270_hflip"
    print(f"orientation {mode}", flush=True)
    train_tf = transforms.Compose([
        Orient(mode),
        transforms.RandomAffine(degrees=10, translate=(0.08, 0.08), scale=(0.9, 1.1), fill=0),
        transforms.ToTensor(),
        transforms.Normalize((0.1751,), (0.3332,)),
    ])
    val_tf = transforms.Compose([
        Orient(mode),
        transforms.ToTensor(),
        transforms.Normalize((0.1751,), (0.3332,)),
    ])
    train_set = EMNIST(str(root), split="byclass", train=True, download=False, transform=train_tf)
    classes = "".join(train_set.classes)
    if classes != FALLBACK_CLASSES:
        raise SystemExit(f"EMNIST class order was {classes!r}")
    val_set = EMNIST(str(root), split="byclass", train=False, download=False, transform=val_tf)
    train_loader = DataLoader(
        Subset(train_set, balanced_indices(
            train_set.targets, args.per_class, seed=1, digit_per_class=args.digit_per_class,
        )),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
    )
    val_loader = DataLoader(
        Subset(val_set, balanced_indices(val_set.targets, args.val_per_class, seed=2)),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
    )
    head = [param for name, param in model.named_parameters() if name.startswith("fc.")]
    backbone = [param for name, param in model.named_parameters() if not name.startswith("fc.")]
    opt = torch.optim.AdamW([
        {"params": backbone, "lr": args.backbone_lr},
        {"params": head, "lr": args.head_lr},
    ], weight_decay=1e-4)
    class_weight = torch.ones(62)
    if args.digit_per_class:
        # 0/O and 1/l are the pairs this head still mixes up.
        for char, penalty in (("0", 3.0), ("1", 3.0), ("O", 2.0), ("o", 2.0), ("I", 2.0), ("l", 2.0), ("L", 2.0)):
            class_weight[FALLBACK_CLASSES.index(char)] = penalty
    loss_fn = nn.CrossEntropyLoss(weight=class_weight, label_smoothing=0.05)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    best = 0.0
    best_digits = 0.0
    meta_path = out.with_suffix(".json")
    if args.resume and meta_path.is_file():
        previous = json.loads(meta_path.read_text(encoding="utf-8"))
        best = float(previous.get("val_macro") or 0)
        best_digits = float(previous.get("digits") or 0)
    stale = 0
    for epoch in range(1, args.epochs + 1):
        train_head_only = epoch == 1 and not args.resume
        for param in backbone:
            param.requires_grad = not train_head_only
        model.train()
        seen = 0
        running = 0.0
        for step, (images, labels) in enumerate(train_loader, start=1):
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(images), labels)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            seen += int(labels.shape[0])
            running += float(loss.item()) * int(labels.shape[0])
            if step % 50 == 0:
                print(f"epoch {epoch} step {step} loss {running / seen:.4f}", flush=True)
        scores = accuracy(model, val_loader)
        print(
            f"epoch {epoch} train_loss {running / max(seen, 1):.4f} "
            f"val {scores['all']:.4f} digits {scores['digits']:.4f} "
            f"0 {scores['zero']:.4f} 1 {scores['one']:.4f} "
            f"upper {scores['upper']:.4f} lower {scores['lower']:.4f}",
            flush=True,
        )
        rank = (scores["digits"] + scores["upper"] + scores["lower"]) / 3
        improved = rank > best + 0.001 or scores["digits"] > best_digits + 0.005
        if improved:
            best = max(best, rank)
            best_digits = max(best_digits, scores["digits"])
            stale = 0
            torch.save(model.state_dict(), out)
            meta_path.write_text(json.dumps({
                "classes": classes,
                "val_macro": round(rank, 4),
                "digits": round(scores["digits"], 4),
                "upper": round(scores["upper"], 4),
                "lower": round(scores["lower"], 4),
            }, indent=2), encoding="utf-8")
            print(f"saved {out}", flush=True)
        else:
            stale += 1
            if epoch >= 4 and stale >= 2:
                print("stopped early", flush=True)
                break
        for group in opt.param_groups:
            group["lr"] *= 0.7
    print(f"best macro {best:.4f}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", default="")
    parser.add_argument("--resume", default="")
    parser.add_argument("--digit-per-class", type=int, default=0)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default="/tmp/emnist")
    parser.add_argument("--per-class", type=int, default=1800)
    parser.add_argument("--val-per-class", type=int, default=250)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--backbone-lr", type=float, default=1e-4)
    parser.add_argument("--head-lr", type=float, default=1e-3)
    args = parser.parse_args()
    if not args.resume and not args.init:
        parser.error("--init is required unless --resume is set")
    if args.digit_per_class <= 0:
        args.digit_per_class = None
    run(args)


if __name__ == "__main__":
    main()
