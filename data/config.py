"""Watchkeeper maritime-vessel dataset — central config.

Everything the pipeline needs to stay configurable:
  - vessel categories (commercial, passenger/service, government/security,
    fishing/small-craft, piracy-evidence)
  - research regions (add new regions later)
  - source priority list
  - tool availability (recorded, not invented)

The pipeline reads this file; nothing here is hardcoded into the logic.
"""

# ---------------------------------------------------------------------------
# Vessel categories
# ---------------------------------------------------------------------------
VESSEL_CATEGORIES = {
    "commercial": [
        "container ship", "ultra-large container vessel", "panamax container ship",
        "feeder container ship", "general cargo ship", "bulk carrier", "oil tanker",
        "chemical tanker", "lng carrier", "lpg carrier", "ro-ro vessel",
        "vehicle carrier", "reefer", "heavy-lift vessel", "livestock carrier",
    ],
    "passenger_service": [
        "passenger ship", "cruise ship", "ferry", "tugboat", "pilot boat",
        "harbour service vessel", "dredger", "cable laying ship", "research vessel",
        "offshore supply vessel", "platform support vessel", "sar vessel", "fireboat",
    ],
    "government_security": [
        "coast guard vessel", "patrol boat", "customs vessel", "police vessel",
        "naval auxiliary", "frigate", "destroyer", "corvette", "amphibious vessel",
        "mine countermeasure vessel",
    ],
    "fishing_small_craft": [
        "trawler", "longliner", "purse seiner", "gillnet vessel", "dhow", "skiff",
        "rigid inflatable boat", "speedboat", "unregistered small craft",
        "pleasure craft", "sailing vessel", "yacht", "personal watercraft",
    ],
    "piracy_evidence": [
        "confirmed piracy-incident vessel",
        "suspected piracy-associated craft",
        "hijacked vessel",
        "mothership associated with a documented incident",
        "high-speed approach craft",
        "unlit small craft",
        "ais-dark vessel",
        "ais-spoofing candidate",
        "identity-conflict candidate",
        "rendezvous-pattern vessel",
        "loitering-pattern vessel",
        "abnormal course or speed vessel",
        "ordinary vessel with no piracy evidence",
    ],
}

# ---------------------------------------------------------------------------
# Research regions (configurable)
# ---------------------------------------------------------------------------
RESEARCH_REGIONS = [
    "Gulf of Aden", "Bab-el-Mandeb", "Red Sea", "Arabian Sea", "Gulf of Oman",
    "Strait of Hormuz", "Western Indian Ocean", "Somali Basin", "Gulf of Guinea",
    "Strait of Malacca", "Singapore Strait", "South China Sea", "Bay of Bengal",
    "Mozambique Channel", "Caribbean Sea",
]

# ---------------------------------------------------------------------------
# Authoritative piracy-incident sources (a 'confirmed' label needs >=1 of these,
# and preferably 2 independent sources)
# ---------------------------------------------------------------------------
AUTHORITATIVE_SOURCES = [
    "International Maritime Organization",
    "ICC International Maritime Bureau",
    "UK Maritime Trade Operations",
    "European Union Naval Force",
    "Combined Maritime Forces",
    "National coast guards",
    "National navies",
    "UN reports",
    "Court records",
    "Reputable maritime-security reports",
]

# ---------------------------------------------------------------------------
# Source priority (highest first)
# ---------------------------------------------------------------------------
SOURCE_PRIORITY = [
    "Government and intergovernmental sources",
    "Official maritime-safety and security organizations",
    "Port authorities and coast guards",
    "Classification societies",
    "Manufacturer and shipyard specifications",
    "Peer-reviewed research",
    "Licensed open datasets",
    "Reputable maritime publications",
    "Vessel-tracking websites where permitted",
    "General web pages (supporting only)",
]

# ---------------------------------------------------------------------------
# Search queries (run against available tools)
# ---------------------------------------------------------------------------
SEARCH_QUERIES = [
    "container vessel image dataset",
    "container ship side profile",
    "container vessel aerial imagery",
    "container ship thermal infrared",
    "small vessel maritime thermal dataset",
    "ship detection EO IR dataset",
    "AIS anomaly detection piracy",
    "AIS spoofing vessel identity conflict",
    "piracy mothership documented incident",
    "high speed skiff piracy attack",
    "dhow vessel identification",
    "small fishing vessel aerial dataset",
    "maritime SAR vessel detection dataset",
    "Gulf of Aden piracy incident vessel",
    "Gulf of Guinea piracy incident report",
    "vessel classification deep learning dataset",
]

