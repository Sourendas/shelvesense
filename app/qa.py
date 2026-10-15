"""Shopper Q&A with evidence citations from products + reviews."""

from __future__ import annotations

from typing import Any

from .similarity import LocalTfidfIndex, build_corpus_texts


def ask(
    question: str,
    products: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    top_k: int = 5,
) -> dict[str, Any]:
    """Answer a shopper question with ranked SKUs and citation snippets.

    Retrieval uses LocalTfidfIndex (CPU stub). On AMD Developer Cloud, replace
    the index with ROCm embeddings — see similarity.py header comments.
    """
    question = (question or "").strip()
    if not question:
        return {
            "question": question,
            "answer": "Ask a product question, e.g. which SKU for dry skin?",
            "recommendations": [],
            "citations": [],
            "retriever": "local-tfidf-stub",
        }

    texts, meta = build_corpus_texts(products, reviews)
    index = LocalTfidfIndex(texts)
    ranked = index.score(question)

    # Aggregate product scores from product docs + matching reviews
    sku_scores: dict[str, float] = {}
    citations: list[dict[str, Any]] = []
    product_by_sku = {p["sku"]: p for p in products}

    for idx, score in ranked[: max(top_k * 4, 12)]:
        if score <= 0:
            continue
        m = meta[idx]
        sku = m["sku"]
        sku_scores[sku] = sku_scores.get(sku, 0.0) + score
        if m["kind"] == "review":
            r = m["ref"]
            snippet = (r.get("body") or r.get("title") or "")[:180]
            citations.append(
                {
                    "type": "review",
                    "sku": sku,
                    "review_id": r.get("review_id"),
                    "rating": r.get("rating"),
                    "snippet": snippet,
                    "score": round(score, 4),
                }
            )
        else:
            p = m["ref"]
            snippet = f"{p.get('title', '')} — {p.get('description', '')}"[:180]
            citations.append(
                {
                    "type": "product",
                    "sku": sku,
                    "title": p.get("title"),
                    "snippet": snippet,
                    "score": round(score, 4),
                }
            )

    # Rank SKUs
    ranked_skus = sorted(sku_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    recommendations: list[dict[str, Any]] = []
    for sku, sc in ranked_skus:
        p = product_by_sku.get(sku)
        if not p:
            continue
        recommendations.append(
            {
                "sku": sku,
                "title": p.get("title"),
                "brand": p.get("brand"),
                "price_usd": p.get("price_usd"),
                "skin_type": p.get("skin_type") or [],
                "concerns": p.get("concerns") or [],
                "key_ingredients": (p.get("key_ingredients") or [])[:6],
                "avg_rating": (p.get("enriched") or {}).get("avg_rating"),
                "score": round(sc, 4),
                "why": _why(p, question),
            }
        )

    answer = _compose_answer(question, recommendations)
    # Dedupe citations by (type, sku, snippet prefix), keep top
    seen: set[str] = set()
    unique_cites: list[dict[str, Any]] = []
    for c in citations:
        key = f"{c['type']}:{c['sku']}:{c['snippet'][:40]}"
        if key in seen:
            continue
        seen.add(key)
        unique_cites.append(c)
        if len(unique_cites) >= top_k + 3:
            break

    return {
        "question": question,
        "answer": answer,
        "recommendations": recommendations,
        "citations": unique_cites,
        "retriever": "local-tfidf-stub",  # swap label when AMD embeddings land
        "note": "Retrieval is a local TF-IDF stub. AMD ROCm embeddings plug in via app/similarity.py.",
    }


def _why(product: dict[str, Any], question: str) -> str:
    bits: list[str] = []
    q = question.lower()
    skin = product.get("skin_type") or []
    concerns = product.get("concerns") or []
    ings = product.get("key_ingredients") or []
    if skin:
        bits.append("skin types: " + ", ".join(skin))
    if concerns:
        bits.append("concerns: " + ", ".join(concerns[:3]))
    if ings and any(w in q for w in ("ingredient", "contain", "with")):
        bits.append("ingredients: " + ", ".join(ings[:4]))
    if not bits and product.get("description"):
        bits.append(product["description"][:100])
    return "; ".join(bits) if bits else "Matched catalogue + review text."


def _compose_answer(question: str, recs: list[dict[str, Any]]) -> str:
    if not recs:
        return (
            "I could not find a strong match in this sample catalogue. "
            "Try asking about dry skin, SPF, acne, or a brand name."
        )
    top = recs[0]
    others = recs[1:3]
    lines = [
        f"For “{question}”, the best match is **{top['sku']} — {top['title']}** "
        f"({top.get('brand')}, ${top.get('price_usd')})."
    ]
    if top.get("why"):
        lines.append(f"Why: {top['why']}.")
    if others:
        alt = ", ".join(f"{o['sku']} ({o['title']})" for o in others)
        lines.append(f"Also consider: {alt}.")
    lines.append("See citations below for review and listing evidence.")
    return " ".join(lines)
