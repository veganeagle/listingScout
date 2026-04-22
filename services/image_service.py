# services.image_search.py

import os
import requests
import imagehash
from io import BytesIO
from PIL import Image
from urllib.parse import urlparse


SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "")
GOOGLE_VISION_KEY = os.environ.get("GOOGLE_VISION_KEY", "")
MATCH = 12
NEAR_MATCH = 24
RANK_CUTOFF = 14
REQUEST_TIMEOUT = 25


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().lstrip("www.")


def _is_match(score1: int | None, rank: int) -> bool:
    if score1 is None: return False
    if score1 <= MATCH: return True
    if score1 <= NEAR_MATCH and rank <= RANK_CUTOFF: return True
    return False

def _normalize_match(url: str, title: str = "", source: str = "", match_type: str = "unknown",
    thumbnail_url: str | None = None, rank: int = 0, score1: int | None = None):
    return {
        "url": url,
        "domain": _domain(url),
        "title": title or "",
        "source": source or "",
        "match_type": match_type or "unknown",
        "thumbnail_url": thumbnail_url,
        "rank": rank,
        "score1": score1,
    }

def _phash_from_url(url: str):
    if not url: return None
    try:
        r = requests.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        return imagehash.phash(Image.open(BytesIO(r.content)))
    except Exception:
        return None


def search_serpapi(image_url: str) -> list[dict]:
    if not SERPAPI_KEY:
        return []

    try:
        r = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_lens",
                "url": image_url,
                "api_key": SERPAPI_KEY,
            },
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        source_hash = _phash_from_url(image_url)
        print("SERP RAW exact:", len(data.get("exact_matches", [])))
        print("SERP RAW visual:", len(data.get("visual_matches", [])))

        out = []
        for idx, item in enumerate(data.get("exact_matches", []), start=1): ## EXACT MATCH
            if item.get("link"):
                thumb = item.get("thumbnail")
                cand_hash = _phash_from_url(thumb) if thumb and source_hash else None
                score1 = (source_hash - cand_hash) if source_hash and cand_hash else None
                if _is_match(score1, idx):
                    out.append(_normalize_match(url=item["link"], title=item.get("title", ""), source="serpapi",
                        match_type="exact", thumbnail_url=thumb, rank=idx, score1=score1, 
                    )
                )

        visuals = data.get("visual_matches", [])
        for idx, item in enumerate(visuals, start=1):    ## VISUAL MATCH
            if item.get("link"):
                thumb = item.get("thumbnail")
                cand_hash = _phash_from_url(thumb) if thumb and source_hash else None
                score1 = int(source_hash - cand_hash) if source_hash and cand_hash else None
                if _is_match(score1, idx):
                    out.append(_normalize_match(url=item["link"], title=item.get("title", ""), source="serpapi",
                        match_type="visual", thumbnail_url=thumb, rank=idx, score1=score1,
                    )
                )
        return out
    except Exception as e:
        print("SERP ERROR:", e)
        return []


def search_vision_api(image_url: str) -> list[dict]:
    if not GOOGLE_VISION_KEY: return []
    try:
        r = requests.post(
            f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_KEY}",
            json={
                "requests": [
                    {
                        "image": {"source": {"imageUri": image_url}},
                        "features": [{"type": "WEB_DETECTION", "maxResults": 40}],
                    }
                ]
            },
            timeout=20,
        )
        r.raise_for_status()
        web = r.json().get("responses", [{}])[0].get("webDetection", {})

        out = []
        for page in web.get("pagesWithMatchingImages", []):
            if page.get("url"):
                out.append(
                    _normalize_match(
                        url=page["url"],
                        title=page.get("pageTitle", ""),
                        source="vision",
                        match_type="web",
                        thumbnail_url=None,
                    )
                )
        return out
    except Exception:
        return []


def _dedupe(matches: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for item in matches:
        domain = item["domain"]
        if domain in seen:
            continue
        seen.add(domain)
        out.append(item)
    return out


def run_image_search(image_url: str) -> dict:
    print(f"SERPAPI_KEY present: {bool(SERPAPI_KEY)}")
    print (f'Image service for {image_url}')
    serp = search_serpapi(image_url)
    if serp:
        print(f'matches found by serp {len(serp)}')
        return {
            "provider": "serpapi",
            "matches": _dedupe(serp),
        }

    vision = search_vision_api(image_url)
    print(f'matches found by google vision {len(vision)}')
    if vision:
        return {
            "provider": "vision",
            "matches": _dedupe(vision),
        }
    print (' no matches')

    return {
        "provider": "none",
        "matches": [],
    }