# ---------------------------------------------------------------------------
# Research questions (each answer needs a citation/DOI/URL)
# ---------------------------------------------------------------------------
RESEARCH_QUESTIONS = [
    "Which visual features distinguish major vessel classes?",
    "Which vessel features remain useful under thermal or low-light imagery?",
    "What distinguishes small fishing craft, dhows, skiffs, patrol boats and high-speed approach craft?",
    "Which vessel behaviours correlate with piracy incidents?",
    "Which behaviours produce false positives?",
    "How should AIS silence be interpreted?",
    "How can AIS spoofing or identity conflict be detected?",
    "How can EO, thermal, radar and AIS observations be fused?",
    "Which models perform well for small-vessel detection?",
    "Which public datasets are suitable for maritime computer vision?",
    "What biases exist in current maritime-image datasets?",
    "How should Watchkeeper represent uncertainty to an operator?",
]

# ---------------------------------------------------------------------------
# Primary tools + recorded availability
# ---------------------------------------------------------------------------
TOOLS = {
    "firecrawl": {
        "repo": "https://github.com/firecrawl/firecrawl",
        "available": False,
        "note": "firecrawl CLI not installed and no FIRECRAWL_API_KEY env var. Using direct HTTP + GitHub/GitHub-raw APIs for web discovery and image-URL scraping.",
    },
    "tavily": {
        "org": "https://github.com/tavily-ai",
        "available": False,
        "note": "tavily CLI not installed and no TAVILY_API_KEY. Broad web discovery done via the GitHub Search API + public dataset repos (Kaggle/Roboflow/Zenodo).",
    },
    "consensus": {
        "repo": "https://github.com/Consensus-NLP/consensus-mcp",
        "available": False,
        "note": "Consensus MCP not loaded. Peer-reviewed evidence gathered via Semantic Scholar / arXiv / IEEE Xplore public APIs and DOIs recorded in the evidence file.",
    },
    "scrapegraphai": {
        "repo": "https://github.com/ScrapeGraphAI/Scrapegraph-ai",
        "available": True,
        "note": "Playwright-based scraping already used for the Cloudflare-protected image sources (MarineTraffic, Roboflow).",
    },
    "graft": {
        "repo": "https://github.com/graft",
        "available": True,
        "note": "Repo context graph; used to orient the pipeline codebase (graft map / graft ask) at low token cost.",
    },
}

# ---------------------------------------------------------------------------
# Reuse / licence status for the scraped image sources
# ---------------------------------------------------------------------------
IMAGE_SOURCE_LICENCES = {
    "marinetraffic": "reference_only",   # MarineTraffic photos: user-uploaded, check terms
    "roboflow": "permitted",            # Roboflow thermal-ships dataset (open for research)
    "satellite": "permitted",           # HRSID + DSSDD: research use, MIT-licensed repos
}

# ---------------------------------------------------------------------------
# Vessel record schema (defaults for a normalized record)
# ---------------------------------------------------------------------------
def empty_record(record_id):
    return {
        "record_id": record_id,
        "vessel_name": None,
        "imo": None,
        "mmsi": None,
        "call_sign": None,
        "flag": None,
        "vessel_type_raw": None,
        "vessel_type_normalized": None,
        "vessel_subtype": None,
        "ais_ship_type_code": None,
        "build_year": None,
        "builder": None,
        "operator": None,
        "registered_owner": None,
        "length_m": None,
        "beam_m": None,
        "draught_m": None,
        "gross_tonnage": None,
        "deadweight_tonnes": None,
        "container_capacity_teu": None,
        "service_speed_knots": None,
        "max_speed_knots": None,
        "visual_features": [],
        "superstructure_position": None,
        "hull_form": None,
        "deck_configuration": None,
        "cargo_configuration": None,
        "sensor_modality": "unknown",
        "viewpoint": "unknown",
        "environment": {"day_night": None, "weather": None, "sea_state": None, "visibility": None},
        "location": {"latitude": None, "longitude": None, "region": None, "port": None},
        "observation_time_utc": None,
        "risk_label": "unknown",
        "piracy_evidence_status": "not_applicable",
        "incident_ids": [],
        "source_urls": [],
        "source_titles": [],
        "source_publishers": [],
        "retrieved_at_utc": None,
        "licence": None,
        "reuse_status": "unknown",
        "confidence": 0.0,
        "validation_notes": None,
    }
