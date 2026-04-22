# Listing Finder — Architecture & Business Notes

## The Core Idea

An Airbnb host's listing photos almost always appear on multiple platforms simultaneously — their Airbnb page, their direct-booking website (powered by a PMS like Lodgify or OwnerRez), VRBO, Booking.com, and so on. Those direct-booking pages often display the host's real email and phone number — contact details Airbnb deliberately hides.

**Listing Finder** automates that discovery:
1. Take the hero image from any Airbnb listing URL
2. Run a reverse image search to find every other page that image appears on
3. Identify which of those pages are PMS-powered direct-booking sites
4. Extract the host's contact information from those pages

---

## Pipeline Overview

```
Airbnb URL or Image URL
        │
        ▼
┌───────────────────────┐
│  1. Image Extraction  │   Pulls the hero photo URL from the Airbnb listing
│     (listing_finder)  │   via og:image meta tag, JSON-LD schema, or Airbnb API
└───────────┬───────────┘
            │  image URL (publicly accessible)
            ▼
┌───────────────────────┐
│  2. Reverse Image     │   Sends image URL to Google Lens (via SerpApi) or
│     Search            │   Google Cloud Vision webDetection API
│                       │   Returns: list of pages that contain this image
└───────────┬───────────┘
            │  [{url, title, source}, ...]
            ▼
┌───────────────────────┐
│  3. Platform          │   Matches each URL against a fingerprint list of 30+
│     Detection         │   known PMS platforms (Lodgify, OwnerRez, Hostaway,
│                       │   Guesty, Beds24, etc.) and OTA competitors
└───────────┬───────────┘
            │  annotated URLs with platform labels
            ▼
┌───────────────────────┐
│  4. Contact           │   For each direct-booking URL, fetches the page and
│     Extraction        │   scrapes for emails (regex) and phone numbers (regex)
│                       │   Also checks /contact and /about subpages
│                       │   Also parses schema.org JSON-LD for telephone/email
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│  5. JSON Report       │   Structured output: all matches, platform IDs,
│                       │   found emails, found phones, summary
└───────────────────────┘
```

---

## API Options for Step 2

### Option A — SerpApi Google Lens (Recommended to start)
- **URL**: https://serpapi.com/google-lens-api
- **Pricing**: $50/month for 5,000 searches; 100 free searches on sign-up
- **Pros**: No infrastructure needed, very easy to use, returns visual + exact matches
- **Setup**: `export SERPAPI_KEY="your_key_here"`

### Option B — Google Cloud Vision webDetection
- **URL**: https://cloud.google.com/vision/docs/detecting-web
- **Pricing**: First 1,000 units/month FREE, then $1.50 / 1,000
- **Pros**: More accurate for exact matches; lower cost at scale
- **Setup**: `export GOOGLE_VISION_KEY="your_key_here"`

---

## PMS Platforms Detected (30+ fingerprints)

| Category | Platforms |
|----------|-----------|
| Direct booking engines | Lodgify, OwnerRez, Hostaway, Guesty, Hostfully, Hospitable, Smoobu |
| Channel managers w/ direct booking | iGMS, Tokeet, Uplisting, Beds24, Cloudbeds, Zeevou |
| Regional/specialty | Supercontrol, LiveRez, Barefoot, Streamline VRS, Kigo, Track HS |
| OTA competitors (tracked, not scraped) | VRBO, Booking.com, TripAdvisor, Expedia, Vacasa, Evolve |

---

## Output Format (report.json)

```json
{
  "image_url": "https://...",
  "timestamp": "2026-04-01T12:00:00",
  "total_pages_found": 7,
  "direct_booking_hits": 3,
  "ota_hits": 3,
  "unknown_hits": 1,
  "contact_summary": {
    "emails": ["host@mybeachhouse.com"],
    "phones": ["+1 (850) 555-1234"]
  },
  "matches": [
    {
      "url": "https://mybeachhouse.lodgify.com/",
      "domain": "mybeachhouse.lodgify.com",
      "platform": "Lodgify",
      "is_direct": true,
      "page_title": "My Beach House — Book Direct",
      "emails": ["host@mybeachhouse.com"],
      "phones": ["+1 (850) 555-1234"],
      "error": null
    }
  ]
}
```

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key (get a free SerpApi key at serpapi.com)
export SERPAPI_KEY="your_serpapi_key_here"

# 3. Run on an Airbnb listing URL
python listing_finder.py --url "https://www.airbnb.com/rooms/12345"

# 4. Or pass an image URL directly (skip Airbnb extraction)
python listing_finder.py --image "https://cdn.example.com/property-hero.jpg"

# 5. Demo mode (no API key needed — uses simulated results)
python listing_finder.py --demo
```

---

## Micro SaaS Path to Revenue

### Target Customer
Property managers and hosts who want to:
- Verify their direct-booking site is discoverable
- Know which OTAs are using their photos without permission
- Find their own contact info exposure across the web
- Benchmark their competitors' distribution footprint

### Pricing Ideas
| Tier | Price | Includes |
|------|-------|---------|
| Pay-per-use | $0.25–$1.00 / search | No commitment, good for occasional use |
| Starter | $19/month | 50 searches/month |
| Pro | $49/month | 250 searches/month + CSV export |
| Agency | $149/month | Unlimited + bulk upload + API access |

### Distribution
- Sell directly to hosts via Facebook Groups (STR communities, BiggerPockets)
- List on AppSumo for a launch deal
- Integrate as a feature into an existing STR tool (HostGPT, iGMS, etc.)

### Next Steps to Productize
1. Wrap in a simple Flask/FastAPI web UI with image upload
2. Add a Chrome Extension that adds a "Find Direct Booking" button on Airbnb listing pages
3. Build a bulk mode — upload a CSV of Airbnb URLs, get a full report
4. Add competitor analysis: find ALL listings by the same host across platforms
5. Add monitoring: alert host when their images appear on a new platform

---

## Legal Considerations
- Reverse image search uses publicly available web indexes — no TOS issues
- Scraping public-facing pages for contact info (that the host published themselves) is generally acceptable; check jurisdiction-specific rules
- Do not scrape Airbnb directly (TOS violation) — use only the hero image URL they've already made public
- Store no PII beyond what the host publicly published
