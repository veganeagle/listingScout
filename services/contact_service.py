# contact service

from services.scraper import scrape_contact


def _source_quality(bucket: str, score1: int | None, rank: int) -> str:
    if bucket == "direct":
        return "high"
    if score1 is not None and score1 <= 12:
        return "medium"
    if score1 is not None and score1 <= 26 and rank <= 20:
        return "medium"
    return "low"


def scrape_candidates(direct: list[dict], unknown: list[dict], base_address: str | None = None) -> dict:
    records = []
    for bucket_name, items in (("direct", direct), ("unknown", unknown)):
        for item in items:
            contact = scrape_contact(item["url"])
            records.append(
                {
                    "url": item["url"],
                    "domain": item["domain"],
                    "title": contact.get("title") or item.get("title", ""),
                    "emails": contact.get("emails", []),
                    "phones": contact.get("phones", []),
                    "address": contact.get("address") or base_address,
                    "error": contact.get("error"),
                    "source_bucket": bucket_name,
                    "source_quality": _source_quality(
                        bucket_name,
                        item.get("score1"),
                        item.get("rank", 0),
                    ),
                    "rank": item.get("rank", 0),
                    "score1": item.get("score1"),
                }
            )

    return {
        "status": "ok",
        "records": records,
    }