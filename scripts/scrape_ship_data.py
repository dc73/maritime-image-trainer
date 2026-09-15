"""Scrape ship imagery from satellite datasets, Roboflow, and MarineTraffic.

Both JS-heavy sources (Roboflow, MarineTraffic) sit behind Cloudflare and only
render with a real (headed) Chrome under a virtual display. The satellite
datasets are static files fetched straight from the GitHub API.

Outputs:
  ship_data/raw/<source>/*.jpg
  ship_data/meta/records.jsonl
"""
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import requests
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "ship_data" / "raw"
META = ROOT / "ship_data" / "meta"
RAW.mkdir(parents=True, exist_ok=True)
META.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}


def http_get(url, stream_to=None, timeout=60):
    r = requests.get(url, headers=HEADERS, timeout=timeout, stream=bool(stream_to))
    r.raise_for_status()
    if stream_to:
        with open(stream_to, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 16):
                f.write(chunk)
    return r


def sanitize(name, maxlen=60):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_")
    return (name[:maxlen] or "img")


def ext_from_url(url):
    path = urlparse(url).path
    m = re.search(r"\.(jpe?g|png|webp|bmp)$", path, re.I)
    return ("." + m.group(1).lower()) if m else ".jpg"


def save_image(url, source, slug):
    dest_dir = RAW / source
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}{ext_from_url(url)}"
    http_get(url, stream_to=str(dest))
    return dest


def launch_browser(playwright, channel="chrome"):
    """Launch a real Chrome under xvfb so Cloudflare passes."""
    return playwright.chromium.launch(
        headless=False,
        channel=channel,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )


def scrape_marinetraffic(max_photos=60):
    """MarineTraffic photos via headed Chrome (xvfb) + Cloudflare challenge.

    The getPhoto endpoint is Cloudflare-protected, so we render each photo
    by navigating its direct URL and capturing a PNG screenshot of the
    rendered image. Returns (photo_id, meta, png_bytes) tuples.
    """
    out = []
    base = "https://www.marinetraffic.com/zh/photos?order=date_uploaded"
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(base, timeout=90000)
        page.wait_for_selector("img[src*='getPhoto']", timeout=90000)
        page.wait_for_timeout(3000)
        urls = [
            u
            for u in page.eval_on_selector_all(
                "img[src*='getPhoto']",
                "imgs => imgs.map(i => i.src)"
            )
        ][:max_photos]
        for u in urls:
            m = parse_qs(urlparse(u).query)
            photo_id = m.get("photo_id", [""])[0]
            size = m.get("photo_size", ["800"])[0]
            photo_url = f"https://www.marinetraffic.com/getPhoto/?photo_id={photo_id}&photo_size={size}"
            # Render the photo directly (passes Cloudflare) and screenshot it.
            page2 = browser.new_page(viewport={"width": 800, "height": 800})
            page2.goto(photo_url, timeout=90000)
            page2.wait_for_load_state("domcontentloaded", timeout=90000)
            page2.wait_for_timeout(3000)
            png = page2.screenshot(type="png")
            page2.close()
            out.append((photo_id, {"order": "date_uploaded", "size": size, "format": "png"}, png))
        browser.close()
    return out


def scrape_roboflow(max_images=100):
    """Roboflow browse page via headed Chrome (xvfb)."""
    out = []
    url = (
        "https://app.roboflow.com/dheerchhabria-gmail-com/thermal-ships-moctp-1yuut-5ljo1"
        "/browse?queryText=&pageSize=1000&startingIndex=0&browseQuery=true"
    )
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.goto(url, timeout=90000)
        page.wait_for_selector("img[src*='source.roboflow.com']", timeout=90000)
        page.wait_for_timeout(8000)
        html = page.content()
        urls = set(re.findall(r"https?://[^\"'\s]+?\.(?:jpe?g|png|webp)", html))
        # Keep only the actual sample thumbnails, skip annotation overlays.
        thumbs = [
            u for u in urls
            if "/thumb." in u or re.search(r"thumb\.(jpe?g|png)$", u, re.I)
        ]
        for u in thumbs[:max_images]:
            seg = u.split("/")[-2]
            out.append((u, {"dataset": "thermal-ships", "sample_id": seg}))
        browser.close()
    return out


