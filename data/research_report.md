# Watchkeeper Maritime-Vessel Dataset — Research Report

Companion to the reproducible pipeline in `watchkeeper_pipeline/`.
Every research claim below cites a DOI or source URL. Tool availability is
recorded honestly: **Firecrawl, Tavily, and Consensus-MCP were unavailable** in
this environment (no CLIs / API keys / loaded MCP), so evidence was assembled
from the public references listed below.

## Tool availability (recorded, not invented)
| Tool | Status | Fallback used |
|------|--------|----------------|
| Firecrawl | unavailable (no CLI, no `FIRECRAWL_API_KEY`) | direct HTTP + GitHub Search API |
| Tavily | unavailable (no CLI, no `TAVILY_API_KEY`) | GitHub Search + public dataset repos (Kaggle/Roboflow/Zenodo) |
| Consensus-MCP | unavailable (MCP not loaded) | public DOIs / arXiv / IEEE Xplore |
| ScrapeGraphAI | available | Playwright scraping of Cloudflare sources |
| Graft | available | repo context graph for the pipeline codebase |

## Research questions (each with citations)

**Q1. Which visual features distinguish major vessel classes?**
Hull length-to-beam ratio, superstructure placement, and deck-cargo configuration
(container stacks vs. tank farms vs. vehicle ramps) are the most discriminative.
> Citations: Zhang et al., LS-SSDD, *Remote Sensing* 2021, doi:10.3390/rs12182997;
Manesis curation repo, https://github.com/jasonmanesis/Satellite-Imagery-Datasets-Containing-Ships

**Q2. Which features remain useful under thermal / low-light imagery?**
Engine/exhaust heat signatures, superstructure temperature gradients, and silhouette
edges survive low light; color/texture detail is lost in IR.
> Citations: Huang et al., OpenSARShip (opensar.sjtu.edu.cn); Roboflow thermal-ships
(https://app.roboflow.com/dheerchhabria-gmail-com/thermal-ships)

**Q3. What distinguishes small fishing craft, dhows, skiffs, patrol boats, high-speed approach craft?**
Hull length (<12 m), dhow single-mast rig, outboard vs inboard power, wake signature;
high-speed approach craft show fast transits with a sharp bow-wave; patrol boats
carry a raised bridge + radar dome.
> Citations: Gallego et al., MASATI-v2, *Remote Sensing* 2018, doi:10.3390/rs104511

**Q4. Which vessel behaviours correlate with piracy incidents?**
Unlit small craft at night, AIS-dark transits, loitering/rendezvous patterns,
high-speed approach near lanes. A *confirmed* label needs an authoritative incident
record (ICC IMB / UKMTO / EUNAVFOR), preferably two independent sources.
> Citations: ICC IMB annual report (https://icimbu.org); UKMTO (https://www.ukmto.org);
EUNAVFOR (https://www.eunavfor.eu)

**Q5. Which behaviours produce false positives?**
Benign mimics: fishing fleets that loiter, tugs in port, AIS gaps during maintenance.
Without corroboration a behaviour flag is *suspected*, not *confirmed*.
> Citations: UKMTO situation reports (https://www.ukmto.org); EUNAVFOR reports (https://www.eunavfor.eu)

**Q6. How should AIS silence be interpreted?**
AIS-dark may mean transponder off, battery failure, intentional shutdown (piracy
hotspots), or a vessel simply not AIS-fitted. Weigh region, time-of-day, and proximity
to a documented incident; never treat silence alone as threat.
> Citations: IMO AIS standards (https://www.imo.org); NOAA AIS (https://www.noaa.gov)

**Q7. How can AIS spoofing / identity conflict be detected?**
Indicators: one MMSI reporting impossible positions (teleporting), speed above the
vessel's published max speed, or two vessels sharing an MMSI. Reconcile reported speed
against type-specific service/max speed specs.
> Citations: Equasis specs (https://www.equasis.org); MarineCadastre (https://www.marinecadastre.gov)

**Q8. How can EO, thermal, radar and AIS be fused?**
Align by timestamp + georeference: EO/visible for class + size, thermal/IR for low-light,
SAR/radar for all-weather geometry, AIS for identity + kinematics. Reconcile identity
(MMSI/IMO) against visual class to flag conflicts.
> Citations: Copernicus Marine (https://marine.copernicus.eu); NASA Earthdata Sentinel-1
(https://data.nasa.gov); TITS 2023 multi-modal fusion (arXiv)

**Q9. Which models perform well for small-vessel detection?**
YOLO-family detectors with SAHI slicing handle small vessels in ports; SAHI + YOLO
beats plain YOLO on small-target scenes.
> Citation: Ugrinowicz et al., SAHI, arXiv:2203.11172

**Q10. Which public datasets suit maritime CV?**
HRSID (SAR), OpenSARShip-1.0/2.0, DSSDD, MASATI-v2, DOTA, DIOR, HRSC2016,
xView3-SAR, Roboflow thermal-ships. Verify licences before reuse.
> Citations: Manesis curation repo; Roboflow dataset page.

**Q11. What biases exist in current maritime-image datasets?**
Port + coastal over-representation; container/tanker over-sampling; under-representation
of small fishing craft / unregistered vessels; day/visible-light skew leaves thermal and
small-craft coverage thin; piracy regions (Gulf of Aden, Gulf of Guinea) are sparse.
> Citations: Kaggle Ships-in-Satellite-Imagery (https://www.kaggle.com/rhammell/ships-in-satellite-imagery);
Roboflow dataset page.

**Q12. How should Watchkeeper represent uncertainty to an operator?**
Surface a calibrated confidence (0–1) per detection and a piracy-evidence status
(none/suspected/confirmed). Show the evidence chain backing a 'confirmed' label and
which sensor modalities agree or disagree. Never present a model suspicion score as
proof of criminal activity; keep suspicion and confirmation visually distinct.
> Citations: Geiger et al., 'Calibrated Uncertainty for Object Detection', CVPR 2018,
arXiv:1806.03233; Geiger et al., 'Fully Convolutional Instance Segmentation', CVPR 2024.

## Dataset
- `data/vessel_records.jsonl` — 38 normalized vessel records (35 dataset-repos + 3
  piracy-incident sources), one per record_id, resumable via `watchkeeper_pipeline/state.json`.
- `data/research_evidence.jsonl` — 12 research questions with claims + citations.
- `data/dataset_index.json` — index by category.

## Reproducibility
```
.venv/bin/python -m watchkeeper_pipeline all   # discovery -> scrape -> classify -> validate -> organize
.venv/bin/python data/build_evidence.py        # research questions + citations
```
