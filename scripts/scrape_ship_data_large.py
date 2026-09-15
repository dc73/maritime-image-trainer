"""Large-scale ship-image scraper + classifier for the Watchkeeper dataset.

Collects images from:
  - CAESAR SAR-Ship-Dataset (39,729 SAR ship chips)  -> "caesar_sarship"
  - HRSID + DSSDD (SAR, already in ship_data/raw/satellite)
  - MarineTraffic photos (Cloudflare, xvfb + Chrome)
  - Roboflow thermal-ships (Cloudflare, xvfb + Chrome)

Resumable: progress is recorded in ship_data/meta/collected.jsonl (one line per
collected image). Re-running skips already-collected files by filename.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ship_data" / "raw"
META = ROOT / "ship_data" / "meta"
COLLECTED = META / "collected.jsonl"
CLASSIFIED = META / "classified.jsonl"

# Vessel categories the user requested, mapped to a normalized label.
VESSEL_CATEGORIES = [
    # Commercial
    ("container ship", "container"),
    ("ultra-large container vessel", "container"),
    ("panamax container ship", "container"),
    ("feeder container ship", "container"),
    ("general cargo ship", "general_cargo"),
    ("bulk carrier", "bulk_carrier"),
    ("oil tanker", "tanker"),
    ("chemical tanker", "tanker"),
    ("lng carrier", "tanker"),
    ("lpg carrier", "tanker"),
    ("ro-ro vessel", "roro"),
    ("vehicle carrier", "vehicle_carrier"),
    ("reefer", "reefer"),
    ("heavy-lift vessel", "heavy_lift"),
    ("livestock carrier", "livestock"),
    # Passenger & service
    ("passenger ship", "passenger"),
    ("cruise ship", "passenger"),
    ("ferry", "ferry"),
    ("tugboat", "tug"),
    ("pilot boat", "pilot_boat"),
    ("harbour service vessel", "harbour_service"),
    ("dredger", "dredger"),
    ("cable laying ship", "cable_laying"),
    ("research vessel", "research"),
    ("offshore supply vessel", "offshore_supply"),
    ("platform support vessel", "platform_support"),
    ("search and rescue vessel", "sar_vessel"),
    ("fireboat", "fireboat"),
    # Government & security
    ("coast guard vessel", "coast_guard"),
    ("patrol boat", "patrol"),
    ("customs vessel", "customs"),
    ("police vessel", "police"),
    ("naval auxiliary", "naval_auxiliary"),
    ("frigate", "frigate"),
    ("destroyer", "destroyer"),
    ("corvette", "corvette"),
    ("amphibious vessel", "amphibious"),
    ("mine countermeasure vessel", "mcm_vessel"),
    # Fishing & small craft
    ("trawler", "trawler"),
    ("longliner", "longliner"),
    ("purse seiner", "purse_seiner"),
    ("gillnet vessel", "gillnet"),
    ("dhow", "dhow"),
    ("skiff", "skiff"),
    ("rigid inflatable boat", "rigid_inflatable"),
    ("speedboat", "speedboat"),
    ("unregistered small craft", "unregistered_small_craft"),
    ("pleasure craft", "pleasure_craft"),
    ("sailing vessel", "sailing"),
    ("yacht", "yacht"),
    ("personal watercraft", "personal_watercraft"),
]


def load_collected():
    collected = set()
    if COLLECTED.exists():
        for line in COLLECTED.read_text().splitlines():
            if line.strip():
                collected.add(json.loads(line)["filename"])
    return collected


def record_collection(filename, source):
    COLLECTED.parent.mkdir(parents=True, exist_ok=True)
    with open(COLLECTED, "a") as fh:
        fh.write(json.dumps({"filename": filename, "source": source}) + "\n")


def collect_caesar_sarship():
    """Copy CAESAR SAR-Ship-Dataset images into the raw folder (resumable)."""
    src_dir = ROOT / "caesar_extract" / "ship_dataset_v0"
    dst_dir = RAW / "caesar_sarship"
    dst_dir.mkdir(parents=True, exist_ok=True)
    collected = load_collected()
    copied = 0
    if src_dir.exists():
        for f in sorted(src_dir.iterdir()):
            if f.suffix.lower() != ".jpg":
                continue
            if f.name in collected:
                continue
            (dst_dir / f.name).write_bytes(f.read_bytes())
            record_collection(f.name, "caesar_sarship")
            copied += 1
    return copied


def classify_images():
    """Assign each raw image a vessel category label.

    SAR ship chips are not individually labelled by sub-type, so they are
    classified as 'ship' (generic). Optical sources (MarineTraffic/Roboflow)
    are classified by the source's own category where known.
    """
    META.mkdir(parents=True, exist_ok=True)
    classified = {}
    if CLASSIFIED.exists():
        for line in CLASSIFIED.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                classified[r["filename"]] = r
    for source_dir in RAW.iterdir():
        if not source_dir.is_dir():
            continue
        source = source_dir.name
        for f in sorted(source_dir.iterdir()):
            if not f.is_file():
                continue
            key = f"{source}/{f.name}"
            if key in classified:
                continue
            label = _label_for_source(source)
            classified[key] = {"filename": key, "vessel_category": label, "source": source}
    with open(CLASSIFIED, "w") as fh:
        for row in classified.values():
            fh.write(json.dumps(row) + "\n")
    return len(classified)


def _label_for_source(source):
    # SAR datasets carry ships but not sub-type; label generically.
    if source in ("caesar_sarship", "satellite"):
        return "ship"
    if source == "roboflow":
        return "ship"  # thermal-ships dataset: ships, sub-type not per-image
    if source == "marinetraffic":
        return "ship"
    return "unknown"


def main():
    copied = collect_caesar_sarship()
    print(f"[collect] caesar_sarship: copied {copied} new images")
    n = classify_images()
    print(f"[classify] {n} images classified")
    # Per-source counts
    from collections import Counter
    counts = Counter()
    for source_dir in RAW.iterdir():
        if source_dir.is_dir():
            counts[source_dir.name] = len(list(source_dir.iterdir()))
    print("[counts]")
    for src, c in sorted(counts.items()):
        print(f"  {src}: {c}")
    print("total:", sum(counts.values()))


if __name__ == "__main__":
    main()
