# app.py

from pathlib import Path
from dataclasses import asdict
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

from models import (PipelineRequest, PipelineResponse, InputPanel,
    MatchRecord, MatchDiscoveryPanel, ClassificationPanel,
    ContactRecord, ContactPanel, ErrorPayload)
from services.extract_service import resolve_input
from services.image_service import run_image_search
from services.classification_service import classify_matches
from services.contact_service import scrape_candidates


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR),
    static_url_path="")
CORS(app)


def _parse_request(payload: dict) -> PipelineRequest:
    return PipelineRequest(
        image_url=(payload.get("image_url") or "").strip() or None,
        listing_url=(payload.get("listing_url") or "").strip() or None,
        listing_source=(payload.get("listing_source") or "unknown").strip(),
        selected_image_url=(payload.get("selected_image_url") or "").strip() or None,
    )


@app.get("/api/health")
def health():
    print ('Health Check OK')
    return jsonify(
        { "ok": True,
            "routes": ["/api/health", "/api/pipeline/search"],
            "step_1": "input metadata + active image",
            "step_2": "image search",
            "step_3": "pending",
            "step_4": "pending",
        }
    )

@app.post("/api/pipeline/extract")
def pipeline_extract():
    payload = request.get_json(silent=True) or {}
    req = _parse_request(payload)

    extract_result = resolve_input(
        image_url=req.image_url,
        listing_url=req.listing_url,
        selected_image_url=req.selected_image_url,
    )

    if extract_result["status"] == "error":
        err = ErrorPayload(error=extract_result["error"] or "Could not resolve input.")
        return jsonify(asdict(err)), 400

    input_panel = InputPanel(
        submitted_listing_url=extract_result["listing_url"],
        listing_source=extract_result["listing_source"],
        submitted_image_url=req.image_url,
        selected_image_url=req.selected_image_url,
        active_image_url=extract_result["hero_image_url"],
        metadata={
            "input_mode": "listing_url" if req.listing_url else "image_url",
            "extractor_status": extract_result["status"],
            "notes": [],
            "name": extract_result["metadata"].get("name"),
            "city": extract_result["metadata"].get("city"),
            "address": extract_result["metadata"].get("address"),
            "room_id": extract_result.get("room_id"),
            "image_candidate_count": len(extract_result.get("image_candidates", [])),
        },
    )

    return jsonify({
        "ok": True,
        "input_panel": asdict(input_panel),
    })


@app.post("/api/pipeline/search")
def pipeline_search():
    payload = request.get_json(silent=True) or {}
    req = _parse_request(payload)
    extract_result = resolve_input( image_url=req.image_url, listing_url=req.listing_url, selected_image_url=req.selected_image_url)
    active_image_url = extract_result["hero_image_url"]
    print(f"Starting search for {active_image_url}")

    if not active_image_url:
        err = ErrorPayload(error=extract_result["error"] or "Could not resolve an image.")
        return jsonify(asdict(err)), 400
    input_panel = InputPanel(
        submitted_listing_url=extract_result["listing_url"],
        listing_source=extract_result["listing_source"],
        submitted_image_url=req.image_url,
        selected_image_url=req.selected_image_url,
        active_image_url=active_image_url,
        metadata={
            "input_mode": "listing_url" if req.listing_url else "image_url",
            "extractor_status": extract_result["status"],
            "notes": [],
            "name": extract_result["metadata"].get("name"),
            "city": extract_result["metadata"].get("city"),
            "address": extract_result["metadata"].get("address"),
            "room_id": extract_result.get("room_id"),
            "image_candidate_count": len(extract_result.get("image_candidates", [])),
        },
    )

    search_result = run_image_search(active_image_url or "")
    classified = classify_matches(search_result["matches"], property_name=extract_result["metadata"].get("name"))
    contact_result = scrape_candidates(classified["direct"], classified["unknown"], base_address=extract_result["metadata"].get("address"))


        
    def build_match_records(items):
        return [
            MatchRecord(
                url=item["url"],
                domain=item["domain"],
                title=item.get("title", ""),
                source=item.get("source", ""),
                match_type=item.get("match_type", "unknown"),
                thumbnail_url=item.get("thumbnail_url"),
                rank=item.get("rank", 0),
                score1=item.get("score1"),
                listing_id=item.get("listing_id"),
                platform=item.get("platform"),
                hidden_reason=item.get("hidden_reason"),
            )
            for item in items
        ]    
        
        
    def build_contact_records(items):
        return [
            ContactRecord(
                url=item["url"],
                domain=item["domain"],
                emails=item.get("emails", []),
                phones=item.get("phones", []),
                address=item.get("address"),
                title=item.get("title", ""),
                error=item.get("error"),
                source_bucket=item.get("source_bucket"),
                source_quality=item.get("source_quality"),
                rank=item.get("rank", 0),
                score1=item.get("score1"),
            )
            for item in items
        ]

    response = PipelineResponse(
        ok=True,
        input_panel=input_panel,
        match_discovery=MatchDiscoveryPanel(
            provider=search_result["provider"],
            raw_match_count=len(search_result["matches"]),
            matches=build_match_records(search_result["matches"])),
        classification=ClassificationPanel(
            status=classified["status"],
            direct=build_match_records(classified["direct"]),
            ota=build_match_records(classified["ota"]),
            unknown=build_match_records(classified["unknown"]),
            hidden=build_match_records(classified["hidden"])),
        contact=ContactPanel(
            status=contact_result["status"],
            records=build_contact_records(contact_result["records"]),
        ))
    return jsonify(asdict(response))

