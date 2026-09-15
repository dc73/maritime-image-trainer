# Maritime Image Trainer — Watchkeeper

Ship imagery + a structured vessel dataset supporting vessel detection/classification,
EO/thermal recognition, AIS-to-vision correlation, piracy-risk and SAR/IR sensing for
SkyMarine Systems' Watchkeeper autonomous maritime ISR platform.

Two layers:
1. **Image layer** (`ship_data/`) — scraped + processed ship imagery.
2. **Dataset layer** (`data/`) — normalized vessel records, research evidence, and a
   reproducible, resumable pipeline.

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

## Watchkeeper pipeline (reproducible + resumable)
```bash
# run all stages (discovery -> scrape -> classify -> validate -> organize)
.venv/bin/python -m watchkeeper_pipeline all
# or a single stage
.venv/bin/python -m watchkeeper_pipeline discovery
# build the 12 research-question evidence file
.venv/bin/python data/build_evidence.py
```
State lives in `watchkeeper_pipeline/state.json` (completed record_ids), so re-runs
resume where they left off.

## Files
- `data/vessel_records.jsonl` — 38 normalized vessel records (35 dataset repos + 3
  authoritative piracy-incident sources), one per record_id.
- `data/research_evidence.jsonl` — 12 research questions, each with claims + DOI/URL
  citations.
- `data/research_report.md` — human-readable report answering all 12 questions.
- `data/dataset_index.json` — index by category.
- `data/config.py` — categories, regions, source priority, schema (configurable).

## Setup
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
# Cloudflare sources need a virtual display:
xvfb-run -a .venv/bin/python scripts/scrape_ship_data.py
.venv/bin/python scripts/process_ship_data.py
.venv/bin/python -m watchkeeper_pipeline all
```

## Tool availability note
Firecrawl, Tavily, and Consensus-MCP were **unavailable** in this environment (no CLIs,
no API keys, MCP not loaded). The pipeline records this and falls back to direct HTTP +
the GitHub/GitHub-raw APIs. Evidence in `research_evidence.jsonl` uses public DOIs/URLs
so every claim stays checkable.
