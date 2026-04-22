# PMS Booking Site URL Patterns

Examples of real-world booking URLs for each PMS platform. Used as reference
for detecting direct-booking sites in `api/index.py`.

---

## Hostfully

**Example URL:**
```
https://book.hostfully.com/hotel-julie/property-details/39b775e3-b2b2-4129-b1f8-12d9b30c0d05/HOTEL%20JULIE%20Luxe%20&%20Moody%20-%20Flat%203
```

**Pattern observations:**
- Subdomain: `book.hostfully.com`
- Path structure: `/<property-slug>/property-details/<uuid>/<display-name>`
- Uses UUID for the property
- Display name appears URL-encoded in the final path segment

---

## Guesty

**Example sites:**
- stayyonder.com
- thecactuscollection.com

**Typical footprint:**
- URLs often include `/guesty/`
- `guestybookings.com` domain
- Booking engine sometimes opens a Guesty-hosted subdomain

**What to look for:**
- Clean, modern UI
- Booking widget pop-up with Guesty branding in code

---

## Hostaway

**Example sites:**
- futureholiday.com
- azrentals.com

**Typical footprint:**
- Very common pattern: `*.futurestay.com` (legacy)
- `*.hostaway.com` embeds
- Booking pages often redirect to a Hostaway domain
- URL parameters like `?channel=hostaway`

**What to look for:**
- Simple grid listings
- Channel parameter in URL

---

## Lodgify

**Example sites:**
- seasideluxuryrentals.com
- barcelonapartmentrentals.com

**Typical footprint:**
- `*.lodgify.com` subdomains (especially older sites)
- Booking engine often inline (not redirect)

**What to look for:**
- Built-in website + PMS feel
- Sticky booking bar at top

---

## OwnerRez

**Example sites:**
- stayatstj.com
- beachhouserentals.com

**Typical footprint:**
- URLs often include `/quote/` or `/book/`
- Uses ownerrez.com widgets

**What to look for:**
- Slightly more functional than design-heavy
- Quote-first booking flow

---

## Hospitable

**Example sites:**
- Rare for full sites — usually paired with other tools

**Typical footprint:**
- Hospitable is NOT a full PMS website builder
- Usually combined with WordPress or Direct

**What to look for:**
- Not visually identifiable
- Runs backend automation (messaging, ops)

---

## Uplisting

**Example sites:**
- stayhometime.com

**Typical footprint:**
- Uses Uplisting booking engine embeds
- Sometimes white-labeled

**What to look for:**
- Clean booking flow
- Often paired with custom-built websites

---

## Smoobu

**Example sites:**
- hausamsee-ferien.de

**Typical footprint:**
- `*.smoobu.net` booking links
- Website builder sites look simpler

**What to look for:**
- Basic design
- Functional but not highly customized

---

## Escapia

**Example sites:**
- twiddy.com
- outerbanksblue.com

**Typical footprint:**
- Often deeply integrated with Vrbo
- Legacy-style booking flows

**What to look for:**
- More "corporate" / legacy UI
- Heavier navigation and search filters

---

## Track

**Example sites:**
- naturalretreats.com
- avantstay.com

**Typical footprint:**
- Fully custom front-end
- PMS is invisible (enterprise backend)

**What to look for:**
- High-end design
- No obvious third-party branding

---

## Cloudbeds

**Example sites:**
- Boutique hotels & hybrid STR sites

**Typical footprint:**
- Booking engine often via `cloudbeds.com/reservation/...`

**What to look for:**
- Hotel-style booking experience
- Date-first search UI

---

## HolidayFuture

**Example URL:**
```
https://debonairesuites.holidayfuture.com/
```

**Pattern observations:**
- Subdomain pattern: `<property-name>.holidayfuture.com`
- Property gets its own subdomain on the platform

---

## Avantio

**Example sites:**
- costa-rentals.com
- villaplus.com

**Typical footprint:**
- Booking engine uses `/en/rentals/` structure
- `avantio.com` backend calls

**What to look for:**
- European-focused sites
- Multi-language toggle + currency switcher

---

## Beds24

**Example sites:**
- Small independent host sites

**Typical footprint:**
- Booking URLs like `beds24.com/booking2.php`
- Very obvious if not white-labeled

**What to look for:**
- Functional, less polished UI
- Heavy reliance on embedded widgets

---

## RMS Cloud

**Example sites:**
- RV parks, resorts, mixed-use accommodations

**Typical footprint:**
- URLs include `rmscloud.com/Reservation/...`

**What to look for:**
- "Resort-style" booking flows
- Grid-style availability calendars

---

## ResNexus

**Example sites:**
- Bed & breakfasts, inns

**Typical footprint:**
- Booking engine: `resnexus.com/resnexus/reservations/...`

**What to look for:**
- Classic inn/B&B design
- Room-based (not property-based) booking

---

## Little Hotelier

**Example sites:**
- Boutique hotels, small STR hybrids

**Typical footprint:**
- Booking URLs include `littlehotelier.com.au/booking2.php`

**What to look for:**
- Hotel-style booking calendar
- Date-first UX

---

## iGMS

**Example sites:**
- Rare for direct booking sites (mostly backend, like Hospitable)

**Typical footprint:**
- Usually paired with WordPress or custom booking engines

**What to look for:**
- Not visible — focus is operations, not front-end

---

## GuestPoint

**Example sites:**
- Independent hotels, regional operators

**Typical footprint:**
- Booking engine via `guestpoint.com.au` domains

**What to look for:**
- Traditional hotel UI
- Simpler layouts

---

## eZee Absolute

**Example sites:**
- Global budget hotels, small chains

**Typical footprint:**
- Booking URLs: `ezeereservation.com`

**What to look for:**
- Very standardized booking interface
- Strong in Asia/Middle East markets

---

## BookingSync

**Example sites:**
- Custom-built STR brands

**Typical footprint:**
- Rare to see directly (API-first platform)
- Often powers fully custom frontends

**What to look for:**
- Invisible PMS
- High-end or niche operator sites

---

## Kigo

**Example sites:**
- Large US property managers

**Typical footprint:**
- Booking flows often include `/reservations/`
- Backend tied to RealPage

**What to look for:**
- Enterprise feel
- Heavier, data-driven UI

---

# Detection Tips

## How to identify a PMS on any site

1. **Check the booking button URL**
   - Look for redirects (Hostaway, Guesty, Cloudbeds)

2. **Inspect page source** (right-click → View Source)
   - Search for: `hostaway`, `guesty`, `lodgify`, `smoobu`

3. **Use browser tools:**
   - BuiltWith (we have a dataset for this)
   - Wappalyzer Chrome extension

## Strategy implications

| Front-end style | Platforms | Impact |
|---|---|---|
| Template feel | Lodgify, Smoobu | Faster, cheaper, less unique |
| Embedded PMS | Hostaway, Guesty | Flexible design, better branding |
| Custom frontend | Track, Uplisting | Best for scaling + conversions |

## Visibility patterns

**Visible PMS (easy to detect in URL):**
- Beds24, ResNexus, RMS Cloud, Little Hotelier — often expose their booking engine in the URL

**Invisible PMS (hard to detect):**
- BookingSync, iGMS, Track — power custom sites behind the scenes; no URL signature

**Regional leaders:**
- Avantio → Europe
- eZee Absolute → Asia / Middle East
- RMS Cloud → resorts / RV parks
- GuestPoint → Australia