##  Routes here

@app.get("/")
def root():
    return render_template("pipeline.html")


@app.get("/pipeline.html")
def pipeline_page():
    return render_template("pipeline.html")

@app.get("/bulk.html")
def bulk_page():
    return render_template("bulk.html")



## compatibility for index.html here:

@app.get("/index.html")
def index_page():
    return send_from_directory(BASE_DIR / "public", "index.html")


@app.post("/api/search")
def legacy_search():
    payload = request.get_json(silent=True) or {}
    req = _parse_request({
        "listing_url": payload.get("airbnb_url"),
        "image_url": payload.get("image_url"),
    })

    extract_result = resolve_input(
        image_url=req.image_url,
        listing_url=req.listing_url,
        selected_image_url=req.selected_image_url,
    )
    active_image_url = extract_result["hero_image_url"]

    if not active_image_url:
        err = ErrorPayload(error=extract_result["error"] or "Could not resolve an image.")
        return jsonify(asdict(err)), 400

    search_result = run_image_search(active_image_url or "")
    classified = classify_matches(
        search_result["matches"],
        property_name=extract_result["metadata"].get("name"),
    )
    contact_result = scrape_candidates(classified["direct"], classified["unknown"])

    contact_by_url = {r["url"]: r for r in contact_result["records"]}
    matches = []

    for item in search_result["matches"]:
        c = contact_by_url.get(item["url"], {})
        platform = item.get("platform")
        is_ota = item.get("is_ota", False)

        if not platform:
            # recover platform from classified buckets if present
            for bucket in ("direct", "ota", "unknown", "hidden"):
                hit = next((x for x in classified[bucket] if x["url"] == item["url"]), None)
                if hit:
                    platform = hit.get("platform")
                    is_ota = hit.get("is_ota", False)
                    break

        matches.append({
            "url": item["url"],
            "domain": item["domain"],
            "platform": platform,
            "is_ota": is_ota,
            "title": c.get("title") or item.get("title", ""),
            "emails": c.get("emails", []),
            "phones": c.get("phones", []),
        })

    summary_emails = []
    summary_phones = []
    for r in contact_result["records"]:
        summary_emails.extend(r.get("emails", []))
        summary_phones.extend(r.get("phones", []))

    return jsonify({
        "image_url": active_image_url,
        "summary": {
            "total": len(matches),
            "direct": len(classified["direct"]),
            "ota": len(classified["ota"]),
            "unknown": len(classified["unknown"]),
            "hidden_noise": len(classified["hidden"]),
            "emails": list(dict.fromkeys(summary_emails))[:10],
            "phones": list(dict.fromkeys(summary_phones))[:10],
        },
        "matches": matches,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)