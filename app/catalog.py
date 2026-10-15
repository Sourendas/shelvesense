"""Load synthetic catalogue + reviews from CSV (stdlib only)."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_products(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _read_csv(path or DATA / "products.csv")
    products: list[dict[str, Any]] = []
    for row in rows:
        products.append(
            {
                "sku": row["sku"].strip(),
                "title": row["title"].strip(),
                "description": row.get("description", "").strip(),
                "category": row.get("category", "").strip(),
                "brand": row.get("brand", "").strip(),
                "price_usd": float(row["price_usd"]) if row.get("price_usd") else None,
                "skin_type": _split_field(row.get("skin_type", "")),
                "concerns": _split_field(row.get("concerns", "")),
                "key_ingredients": _split_field(row.get("key_ingredients", "")),
                "size": row.get("size", "").strip(),
                # filled by enrich
                "enriched": {},
            }
        )
    return products


def load_reviews(path: Path | None = None) -> list[dict[str, Any]]:
    rows = _read_csv(path or DATA / "reviews.csv")
    reviews: list[dict[str, Any]] = []
    for row in rows:
        reviews.append(
            {
                "review_id": row["review_id"].strip(),
                "sku": row["sku"].strip(),
                "rating": int(row["rating"]) if row.get("rating") else 0,
                "title": row.get("title", "").strip(),
                "body": row.get("body", "").strip(),
            }
        )
    return reviews


def _split_field(value: str) -> list[str]:
    if not value or not value.strip():
        return []
    return [p.strip().lower() for p in value.replace(";", ",").split(",") if p.strip()]


def reviews_for_sku(reviews: list[dict[str, Any]], sku: str) -> list[dict[str, Any]]:
    return [r for r in reviews if r["sku"] == sku]
