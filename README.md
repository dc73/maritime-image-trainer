# Maritime Image Trainer

Ship imagery collected from three public sources, normalized for training
maritime ship detection / classification models.

## Sources
- **MarineTraffic** — user-uploaded ship photos (Cloudflare-protected).
- **Roboflow** — thermal ship dataset (`thermal-ships`).
- **Satellite / SAR** — HRSID + dual-polarimetric SAR ship datasets (referenced
  by `jasonmanesis/Satellite-Imagery-Datasets-Containing-Ships`).

## Layout
```
maritime-image-trainer/
├── requirements.txt
├── scripts/
│   ├── scrape_ship_data.py   # scrape the 3 sources (xvfb + headed Chrome for Cloudflare)
│   └── process_ship_data.py  # normalize raw -> 512x512 RGB + manifest
└── ship_data/
    ├── raw/{marinetraffic,roboflow,satellite}/   # as-downloaded images
    ├── meta/records.jsonl                            # per-image provenance
    └── processed/{marinetraffic,roboflow,satellite}/ # uniform 512x512 PNG + manifest.jsonl
```

## Conventions
- Filenames carry the ship identity: the **number** (photo_id / sample_id / image id)
  is used as the filename; the **name** (dataset label) is recorded in the metadata.
- `ship_data/processed/manifest.jsonl` maps each image to its provenance record.

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
# Cloudflare sources need a virtual display:
xvfb-run -a .venv/bin/python scripts/scrape_ship_data.py
.venv/bin/python scripts/process_ship_data.py
```
