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
REQUEST_TIMEOUT = 10

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,7}\b")
_PHONE_RE = re.compile(
    r"(?:\+?1[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}"
    r"|\+\d{1,3}[\s.\-]?(?:\(?\d{1,4}\)?[\s.\-])?\d{1,4}[\s.\-]\d{1,9})"
)
_ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.'#\- ]+\s(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr|Court|Ct|Boulevard|Blvd|Way|Place|Pl|Terrace|Ter)\b",
    re.I)

BASE_DIR = Path(__file__).resolve().parent.parent

with open(BASE_DIR / "reference_data.json", "r", encoding="utf-8") as f:
    REF = json.load(f)

_JUNK_DOMAINS = set(REF["junk_domains"])
_WEBMAIL_DOMAINS = set(REF["webmail_domains"])
_JUNK_LOCAL_PARTS = set(REF["junk_local_parts"])


def _root_domain(host: str) -> str:
    if not host:
        return ""
    host = host.lower().lstrip("www.")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])

def _visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text


def _likely_phone_context(text: str, match_text: str) -> bool:
    i = text.find(match_text)
    if i == -1:
        return False

    window = text[max(0, i - 40): min(len(text), i + len(match_text) + 40)].lower()

    good = (
        "call", "phone", "tel", "text", "contact",
        "reservation", "booking", "mobile", "office"
    )
    bad = (
        "woff", "woff2", "ttf", "otf", "font",
        "padding", "margin", "width", "height",
        "translate", "rotate", "scale", "matrix",
        "rgba", "background", "stylesheet"
    )

    return any(g in window for g in good) and not any(b in window for b in bad)


def clean_emails(raw, page_domain: str = ""):
    out = []
    page_root = _root_domain(page_domain)

    for e in raw:
        e = e.strip().lower()

        if len(e) > 80 or len(e) < 6:
            continue
        if re.match(r"^u00[0-9a-f]{2}", e):
            continue
        if "\\u" in e or "u003" in e.split("@")[0]:
            continue
        if re.search(r"[^a-z0-9._%+\-@]", e):
            continue

        local, _, domain = e.partition("@")

        if len(local) >= 24 and re.fullmatch(r"[a-f0-9]+", local):
            continue
        if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|css|js|woff2?)$", e, re.I):
            continue
        if domain in _JUNK_DOMAINS:
            continue
        if any(domain.endswith("." + jd) for jd in _JUNK_DOMAINS):
            continue
        if local in _JUNK_LOCAL_PARTS:
            continue

        root = _root_domain(domain)
        is_page_match = page_root and (root == page_root)
        is_webmail = domain in _WEBMAIL_DOMAINS
        if not (is_page_match or is_webmail):
            continue

        out.append(e)

    return list(dict.fromkeys(out))[:3]

def clean_phones(raw):
    out = []
    for p in raw:
        digits = re.sub(r"\D", "", p)

        if len(digits) == 11 and digits.startswith("1"):
            n = digits[1:]
        elif len(digits) == 10:
            n = digits
        else:
            continue

        area = n[:3]
        exch = n[3:6]
        if area[0] in "01" or exch[0] in "01": continue
        if n in {"8663933393", "8772024291"}: continue
        out.append(f"+1{n}")

    return list(dict.fromkeys(out))[:8]

def clean_addresses(raw):
    out = []
    for a in raw:
        a = re.sub(r"\s+", " ", a).strip(" ,")
        if len(a) >= 10:
            out.append(a)
    return list(dict.fromkeys(out))[:3]


def _decode_unicode_escapes(s: str) -> str:
    if not s:
        return s
    try:
        s = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)
    except Exception:
        pass
    try:
        import html as _html
        s = _html.unescape(s)
    except Exception:
        pass
    return s


def scrape_contact(url: str) -> dict:
    result = {"emails": [], "phones": [], "title": "","address":None, "error": None}
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    page_domain = parsed.netloc

    def fetch(target):
        try:
            r = requests.get(target, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if r.status_code == 200:
                html_decoded = _decode_unicode_escapes(r.text)
                soup = BeautifulSoup(html_decoded, "html.parser")
                visible_text = _visible_text(soup)
                return soup, html_decoded, visible_text
        except Exception:
            pass
        return None, None, None

    soup, html, text = fetch(url)
    if html is None:
        result["error"] = "Could not fetch"
        return result

    result["title"] = soup.title.string.strip() if soup.title and soup.title.string else ""

    emails = clean_emails(set(_EMAIL_RE.findall(html)), page_domain=page_domain)
    raw_phone_hits = _PHONE_RE.findall(text)
    raw_phone_hits = [p for p in raw_phone_hits if _likely_phone_context(text, p)]
    phones = clean_phones(raw_phone_hits)
    addresses = clean_addresses(_ADDRESS_RE.findall(text))

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, dict):
                if "telephone" in data:
                    phones.append(str(data["telephone"]))
                if "email" in data:
                    emails.append(str(data["email"]).lower())
        except Exception:
            pass

    if not emails and not phones:
        for subpath in ["/contact", "/contact-us", "/about"]:
            _, s_html, s_text = fetch(base + subpath)
            if s_html:
                emails += clean_emails(set(_EMAIL_RE.findall(s_html)), page_domain=page_domain)
                raw_sub_phones = [p for p in _PHONE_RE.findall(s_text) if _likely_phone_context(s_text, p)]
                phones += clean_phones(raw_sub_phones)
                if emails or phones:    break

    result["emails"] = clean_emails(set(emails), page_domain=page_domain)
    result["phones"] = clean_phones(phones)
    result["address"] = clean_addresses(addresses)[0] if addresses else None
    return result