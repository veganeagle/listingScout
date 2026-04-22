# services/extract_service.py

import json
import re
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT = 15

BASE_DIR = Path(__file__).resolve().parent.parent
REF_PATH = BASE_DIR / "reference_data.json"

with open(REF_PATH, "r", encoding="utf-8") as f:
    REF = json.load(f)

PMS_PLATFORMS = REF["pms_platforms"]
OTA_NAMES = {"Airbnb"} | set(REF["ota_names"])


def _root_domain(url: str) -> str:
    host = urlparse(url).netloc.lower().lstrip("www.")
    return host


def _detect_platform(url: str) -> str | None:
    lower = url.lower()
    if "airbnb." in lower:
        return "Airbnb"
    for p in PMS_PLATFORMS:
        for pat in p["patterns"]:
            if pat in lower:
                return p["name"]
    return None


def _detect_listing_source(url: str) -> str:
    platform = _detect_platform(url)
    if platform:
        return platform
    return _root_domain(url)


def _clean_text(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value).strip()
        return value or None
    return value


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _looks_like_image(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    lower = url.lower()
    return lower.startswith("http") and any(x in lower for x in [".jpg", ".jpeg", ".png", ".webp", "image", "picture", "photo"])


def _unique_nonempty(values):
    out = []
    seen = set()
    for v in values:
        v = _clean_text(v)
        if not v:
            continue
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _json_walk_images(node):
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() == "image":
                for item in _as_list(v):
                    if isinstance(item, str) and _looks_like_image(item):
                        out.append(item)
                    elif isinstance(item, dict):
                        for kk in ["url", "contentUrl", "thumbnailUrl"]:
                            if _looks_like_image(item.get(kk)):
                                out.append(item[kk])
            else:
                out.extend(_json_walk_images(v))
    elif isinstance(node, list):
        for item in node:
            out.extend(_json_walk_images(item))
    return out


def _json_walk_first(node, keys):
    if isinstance(node, dict):
        for k, v in node.items():
            if k in keys and _clean_text(v):
                return _clean_text(v)
            found = _json_walk_first(v, keys)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _json_walk_first(item, keys)
            if found:
                return found
    return None


def _json_walk_geo(node):
    if isinstance(node, dict):
        if "latitude" in node or "longitude" in node:
            return {
                "latitude": node.get("latitude"),
                "longitude": node.get("longitude"),
            }
        for v in node.values():
            found = _json_walk_geo(v)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = _json_walk_geo(item)
            if found:
                return found
    return None


def _extract_airbnb_room_id(url: str):
    m = re.search(r"/rooms/(\d+)", url)
    return m.group(1) if m else None

def _base_result(listing_url, image_url):
    source = _detect_listing_source(listing_url) if listing_url else "manual"
    return {
        "listing_url": listing_url,
        "listing_source": source,
        "is_ota": source in OTA_NAMES,
        "room_id": _extract_airbnb_room_id(listing_url) if listing_url and "airbnb." in listing_url else None,
        "hero_image_url": image_url,
        "image_candidates": [image_url] if image_url else [],
        "metadata": {},
        "error": None,
    }

def _extract_meta(soup: BeautifulSoup):
    meta = {}

    def get_meta(attr_name, attr_value):
        tag = soup.find("meta", attrs={attr_name: attr_value})
        return _clean_text(tag.get("content")) if tag and tag.get("content") else None

    meta["title"] = get_meta("property", "og:title") or get_meta("name", "twitter:title")
    meta["description"] = get_meta("property", "og:description") or get_meta("name", "description")
    meta["hero_image"] = get_meta("property", "og:image") or get_meta("name", "twitter:image")
    meta["url"] = get_meta("property", "og:url")
    meta["site_name"] = get_meta("property", "og:site_name")
    meta["locality"] = get_meta("property", "og:locality")
    meta["country_name"] = get_meta("property", "og:country-name")
    meta["latitude"] = get_meta("property", "place:location:latitude")
    meta["longitude"] = get_meta("property", "place:location:longitude")

    return meta


def _extract_json_ld(soup: BeautifulSoup):
    blocks = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            blocks.append(data)
        except Exception:
            continue
    return blocks


def _extract_from_json_ld(blocks):
    images = []
    title = None
    description = None
    locality = None
    address = None
    geo = None

    for block in blocks:
        images.extend(_json_walk_images(block))
        if not title:
            title = _json_walk_first(block, {"name", "headline"})
        if not description:
            description = _json_walk_first(block, {"description"})
        if not locality:
            locality = _json_walk_first(block, {"addressLocality"})
        if not address:
            address = _json_walk_first(block, {"streetAddress"})
        if not geo:
            geo = _json_walk_geo(block)

    return {
        "title": title,
        "description": description,
        "locality": locality,
        "address": address,
        "geo": geo or {},
        "images": _unique_nonempty(images),
    }


def _extract_title_parts(title: str | None):
    if not title:
        return {"name": None, "city": None}
    parts = [p.strip() for p in title.split("·")]
    if len(parts) >= 2:
        return {"name": _clean_text(parts[0]), "city": _clean_text(parts[-1])}
    parts = [p.strip() for p in title.split("-")]
    if len(parts) >= 2:
        return {"name": _clean_text(parts[0]), "city": _clean_text(parts[-1])}
    return {"name": _clean_text(title), "city": None}


def extract_listing(listing_url: str) -> dict:
    try:
        r = requests.get(listing_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except Exception as e:
        r = _base_result(listing_url, None)
        r["status"] = "error"
        r["image_candidates"] = []
        r["metadata"] = {}
        r["error"] = str(e)
        return r

    soup = BeautifulSoup(r.text, "html.parser")
    meta = _extract_meta(soup)
    json_ld_blocks = _extract_json_ld(soup)
    json_ld = _extract_from_json_ld(json_ld_blocks)
    title_parts = _extract_title_parts(meta["title"] or json_ld["title"] or soup.title.string if soup.title and soup.title.string else None)
    image_candidates = _unique_nonempty( [meta["hero_image"]] + json_ld["images"])
    hero_image_url = image_candidates[0] if image_candidates else None
    city = (meta["locality"] or json_ld["locality"] or title_parts["city"] or meta["country_name"])
    name = ( title_parts["name"] or json_ld["title"] or meta["title"])

    metadata = {
        "name": _clean_text(name),
        "city": _clean_text(city),
        "address": _clean_text(json_ld["address"]),
        "description": _clean_text(json_ld["description"] or meta["description"]),
        "site_name": _clean_text(meta["site_name"]),
        "canonical_url": _clean_text(meta["url"]) or listing_url,
        "latitude": json_ld["geo"].get("latitude") or meta["latitude"],
        "longitude": json_ld["geo"].get("longitude") or meta["longitude"],
        "page_title": _clean_text(soup.title.string) if soup.title and soup.title.string else None,
    }

    r = _base_result(listing_url, hero_image_url)
    r["status"] = "ok" if hero_image_url else "partial"
    r["image_candidates"] = image_candidates
    r["metadata"] = metadata
    r["error"] = None if hero_image_url else "No hero image found"
    return r


def resolve_input(image_url: str | None = None, listing_url: str | None = None, selected_image_url: str | None = None) -> dict:
    if selected_image_url:
        r = _base_result(listing_url, selected_image_url)
        r["status"] = "ok"
        return r

    if image_url:
        r = _base_result(listing_url, image_url)
        r["status"] = "ok"
        return r

    if listing_url: return extract_listing(listing_url)
    r = _base_result(None, None)
    r["status"] = "error"
    r["error"] = "No image_url or listing_url provided"
    return r