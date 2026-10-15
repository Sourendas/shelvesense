#!/usr/bin/env python3
"""CLI end-to-end demo: load → enrich → ask. Offline, zero network."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.catalog import load_products, load_reviews
from app.enrich import enrich_catalogue
from app.qa import ask


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or "which SKU for dry skin?"
    print("=== ShelfSense offline demo ===")
    print(f"Data dir: {ROOT / 'data'}")
    products = load_products()
    reviews = load_reviews()
    print(f"Loaded {len(products)} products, {len(reviews)} reviews")

    enriched = enrich_catalogue(products, reviews)
    filled = sum(
        1
        for p in enriched
        if (p.get("enriched") or {}).get("source", {}).get("skin_type") == "inferred"
        or (p.get("enriched") or {}).get("source", {}).get("concerns") == "inferred"
    )
    print(f"Enriched catalogue ({filled} products gained inferred attrs)")
    print()
    print("--- Sample enriched rows ---")
    for p in enriched[:3]:
        e = p["enriched"]
        print(
            f"  {p['sku']} | {p['title'][:40]:40s} | "
            f"skin={p['skin_type']} concerns={p['concerns'][:2]} "
            f"src={e['source']['skin_type']}/{e['source']['concerns']}"
        )
    print()
    print(f"--- Q: {question} ---")
    result = ask(question, enriched, reviews)
    print(result["answer"])
    print()
    print("Recommendations:")
    for r in result["recommendations"]:
        print(
            f"  [{r['score']:.3f}] {r['sku']} {r['title']} "
            f"(${r['price_usd']}) — {r['why']}"
        )
    print()
    print("Citations:")
    for c in result["citations"][:5]:
        print(f"  ({c['type']}/{c['sku']}) {c['snippet'][:100]}")
    print()
    print(f"Retriever: {result['retriever']}")
    out = ROOT / "demo_last_answer.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
