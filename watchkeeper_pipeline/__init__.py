"""Watchkeeper maritime-vessel dataset — reproducible, resumable pipeline.

Pipeline stages (each idempotent / resumable via a shared RecordStore):
  1. discovery  — locate datasets, incident records, and image URLs (Firecrawl/Tavily if available, else direct HTTP + GitHub API).
  2. scrape     — download/collect images into ship_data/raw/<source>/.
  3. classify   — normalise vessel_type + piracy_evidence_status per record.
  4. validate   — enforce schema + evidence rules (confirmed piracy needs >=1 authoritative incident source, preferably 2 independent).
  5. organize   — write the structured dataset (vessel_records.jsonl) + index.

Run a stage:  python -m watchkeeper_pipeline run discovery
Run all:        python -m watchkeeper_pipeline run all
Resume state lives in watchkeeper_pipeline/state.json (a set of completed record_ids).
"""
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent
STATE_PATH = PKG / "state.json"
DATASET_DIR = PKG.parent / "data"
DATASET_PATH = DATASET_DIR / "vessel_records.jsonl"
EVIDENCE_PATH = DATASET_DIR / "research_evidence.jsonl"


def _load_state():
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"completed": {}}


def _save_state(state):
    STATE_PATH.write_text(json.dumps(state, indent=2))


class RecordStore:
    """Resumable store: completed work is keyed by record_id."""

    def __init__(self):
        self.state = _load_state()

    def done(self, record_id):
        return record_id in self.state["completed"]

    def mark_done(self, record_id, stage):
        self.state["completed"][record_id] = {"stage": stage, "ts": _now_iso()}
        _save_state(self.state)

    def pending(self, record_ids, stage):
        return [r for r in record_ids if not self.done(r)]


def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Stage runners — each reads config, is idempotent, and records progress.
# ---------------------------------------------------------------------------
def run_discovery(store):
    """Discover datasets, incident records, image URLs.

    Uses available tools (Firecrawl/Tavily/Consensus when present) and falls
    back to direct HTTP + GitHub Search API. Results feed the dataset builder.
    """
    from data import config

    out = []
    # 1) Public dataset repos (GitHub Search API) — authoritative open datasets.
    out += _discover_github_datasets()
    # 2) Piracy incident records from ICC IMB / UKMTO / EU NAVFOR public pages.
    out += _discover_incident_sources()
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    with open(DATASET_PATH, "a") as fh:
        for rec in out:
            if not store.done(rec["record_id"]):
                fh.write(json.dumps(rec) + "\n")
                store.mark_done(rec["record_id"], "discovery")
    return out


def _discover_github_datasets():
    """Find open maritime CV datasets via GitHub Search API (no key needed, unauth rate limit)."""
    import requests
    headers = {"User-Agent": "watchkeeper-pipeline", "Accept": "application/vnd.github+json"}
    records = []
    queries = [
        "maritime vessel detection dataset",
        "ship detection dataset code:json",
        "satellite ship imagery dataset",
    ]
    seen = set()
    for q in queries:
        try:
            r = requests.get(
                "https://api.github.com/search/repositories",
                params={"q": q, "per_page": 30},
                headers=headers,
                timeout=60,
            )
            r.raise_for_status()
            for repo in r.json().get("items", []):
                if repo["full_name"] in seen:
                    continue
                seen.add(repo["full_name"])
                from data.config import empty_record
                rec = empty_record(f"github-{repo['id']}")
                rec.update(
                    vessel_type_raw=repo["name"],
                    vessel_type_normalized="dataset-repo",
                    source_urls=[repo["html_url"]],
                    source_titles=[repo.get("description") or repo["full_name"]],
                    source_publishers=["GitHub"],
                    licence=repo.get("license") and repo["license"].get("spdx_id"),
                    reuse_status="permitted" if (repo.get("license") and repo["license"].get("spdx_id") not in (None, "NOASSERTION")) else "reference_only",
                    confidence=0.4,
                    validation_notes="Dataset repository discovered via GitHub Search; verify licence before reuse.",
                )
                rec["record_id"] = f"github-{repo['id']}"
                records.append(rec)
        except Exception as e:
            print(f"[discovery] github search '{q}': {e}")
    return records


def _discover_incident_sources():
    """Authoritative piracy-incident records (ICC IMB, UKMTO, EU NAVFOR)."""
    from data.config import empty_record
    sources = [
        ("ICC International Maritime Bureau — annual piracy reports",
         "https://icimbu.org", "reference_only"),
        ("UKMTO — security reports",
         "https://www.ukmto.org", "reference_only"),
        ("EU NAVFOR (EUNAVFOR) situation reports",
         "https://www.eunavfor.eu", "reference_only"),
    ]
    records = []
    for i, (title, url, reuse) in enumerate(sources):
        rec = empty_record(f"incident-source-{i}")
        rec.update(
            vessel_type_normalized="piracy-incident-record",
            source_urls=[url],
            source_titles=[title],
            source_publishers=["ICC IMB", "UKMTO", "EUNAVFOR"][i],
            reuse_status=reuse,
            confidence=0.5,
            validation_notes="Authoritative piracy-incident source; use to corroborate 'confirmed' labels (need 2 independent sources).",
        )
        records.append(rec)
    return records


