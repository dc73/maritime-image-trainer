"""Normalize raw ship images into a training-ready layout.

Reads ship_data/raw/<source>/*.{png,jpg} + ship_data/meta/records.jsonl
and writes to ship_data/processed/:
  ship_data/processed/<source>/<ship_id>.png   (uniform 512x512, RGB)
  ship_data/processed/manifest.jsonl            (one line per image w/ metadata)

Ship identity: the "number" is the photo_id/sample_id (the well-formatted
filename); the "name" is the dataset/source label.
"""
import json
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("pip install pillow")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ship_data" / "raw"
META = ROOT / "ship_data" / "meta"
PROCESSED = ROOT / "ship_data" / "processed"
SIZE = 512


def load_records():
    path = META / "records.jsonl"
    records = []
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                records.append(json.loads(line))
    return records


def main():
    records = load_records()
    by_path = {}
    for rec in records:
        if "saved_to" in rec:
            by_path[rec["saved_to"]] = rec

    PROCESSED.mkdir(parents=True, exist_ok=True)
    manifest = []
    for source in ("marinetraffic", "roboflow", "satellite"):
        src_dir = RAW / source
        if not src_dir.exists():
            continue
        out_dir = PROCESSED / source
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.iterdir()):
            if not f.is_file():
                continue
            rec = by_path.get(str(f.relative_to(ROOT)), {})
            img = Image.open(f).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
            # Ship "number" = id from filename (photo_id / sample_id / image id)
            ship_id = f.stem
            out_path = out_dir / f"{ship_id}.png"
            img.save(out_path, "PNG")
            meta = rec.get("meta", {})
            manifest.append(
                {
                    "source": source,
                    "ship_id": ship_id,
                    "name": meta.get("dataset", source),
                    "processed_path": str(out_path.relative_to(ROOT)),
                    "record": rec,
                }
            )
    with open(PROCESSED / "manifest.jsonl", "w") as fh:
        for row in manifest:
            fh.write(json.dumps(row) + "\n")
    print(f"Processed {len(manifest)} images -> {PROCESSED}/")


if __name__ == "__main__":
    main()
