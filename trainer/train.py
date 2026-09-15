"""Train the maritime/thermal vessel classifier.

Usage:
  .venv/bin/python trainer/train.py --epochs 2 --batch 32
Trains a ResNet18 to classify images across all raw sources (maritime SAR,
thermal, optical), saves checkpoint + metrics.
"""
import argparse
import os
from pathlib import Path

# The host GPU is shared and OOM-prone; default to CPU training to be safe.
if os.environ.get("CUDA_VISIBLE_DEVICES") is None:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
import torch
import torch.nn as nn

from .dataset import ShipImageDataset
from .models import build_model

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ship_data" / "raw"
OUT = ROOT / "checkpoints"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--backbone", default="resnet18")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--resume", default="", help="checkpoint to resume from")
    args = ap.parse_args()

    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)
    print(f"[train] device={device} backbone={args.backbone} epochs={args.epochs}")
    # Shared GPU may be OOM-prone; fall back to CPU if the first .to() fails.
    try:
        model_probe = torch.zeros(1, device=device)
        _ = model_probe
    except Exception as e:
        print(f"[train] CUDA OOM on probe ({e}); falling back to CPU")
        device = torch.device("cpu")

    train_ds = ShipImageDataset(RAW, split="train")
    val_ds = ShipImageDataset(RAW, split="val")
    n_classes = len(train_ds.class_names)
    print(f"[train] classes={n_classes}: {train_ds.class_names}")
    print(f"[train] train={len(train_ds)} val={len(val_ds)}")

    model = build_model(n_classes, args.backbone)
    start_epoch = 0
    if args.resume:
        state = torch.load(args.resume, map_location="cpu")
        model.load_state_dict(state["model"])
        start_epoch = state.get("epoch", 0) + 1
        print(f"[train] resuming from {args.resume} at epoch {start_epoch}")
    try:
        model = model.to(device)
    except Exception as e:
        print(f"[train] model.to(cuda) failed ({e}); using CPU")
        device = torch.device("cpu")
        model = model.to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    train_loader = torch.utils.data.DataLoader(
        train_ds, batch_size=args.batch, shuffle=True, num_workers=4, pin_memory=False)
    val_loader = torch.utils.data.DataLoader(
        val_ds, batch_size=args.batch, shuffle=False, num_workers=4, pin_memory=False)

    OUT.mkdir(parents=True, exist_ok=True)
    best_val = 1.0
    for epoch in range(start_epoch, args.epochs):
        model.train()
        running = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            running += loss.item() * x.size(0)
        train_loss = running / len(train_ds)

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x).argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.size(0)
        val_acc = correct / max(total, 1)
        print(f"[epoch {epoch+1}] train_loss={train_loss:.4f} val_acc={val_acc:.4f}")

        # Save a resumable checkpoint every epoch (model + optimizer + epoch + best).
        torch.save(
            {"model": model.state_dict(), "optimizer": opt.state_dict(),
             "epoch": epoch, "best_val": best_val, "backbone": args.backbone},
            OUT / "last_vessel_classifier.pt",
        )
        if val_acc > best_val:
            best_val = val_acc
            torch.save(
                {"model": model.state_dict(), "optimizer": opt.state_dict(),
                 "epoch": epoch, "best_val": best_val, "backbone": args.backbone},
                OUT / "best_vessel_classifier.pt",
            )

    print(f"[train] done. best val_acc={best_val:.4f}.")
    print(f"[train] checkpoints: {OUT/'best_vessel_classifier.pt'} + {OUT/'last_vessel_classifier.pt'}")
    print(f"[train] to resume: .venv/bin/python -m trainer.train --epochs {args.epochs} --resume {OUT/'last_vessel_classifier.pt'}")


if __name__ == "__main__":
    main()