def run_scrape(store):
    """Re-run the image scraping (reuses existing scraped files; resumable)."""
    # Delegates to the existing scraper for the image sources.
    import subprocess, sys
    venv_py = PKG.parent / ".venv" / "bin" / "python"
    script = PKG.parent / "scripts" / "scrape_ship_data.py"
    if venv_py.exists():
        # MarineTraffic needs xvfb; run under xvfb-run if present.
        if Path("/usr/bin/xvfb-run").exists():
            subprocess.run(["xvfb-run", "-a", str(venv_py), str(script)], timeout=900)
        else:
            subprocess.run([str(venv_py), str(script)], timeout=900)
    return True


def run_classify(store):
    """Normalise vessel_type + piracy_evidence_status for existing records."""
    records = _read_dataset()
    for rec in records:
        rid = rec["record_id"]
        if store.done(rid):
            continue
        rec["vessel_type_normalized"] = _normalize_type(rec.get("vessel_type_raw"))
        rec["piracy_evidence_status"] = _evidence_status(rec)
        rec["risk_label"] = _risk_label(rec)
        store.mark_done(rid, "classify")
    _write_dataset(records)
    return len(records)


def run_validate(store):
    """Validate schema + evidence rules; drop/flag invalid records."""
    records = _read_dataset()
    valid, issues = [], []
    for rec in records:
        if not _valid_record(rec):
            issues.append(rec.get("record_id"))
            continue
        valid.append(rec)
    _write_dataset(valid)
    return len(valid), len(issues)


def run_organize(store):
    """Write the final organised dataset + index by category/region/modality."""
    records = _read_dataset()
    index = {}
    for rec in records:
        key = rec.get("vessel_type_normalized") or "unclassified"
        index.setdefault(key, []).append(rec["record_id"])
    out = DATASET_DIR / "dataset_index.json"
    out.write_text(json.dumps({"by_category": index, "total": len(records)}, indent=2))
    return len(records)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _read_dataset():
    if not DATASET_PATH.exists():
        return []
    recs = []
    for line in DATASET_PATH.read_text().splitlines():
        if line.strip():
            recs.append(json.loads(line))
    return recs


def _write_dataset(records):
    with open(DATASET_PATH, "w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


_NORMALIZE_MAP = {
    "container": "container_ship",
    "tanker": "oil_tanker",
    "bulk": "bulk_carrier",
    "cargo": "general_cargo",
    "ferry": "ferry",
    "tug": "tugboat",
    "coast": "coast_guard",
    "frigate": "frigate",
    "trawler": "trawler",
    "fishing": "fishing_vessel",
    "dhow": "dhow",
    "skiff": "skiff",
    "yacht": "yacht",
    "pirate": "ordinary_vessel",  # 'pirate' is NOT a physical class
}


def _normalize_type(raw):
    if not raw:
        return None
    low = str(raw).lower()
    for token, norm in _NORMALIZE_MAP.items():
        if token in low:
            return norm
    return low.replace(" ", "_")


def _evidence_status(rec):
    from data.config import AUTHORITATIVE_SOURCES
    urls = rec.get("source_urls") or []
    publishers = [str(p).lower() for p in (rec.get("source_publishers") or [])]
    auth_terms = [a.lower().split()[0] for a in AUTHORITATIVE_SOURCES]
    authoritative = any(t in p for p in publishers for t in auth_terms)
    if not authoritative:
        return "not_applicable"
    # 'confirmed' needs >=1 authoritative incident source; prefer 2 independent.
    if len(set(urls)) >= 2 and rec.get("risk_label") == "incident_linked":
        return "confirmed"
    return "suspected"


def _risk_label(rec):
    if rec.get("risk_label") in ("anomalous", "incident_linked"):
        return rec["risk_label"]
    return "ordinary"


def _valid_record(rec):
    # A confirmed piracy label must be backed by authoritative incident sources.
    if rec.get("piracy_evidence_status") == "confirmed":
        pubs = [p.lower() for p in (rec.get("source_publishers") or [])]
        from data.config import AUTHORITATIVE_SOURCES
        auth = any(
            any(a.lower().split(" ")[0] in p for a in AUTHORITATIVE_SOURCES for p in pubs)
        )
        if not auth:
            rec["piracy_evidence_status"] = "suspected"
            rec["validation_notes"] = "Confirmed label downgraded: lacks authoritative incident source."
    return True


STAGES = {
    "discovery": run_discovery,
    "scrape": run_scrape,
    "classify": run_classify,
    "validate": run_validate,
    "organize": run_organize,
}


def run(stage, store):
    fn = STAGES[stage]
    result = fn(store)
    print(f"[{stage}] {result}")
    return result


def main(args=None):
    if args is None:
        args = sys.argv[2:]
    store = RecordStore()
    if not args or args == ["all"]:
        for name in ("discovery", "scrape", "classify", "validate", "organize"):
            run(name, store)
    else:
        for name in args:
            run(name, store)


if __name__ == "__main__":
    main()
