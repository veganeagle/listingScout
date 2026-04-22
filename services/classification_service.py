# services/classification_service.py

import json, re
from pathlib import Path
from urllib.parse import urlparse, unquote


BASE_DIR = Path(__file__).resolve().parent.parent
REF_PATH = BASE_DIR / "reference_data.json"

with open(REF_PATH, "r", encoding="utf-8") as f:
    REF = json.load(f)

PMS_PLATFORMS = REF["pms_platforms"]
OTA_NAMES = set(REF["ota_names"])
SKIP_DOMAINS = set(REF["skip_domains"])


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().lstrip("www.")


def _detect_platform(url: str) -> str | None:
    lower = (url or "").lower()
    if "airbnb." in lower:
        return "Airbnb"
    for p in PMS_PLATFORMS:
        for pat in p["patterns"]:
            if pat in lower:
                return p["name"]
    return None

def _extract_listing_id(url: str, platform: str | None) -> str | None:
    if not url or not platform:
        return None

    lower = url.lower()

    if platform == "Airbnb":
        m = re.search(r"/rooms/(\d+)", lower)
        return m.group(1) if m else None

    if platform == "VRBO":
        m = re.search(r"/(?:vacation-rental|en-ca/cottage-rental|en-gb/p\d+|p)(?:/p)?(\d+)", lower)
        if m:
            return m.group(1)
        m = re.search(r"[?&]propertyid=(\d+)", lower)
        return m.group(1) if m else None

    if platform == "Booking.com":
        m = re.search(r"/hotel/[^/]+/[^/.]+\.html", lower)
        if m:
            slug = m.group(0).split("/")[-1].replace(".html", "")
            return slug or None
        return None

    if platform == "Expedia":
        m = re.search(r"/(?:hotel|vacation-rental)/[^?]*/?(\d+)", lower)
        return m.group(1) if m else None

    if platform == "TripAdvisor":
        m = re.search(r"-d(\d+)-", lower)
        return m.group(1) if m else None

    return None



def _is_skip_domain(domain: str) -> bool:
    return domain in SKIP_DOMAINS or any(domain.endswith("." + d) for d in SKIP_DOMAINS)


def _norm(s: str | None) -> str:
    if not s:
        return ""
    return "".join(ch.lower() for ch in s if ch.isalnum())


def _direct_name_hit(name: str | None, url: str) -> bool:
    target = _norm(name)
    if not target:
        return False

    parsed = urlparse(url)
    host = _norm(parsed.netloc)
    path_parts = [p for p in parsed.path.split("/") if p]
    first_path = _norm(unquote(path_parts[0])) if path_parts else ""

    return target in host or (first_path and target in first_path)
    


def _classify_match(match: dict, property_name: str | None = None) -> tuple[str, dict]:
    url = match.get("url", "")
    domain = match.get("domain") or _domain(url)
    platform = match.get("platform") or _detect_platform(url)
    is_ota = platform in OTA_NAMES if platform else False
    listing_id = _extract_listing_id(url, platform)

    item = {
        **match,
        "domain": domain,
        "platform": platform,
        "is_ota": is_ota,
        "listing_id": listing_id,
        "is_direct_candidate": False,
        "hidden_reason": None,
    }

    if _is_skip_domain(domain):
        item["hidden_reason"] = "skip_domain"
        return "hidden", item

    if is_ota:
        return "ota", item

    if platform and not is_ota:
        item["is_direct_candidate"] = True
        return "direct", item

    score1 = match.get("score1")
    if _direct_name_hit(property_name, url) and score1 is not None and score1 <= 26:
        item["is_direct_candidate"] = True
        item["platform"] = platform or "Direct"
        return "direct", item
    if score1 is not None and score1 <= 26 and not is_ota:
        if "arrivalscollection.com" in domain or domain.startswith("book.") or domain.count(".") == 1:
            item["is_direct_candidate"] = True
            item["platform"] = platform or "Direct"
            return "direct", item

    return "unknown", item


def classify_matches(matches: list[dict], property_name: str | None = None) -> dict:    
    direct = []
    ota = []
    unknown = []
    hidden = []

    for match in matches:
        bucket, item = _classify_match(match, property_name=property_name)
        if bucket == "direct":
            direct.append(item)
        elif bucket == "ota":
            ota.append(item)
        elif bucket == "hidden":
            hidden.append(item)
        else:
            unknown.append(item)
    print("\nDIRECT")
    for m in direct:
        print(m["domain"], m.get("platform"), m.get("rank"), m.get("score1"))

    print("\nOTA")
    for m in ota:
        print(m["domain"], m.get("platform"), m.get("rank"), m.get("score1"))

    print("\nUNKNOWN")
    for m in unknown:
        print(m["domain"], m.get("platform"), m.get("rank"), m.get("score1"))

    print("\nHIDDEN")
    for m in hidden:
        print(m["domain"], m.get("hidden_reason"), m.get("rank"), m.get("score1"))

    return {
        "status": "ok",
        "direct": direct,
        "ota": ota,
        "unknown": unknown,
        "hidden": hidden,
    }