def _gh_list(repo, path=None):
    url = f"https://api.github.com/repos/{repo}/contents"
    if path:
        url += f"/{path}"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    return r.json()


def scrape_satellite_ships(max_per_repo=15):
    """SAR ship datasets referenced by the jasonmanesis curation repo.

    The curation repo only catalogs datasets that live in other repos; we
    pull real SAR ship images from the two dataset repos that store them
    directly on GitHub.
    """
    sources = [
        # (repo, subfolder-or-None, dataset_label)
        ("chaozhong2010/HRSID", "data", "HRSID-SAR"),
        (
            "liyiniiecas/A_Dual-polarimetric_SAR_Ship_Detection_Dataset",
            "PNGImages/train",
            "DSSDD-SAR",
        ),
    ]
    out = []
    for repo, path, label in sources:
        try:
            items = _gh_list(repo, path)
        except Exception as e:
            print(f"[satellite] {repo}/{path}: {e}")
            continue
        img_items = [
            it for it in items
            if re.search(r"\.(jpe?g|png|webp|bmp)$", it.get("name", ""), re.I)
            and not re.search(r"_instance_", it["name"], re.I)
        ][:max_per_repo]
        for it in img_items:
            out.append(
                (
                    it["download_url"],
                    {"dataset": label, "name": it["name"]},
                )
            )
    return out


def save_bytes(data, source, slug, fmt="jpg"):
    dest_dir = RAW / source
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}.{fmt}"
    dest.write_bytes(data)
    return dest


def main():
    records = []

    # MarineTraffic: images arrive pre-fetched through the cleared browser.
    for photo_id, meta, body in scrape_marinetraffic(max_photos=60):
        records.append(
            {
                "source": "marinetraffic",
                "image_url": f"https://www.marinetraffic.com/getPhoto/?photo_id={photo_id}",
                "meta": meta,
                "_bytes": body,
            }
        )

    # Roboflow + satellite: plain (url, meta) tuples, downloaded via HTTP.
    for url, meta in scrape_roboflow(max_images=100):
        records.append({"source": "roboflow", "image_url": url, "meta": meta})
    for url, meta in scrape_satellite_ships(max_per_repo=15):
        records.append({"source": "satellite", "image_url": url, "meta": meta})

    failures = 0
    for rec in records:
        source = rec["source"]
        meta = rec["meta"] or {}
        # Prefer the most specific identifier so filenames stay unique.
        photo_id = meta.get("photo_id")
        if not photo_id:
            m = parse_qs(urlparse(rec["image_url"]).query)
            photo_id = m.get("photo_id", [""])[0] or None
        name = (
            photo_id
            or meta.get("sample_id")
            or meta.get("name")
            or "img"
        )
        slug = sanitize(name)
        try:
            if "_bytes" in rec:
                fmt = (rec["meta"] or {}).get("format", "jpg")
                dest = save_bytes(rec.pop("_bytes"), source, slug, fmt)
            else:
                dest = save_image(rec["image_url"], source, slug)
            rec["saved_to"] = str(dest.relative_to(ROOT))
            print(f"[ok] {source}/{dest.name} ({dest.stat().st_size // 1024} KB)")
        except Exception as e:
            rec.pop("_bytes", None)
            failures += 1
            rec["error"] = str(e)
            print(f"[fail] {source}: {e}")

    meta_path = META / "records.jsonl"
    with open(meta_path, "w") as f:
        for rec in records:
            rec.pop("_bytes", None)
            f.write(json.dumps(rec) + "\n")

    print(f"\nDone: {len(records) - failures} images saved, {failures} failures.")
    print(f"Metadata written to {meta_path}")


if __name__ == "__main__":
    main()
